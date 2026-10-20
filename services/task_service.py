from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


VALID_PRIORITIES = {"Low", "Medium", "High"}
PRIORITY_ORDER = {"High": 1, "Medium": 2, "Low": 3}


def validate_task_data(data: Dict[str, Any], is_update: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate task inputs on the server side."""
    if not isinstance(data, dict):
        return False, "Invalid request payload. Expected JSON object."

    if not is_update or "title" in data:
        title = data.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            return False, "Task title is required and cannot be empty."
        if len(title.strip()) > 200:
            return False, "Task title cannot exceed 200 characters."

    if "priority" in data and data["priority"]:
        if data["priority"] not in VALID_PRIORITIES:
            return False, f"Invalid priority. Allowed values: {', '.join(sorted(VALID_PRIORITIES))}."

    if "due_date" in data and data["due_date"]:
        due_date_str = str(data["due_date"]).strip()
        if due_date_str:
            try:
                datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                return False, "Invalid due date format. Expected YYYY-MM-DD."

    if "category" in data and data["category"]:
        if len(str(data["category"]).strip()) > 50:
            return False, "Category name cannot exceed 50 characters."

    if "description" in data and data["description"]:
        if len(str(data["description"])) > 2000:
            return False, "Description cannot exceed 2000 characters."

    return True, None


def task_row_to_dict(row) -> Dict[str, Any]:
    """Convert a SQLite Row object to a task dictionary."""
    if not row:
        return {}
    today_str = date.today().isoformat()
    due_date = row["due_date"] or ""
    is_completed = bool(row["is_completed"])
    is_overdue = False
    is_today = False

    if due_date and not is_completed:
        if due_date < today_str:
            is_overdue = True
        elif due_date == today_str:
            is_today = True
    elif due_date == today_str:
        is_today = True

    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "due_date": due_date,
        "priority": row["priority"],
        "category": row["category"] or "General",
        "is_completed": is_completed,
        "is_overdue": is_overdue,
        "is_today": is_today,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


def create_task(db, data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Create a new task in SQLite."""
    is_valid, error = validate_task_data(data)
    if not is_valid:
        return None, error

    title = data["title"].strip()
    description = (data.get("description") or "").strip()
    due_date = (data.get("due_date") or "").strip()
    priority = data.get("priority", "Medium")
    if priority not in VALID_PRIORITIES:
        priority = "Medium"
    category = (data.get("category") or "General").strip() or "General"

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, due_date, priority, category, is_completed)
        VALUES (?, ?, ?, ?, ?, 0);
    """, (title, description, due_date, priority, category))
    db.commit()

    task_id = cursor.lastrowid
    return get_task_by_id(db, task_id), None


def get_task_by_id(db, task_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single task by ID."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return task_row_to_dict(row)


def get_tasks(
    db,
    status_filter: Optional[str] = "all",
    priority_filter: Optional[str] = "all",
    category_filter: Optional[str] = "all",
    search_query: Optional[str] = None,
    sort_by: Optional[str] = "due_date_asc"
) -> List[Dict[str, Any]]:
    """
    Retrieve tasks with flexible filtering, searching, and sorting.
    Uses parameterized SQL queries.
    """
    today_str = date.today().isoformat()
    query = "SELECT * FROM tasks WHERE 1=1"
    params: List[Any] = []

    # Status filter
    if status_filter == "completed":
        query += " AND is_completed = 1"
    elif status_filter == "pending":
        query += " AND is_completed = 0"
    elif status_filter == "today":
        query += " AND due_date = ?"
        params.append(today_str)
    elif status_filter == "overdue":
        query += " AND is_completed = 0 AND due_date != '' AND due_date < ?"
        params.append(today_str)

    # Priority filter
    if priority_filter and priority_filter in VALID_PRIORITIES:
        query += " AND priority = ?"
        params.append(priority_filter)

    # Category filter
    if category_filter and category_filter != "all":
        query += " AND category = ?"
        params.append(category_filter)

    # Search query
    if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        query += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
        params.extend([term, term, term])

    # Sorting
    if sort_by == "due_date_asc":
        # Put items with due dates first, ascending, then items without due dates
        query += " ORDER BY CASE WHEN due_date = '' OR due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id DESC"
    elif sort_by == "due_date_desc":
        query += " ORDER BY CASE WHEN due_date = '' OR due_date IS NULL THEN 1 ELSE 0 END, due_date DESC, id DESC"
    elif sort_by == "priority_desc":
        # High -> Medium -> Low
        query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END ASC, due_date ASC"
    elif sort_by == "priority_asc":
        # Low -> Medium -> High
        query += " ORDER BY CASE priority WHEN 'Low' THEN 1 WHEN 'Medium' THEN 2 WHEN 'High' THEN 3 ELSE 4 END ASC, due_date ASC"
    elif sort_by == "created_at_desc":
        query += " ORDER BY id DESC"
    else:
        query += " ORDER BY id DESC"

    cursor = db.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    return [task_row_to_dict(r) for r in rows]


def update_task(db, task_id: int, data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Update task details."""
    existing = get_task_by_id(db, task_id)
    if not existing:
        return None, "Task not found."

    is_valid, error = validate_task_data(data, is_update=True)
    if not is_valid:
        return None, error

    title = data.get("title", existing["title"]).strip()
    description = (data.get("description", existing["description"]) or "").strip()
    due_date = (data.get("due_date", existing["due_date"]) or "").strip()
    priority = data.get("priority", existing["priority"])
    if priority not in VALID_PRIORITIES:
        priority = existing["priority"]
    category = (data.get("category", existing["category"]) or "General").strip() or "General"
    is_completed = int(data.get("is_completed", existing["is_completed"]))

    cursor = db.cursor()
    cursor.execute("""
        UPDATE tasks
        SET title = ?, description = ?, due_date = ?, priority = ?, category = ?, is_completed = ?, updated_at = (datetime('now', 'localtime'))
        WHERE id = ?;
    """, (title, description, due_date, priority, category, is_completed, task_id))
    db.commit()

    return get_task_by_id(db, task_id), None


