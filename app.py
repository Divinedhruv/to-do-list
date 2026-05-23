import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
import uuid

from pywebio import start_server
from pywebio.input import input, select, textarea, input_group
from pywebio.output import put_text, put_table, clear, put_markdown, put_row, put_buttons, toast, put_html
from pywebio.pin import put_input, put_select, put_checkbox, get_pin_values

# Configuration
DATA_DIR = Path('data')
DATA_FILE = DATA_DIR / 'todos.json'
BACKUP_DIR = DATA_DIR / 'backups'
LOG_FILE = DATA_DIR / 'app.log'
MAX_BACKUPS = 5

# Setup directories and logging
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TodoService:
    """Business logic layer for todo management."""
    
    def __init__(self, data_file=DATA_FILE):
        self.data_file = Path(data_file)
        self.todos = self._load()
    
    def _load(self):
        """Load todos from file with error recovery."""
        if not self.data_file.exists():
            logger.info(f"Creating new data file: {self.data_file}")
            return []
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} todos")
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to load todos: {e}")
            self._recover_from_backup()
            return []
    
    def _recover_from_backup(self):
        """Attempt to recover from latest backup."""
        backups = sorted(BACKUP_DIR.glob('todos_backup_*.json'), reverse=True)
        if backups:
            try:
                with open(backups[0], 'r', encoding='utf-8') as f:
                    recovered = json.load(f)
                    logger.info(f"Recovered from backup: {backups[0]}")
                    with open(self.data_file, 'w', encoding='utf-8') as fw:
                        json.dump(recovered, fw, ensure_ascii=False, indent=2)
                    return recovered
            except Exception as e:
                logger.error(f"Backup recovery failed: {e}")
        return []
    
    def _backup(self):
        """Create backup before save."""
        if self.data_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = BACKUP_DIR / f'todos_backup_{timestamp}.json'
            try:
                shutil.copy2(self.data_file, backup_file)
                # Keep only latest MAX_BACKUPS
                backups = sorted(BACKUP_DIR.glob('todos_backup_*.json'), reverse=True)
                for old_backup in backups[MAX_BACKUPS:]:
                    old_backup.unlink()
                logger.debug(f"Backup created: {backup_file}")
            except Exception as e:
                logger.warning(f"Backup failed: {e}")
    
    def save(self):
        """Save todos to file with backup."""
        self._backup()
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.todos, f, ensure_ascii=False, indent=2)
            logger.info("Todos saved")
        except Exception as e:
            logger.error(f"Failed to save todos: {e}")
            raise
    
    def add(self, text, due='', priority='Normal', category='General'):
        """Add a new todo."""
        if not text or not text.strip():
            raise ValueError("Task text cannot be empty")
        
        task = {
            'id': str(uuid.uuid4()),
            'text': text.strip(),
            'done': False,
            'priority': priority,
            'due': due.strip(),
            'category': category,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        self.todos.append(task)
        self.save()
        logger.info(f"Added task: {task['id']}")
        return task
    
    def update(self, task_id, **kwargs):
        """Update a todo."""
        for task in self.todos:
            if task['id'] == task_id:
                allowed_fields = {'text', 'done', 'priority', 'due', 'category'}
                for key, val in kwargs.items():
                    if key in allowed_fields:
                        task[key] = val
                task['updated_at'] = datetime.utcnow().isoformat()
                self.save()
                logger.info(f"Updated task: {task_id}")
                return task
        raise ValueError(f"Task {task_id} not found")
    
    def delete(self, task_id):
        """Delete a todo."""
        self.todos = [t for t in self.todos if t['id'] != task_id]
        self.save()
        logger.info(f"Deleted task: {task_id}")
    
    def toggle(self, task_id):
        """Toggle task completion status."""
        task = self.update(task_id, done=not next((t.get('done') for t in self.todos if t['id'] == task_id), False))
        return task
    
    def get_stats(self):
        """Get task statistics."""
        total = len(self.todos)
        completed = sum(1 for t in self.todos if t.get('done'))
        pending = total - completed
        by_priority = {'High': 0, 'Normal': 0, 'Low': 0}
        for t in self.todos:
            if not t.get('done'):
                by_priority[t.get('priority', 'Normal')] += 1
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'by_priority': by_priority
        }
    
    def filter_and_sort(self, search='', priority='All', category='All', hide_done=False, sort_by='created'):
        """Filter and sort todos."""
        result = self.todos
        
        # Apply filters
        if search:
            result = [t for t in result if search.lower() in t.get('text', '').lower()]
        if priority != 'All':
            result = [t for t in result if t.get('priority') == priority]
        if category != 'All':
            result = [t for t in result if t.get('category') == category]
        if hide_done:
            result = [t for t in result if not t.get('done')]
        
        # Apply sorting
        if sort_by == 'priority':
            priority_order = {'High': 0, 'Normal': 1, 'Low': 2}
            result.sort(key=lambda t: (t.get('done'), priority_order.get(t.get('priority', 'Normal'), 3)))
        elif sort_by == 'due':
            result.sort(key=lambda t: (t.get('done'), t.get('due', 'z')))
        else:  # created (default)
            result.sort(key=lambda t: (t.get('done'), t.get('created_at', '')))
        
        return result


