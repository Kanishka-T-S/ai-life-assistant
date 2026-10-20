import sqlite3
from flask import g, current_app


def get_db():
    """Open a new database connection if there is none yet for the current request context."""
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
        # Enable foreign key enforcement
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    """Close database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app=None):
    """Initialize database tables."""
    if app:
        with app.app_context():
            db = get_db()
            _create_schema(db)
    else:
        db = get_db()
        _create_schema(db)


def _create_schema(db):
    """Create tables with parameterized schemas and constraints."""
    cursor = db.cursor()

    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')) DEFAULT 'Medium',
            category TEXT NOT NULL DEFAULT 'General',
            is_completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # Habits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            frequency TEXT NOT NULL DEFAULT 'daily',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)

    # Habit completion logs (one entry per habit per date)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE(habit_id, date)
        );
    """)

    # Indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(is_completed);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_logs_date ON habit_logs(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_logs(habit_id);")

    db.commit()


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