def toggle_task_completion(db, task_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Toggle the completion state of a task."""
    existing = get_task_by_id(db, task_id)
    if not existing:
        return None, "Task not found."

    new_status = 0 if existing["is_completed"] else 1
    cursor = db.cursor()
    cursor.execute("""
        UPDATE tasks
        SET is_completed = ?, updated_at = (datetime('now', 'localtime'))
        WHERE id = ?;
    """, (new_status, task_id))
    db.commit()

    return get_task_by_id(db, task_id), None


def delete_task(db, task_id: int) -> bool:
    """Delete a task by ID."""
    cursor = db.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
    db.commit()
    return cursor.rowcount > 0


def get_task_stats(db) -> Dict[str, Any]:
    """Calculate real-time task statistics."""
    today_str = date.today().isoformat()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM tasks;")
    total_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_completed = 1;")
    completed_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE is_completed = 0;")
    pending_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE due_date = ?;", (today_str,))
    today_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE due_date = ? AND is_completed = 1;", (today_str,))
    today_completed = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE is_completed = 0 AND due_date != '' AND due_date < ?;
    """, (today_str,))
    overdue_tasks = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE is_completed = 0 AND priority = 'High';
    """)
    high_priority_pending = cursor.fetchone()[0]

    # Calculate completion percentage for today's tasks or all tasks
    task_completion_rate = 0
    if total_tasks > 0:
        task_completion_rate = round((completed_tasks / total_tasks) * 100)

    today_completion_rate = 0
    if today_tasks > 0:
        today_completion_rate = round((today_completed / today_tasks) * 100)

    return {
        "total": total_tasks,
        "completed": completed_tasks,
        "pending": pending_tasks,
        "today_total": today_tasks,
        "today_completed": today_completed,
        "today_pending": max(0, today_tasks - today_completed),
        "overdue": overdue_tasks,
        "high_priority_pending": high_priority_pending,
        "completion_rate": task_completion_rate,
        "today_completion_rate": today_completion_rate
    }
