To-Do List Web App (Python only)

**Enterprise-Grade Task Management System built entirely in Python using PyWebIO**

## Key Features (CTO Edition)

### Core Functionality
- Create, read, update, delete (CRUD) tasks with persistent JSON storage
- Mark tasks complete/incomplete with instant visual feedback
- Search, filter by priority/category, and sort tasks
- Auto-backup system with configurable retention (latest 5 backups)
- Data recovery from backups on corruption

### Architecture & Code Quality
- **Service layer** (`TodoService` class) separating business logic from UI
- Comprehensive error handling and validation
- Structured logging to `data/app.log` with both console and file output
- Organized directory structure (`data/`, `data/backups/`)
- Graceful error recovery with automatic backup restoration

### Task Management
- **Priorities**: Low, Normal, High (with sortable UI)
- **Categories**: Flexible, user-defined categories
- **Due dates**: YYYY-MM-DD format with sorting support
- **Metadata**: Created & updated timestamps

### UI/UX
- Dashboard with real-time statistics (total, pending, completed, high-priority counts)
- Advanced filtering: search, priority, category, hide-completed
- Multiple sort options: by creation date, priority, or due date
- Professional icons and layout without HTML/CSS
- Toast notifications for user actions

### Data Management
- **Export**: Full JSON export for backups and migration
- **Import**: Bulk import from JSON files
- **Statistics**: Real-time task analytics and counts

### Technical Features
- Environment-based port configuration (`PORT` env var)
- Structured logging with timestamps and log levels
- Automated backup with timestamp versioning
- Data validation on input/output
- Thread-safe service layer

---

## Run Locally

```bash
python -m pip install -r requirements.txt
python app.py
```

Open http://localhost:8080 in your browser.

To use a different port:
```bash
$env:PORT=8081  # PowerShell
python app.py
```

Or:
```cmd
set PORT=8081  # Command prompt
python app.py
```

---

## Project Structure

```
.
├── app.py              # Main application (service layer + UI)
├── requirements.txt    # Python dependencies
├── data/
│   ├── todos.json      # Main task database
│   ├── app.log         # Application logs
│   └── backups/        # Automatic backups (max 5)
└── README.md           # This file
```

---

## Files

- **app.py**: Enterprise-grade application with TodoService, logging, error handling
- **requirements.txt**: PyWebIO dependency
- **data/todos.json**: Task database (auto-created)
- **data/app.log**: Structured logs
- **data/backups/**: Automatic daily backups

---

## Next Steps

- Add SQLite backend for scalability
- Implement user authentication and multi-user support
- Add task templates and recurring tasks
- Deploy via Docker for production
- Add REST API layer for mobile clients