# Global service instance
service = TodoService()


def add_task_dialog():
    """Dialog to add new task."""
    try:
        categories = sorted(set(t.get('category', 'General') for t in service.todos) or ['General'])
        data = input_group('Add Task', [
            input('Task', name='text', required=True),
            input('Due (YYYY-MM-DD)', name='due', placeholder='2026-12-31'),
            select('Priority', name='priority', options=['Low', 'Normal', 'High'], value='Normal'),
            select('Category', name='category', options=categories + ['+ New Category'], value=categories[0] if categories else 'General')
        ])
        
        category = data['category']
        if category == '+ New Category':
            category = input('New category name', required=True).strip()
        
        service.add(data['text'], data['due'], data['priority'], category)
        toast('✅ Task added', duration=2)
        logger.info(f"User added task: {data['text']}")
    except Exception as e:
        logger.error(f"Add task error: {e}")
        toast(f'❌ Error: {str(e)}', duration=3)


def edit_task_dialog(task_id):
    """Dialog to edit existing task."""
    try:
        task = next((t for t in service.todos if t['id'] == task_id), None)
        if not task:
            toast('❌ Task not found', duration=2)
            return
        
        categories = sorted(set(t.get('category', 'General') for t in service.todos))
        data = input_group('Edit Task', [
            input('Task', name='text', value=task['text'], required=True),
            input('Due (YYYY-MM-DD)', name='due', value=task.get('due', '')),
            select('Priority', name='priority', options=['Low', 'Normal', 'High'], value=task.get('priority', 'Normal')),
            select('Category', name='category', options=categories, value=task.get('category', 'General'))
        ])
        
        service.update(task_id, **data)
        toast('✅ Task updated', duration=2)
        logger.info(f"User updated task: {task_id}")
    except Exception as e:
        logger.error(f"Edit task error: {e}")
        toast(f'❌ Error: {str(e)}', duration=3)


def render_dashboard():
    """Render statistics dashboard."""
    stats = service.get_stats()
    put_markdown('### 📊 Dashboard')
    
    dashboard_html = f'''
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0;">
        <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; text-align: center;">
            <div style="font-size: 24px; font-weight: bold; color: #2e7d32;">{stats['total']}</div>
            <div style="color: #666; font-size: 14px;">Total Tasks</div>
        </div>
        <div style="background: #fff3e0; padding: 15px; border-radius: 8px; text-align: center;">
            <div style="font-size: 24px; font-weight: bold; color: #f57c00;">{stats['pending']}</div>
            <div style="color: #666; font-size: 14px;">Pending</div>
        </div>
        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center;">
            <div style="font-size: 24px; font-weight: bold; color: #1565c0;">{stats['completed']}</div>
            <div style="color: #666; font-size: 14px;">Completed</div>
        </div>
        <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; text-align: center;">
            <div style="font-size: 24px; font-weight: bold; color: #6a1b9a;">{stats['by_priority']['High']}</div>
            <div style="color: #666; font-size: 14px;">High Priority</div>
        </div>
    </div>
    '''
    put_html(dashboard_html)


def render_tasks():
    """Main task rendering with filters and controls."""
    clear()
    
    put_markdown('# 📋 To-Do Manager — Enterprise Edition')
    put_markdown('**CTO-Grade Task Management System** — with auto-backup, error recovery & analytics')
    
    # Render dashboard
    render_dashboard()
    
    # Controls panel
    put_markdown('### 🎛️ Controls & Filters')
    put_row([
        put_buttons(['➕ Add Task', '🔄 Refresh'], onclick=[add_task_dialog, lambda _: None]),
        put_buttons(['💾 Export', '📥 Import', '🗑️ Clear All'], onclick=[export_json, import_json, clear_all_tasks])
    ])
    
    put_markdown('---')
    
    # Initialize filter widgets first
    categories = sorted(set(t.get('category', 'General') for t in service.todos)) or ['General']
    put_input('search', label='🔍 Search', value='', placeholder='Search tasks...')
    put_select('priority_filter', label='⭐ Priority', options=['All', 'High', 'Normal', 'Low'], value='All')
    put_select('category_filter', label='📂 Category', options=['All'] + categories, value='All')
    put_select('sort_by', label='📑 Sort By', options=['created', 'priority', 'due'], value='created')
    put_checkbox('hide_done', options=['✓ Hide Done'], value=[])
    
    # Now read the pin values (they should have defaults from above)
    pin_values = get_pin_values(['search', 'priority_filter', 'category_filter', 'hide_done', 'sort_by'])
    search = pin_values.get('search', '')
    priority = pin_values.get('priority_filter', 'All')
    category = pin_values.get('category_filter', 'All')
    hide_done = 'Hide Done' in (pin_values.get('hide_done', []) or [])
    sort_by = pin_values.get('sort_by', 'created')
    
    put_markdown('---')
    
    # Get filtered tasks
    tasks = service.filter_and_sort(search, priority, category, hide_done, sort_by)
    
    if not tasks:
        put_markdown('### 📭 No tasks match the current filters.')
    else:
        put_markdown(f'### 📝 Tasks ({len(tasks)})')
        
        for idx, task in enumerate(tasks, 1):
            status_icon = '✅' if task.get('done') else '⬜'
            priority_emoji = {'High': '🔴', 'Normal': '🟡', 'Low': '🟢'}.get(task.get('priority', 'Normal'), '🔵')
            
            # Task content
            task_text = task['text']
            if task.get('done'):
                task_text = f"~~{task_text}~~"
            
            due_str = f"📅 {task['due']}" if task.get('due') else ""
            cat_str = f"📂 {task.get('category', 'General')}"
            
            def make_toggle(tid):
                def _(_):
                    try:
                        service.toggle(tid)
                        toast('✅ Toggled', duration=1)
                    except Exception as e:
                        toast(f'❌ Error: {e}', duration=2)
                return _
            
            def make_edit(tid):
                def _(_):
                    edit_task_dialog(tid)
                return _
            
            def make_delete(tid):
                def _(_):
                    try:
                        service.delete(tid)
                        toast('Delete', duration=1)
                    except Exception as e:
                        toast(f'Error: {e}', duration=2)
                return _
            
            task_info = f"**{task_text}**  \n{priority_emoji} Priority: **{task.get('priority', 'Normal')}** | {cat_str} | {due_str}"
            
            put_row([
                put_text(f"{idx}.", scope="item"),
                put_text(status_icon, scope="status"),
                put_markdown(task_info),
                put_buttons(['Edit', 'Toggle', 'Delete'], 
                           onclick=[make_edit(task['id']), make_toggle(task['id']), make_delete(task['id'])])
            ], size='30px 30px 1fr 250px')
    
    put_markdown('---')
    
    # Footer
    put_row([
        put_buttons(['Quit'], onclick=[lambda _: logger.info("User quit")])
    ])


def export_json(_):
    """Export all todos as JSON."""
    try:
        json_str = json.dumps(service.todos, ensure_ascii=False, indent=2)
        textarea('📊 Exported JSON (copy below)', value=json_str, rows=15)
        logger.info("User exported todos")
    except Exception as e:
        logger.error(f"Export error: {e}")
        toast(f'❌ Export failed: {e}', duration=3)


def import_json(_):
    """Import todos from JSON."""
    try:
        json_str = textarea('📥 Paste JSON to import', rows=15)
        if not json_str:
            return
        
        data = json.loads(json_str)
        if isinstance(data, list):
            service.todos = data
            service.save()
            toast('✅ Imported successfully', duration=2)
            logger.info("User imported todos")
        else:
            toast('❌ Invalid format: expected list', duration=3)
    except Exception as e:
        logger.error(f"Import error: {e}")
        toast(f'❌ Import failed: {e}', duration=3)


def clear_all_tasks(_):
    """Clear all completed tasks."""
    try:
        initial_count = len(service.todos)
        service.todos = [t for t in service.todos if not t.get('done')]
        service.save()
        cleared = initial_count - len(service.todos)
        toast(f'✅ Cleared {cleared} completed tasks', duration=2)
        logger.info(f"User cleared {cleared} completed tasks")
    except Exception as e:
        logger.error(f"Clear all error: {e}")
        toast(f'❌ Error: {e}', duration=3)


def todo_app():
    """Main application - render once, PyWebIO handles interactions."""
    logger.info("App started")
    try:
        render_tasks()
    except KeyboardInterrupt:
        logger.info("App interrupted")
    except Exception as e:
        logger.error(f"App error: {e}")
        put_markdown(f'❌ **Critical Error**: {e}')





if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    try:
        start_server(todo_app, port=port, host='0.0.0.0', debug=False)
    except Exception as e:
        logger.critical(f"Server startup failed: {e}")
        raise
