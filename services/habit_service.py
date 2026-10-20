from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set


VALID_FREQUENCIES = {"daily", "weekdays", "weekly"}


def validate_habit_data(data: Dict[str, Any], is_update: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate habit inputs on the server side."""
    if not isinstance(data, dict):
        return False, "Invalid request payload. Expected JSON object."

    if not is_update or "name" in data:
        name = data.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            return False, "Habit name is required and cannot be empty."
        if len(name.strip()) > 100:
            return False, "Habit name cannot exceed 100 characters."

    if "frequency" in data and data["frequency"]:
        freq = str(data["frequency"]).strip().lower()
        if freq not in VALID_FREQUENCIES:
            return False, f"Invalid frequency. Allowed: {', '.join(sorted(VALID_FREQUENCIES))}."

    if "description" in data and data["description"]:
        if len(str(data["description"])) > 500:
            return False, "Description cannot exceed 500 characters."

    return True, None


def calculate_habit_streaks(completed_dates_set: Set[str]) -> Tuple[int, int]:
    """
    Calculate (current_streak, longest_streak) from a set of YYYY-MM-DD date strings.
    Streak logic:
    - If today is completed, streak counts consecutive days ending today.
    - If today is not completed yet, but yesterday was, streak counts consecutive days ending yesterday.
    - Otherwise current streak is 0.
    - Longest streak counts the maximum run of consecutive calendar days ever recorded.
    """
    if not completed_dates_set:
        return 0, 0

    parsed_dates = sorted([datetime.strptime(d, "%Y-%m-%d").date() for d in completed_dates_set])

    # Calculate longest streak
    longest_streak = 0
    current_run = 0
    prev_date = None

    for d in parsed_dates:
        if prev_date is None:
            current_run = 1
        elif d == prev_date + timedelta(days=1):
            current_run += 1
        elif d == prev_date:
            # Duplicate, ignore
            pass
        else:
            current_run = 1
        if current_run > longest_streak:
            longest_streak = current_run
        prev_date = d

    # Calculate current streak
    today = date.today()
    yesterday = today - timedelta(days=1)
    current_streak = 0

    if today in parsed_dates:
        check_date = today
    elif yesterday in parsed_dates:
        check_date = yesterday
    else:
        return 0, longest_streak

    parsed_set = set(parsed_dates)
    while check_date in parsed_set:
        current_streak += 1
        check_date -= timedelta(days=1)

    return current_streak, max(longest_streak, current_streak)


def get_habit_history_last_7_days(completed_dates_set: Set[str]) -> List[Dict[str, Any]]:
    """Return completion status for each of the last 7 days (today down to 6 days ago)."""
    today = date.today()
    history = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        history.append({
            "date": day_str,
            "day_name": day.strftime("%a"),
            "completed": day_str in completed_dates_set
        })
    return history


def create_habit(db, data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Create a new habit."""
    is_valid, error = validate_habit_data(data)
    if not is_valid:
        return None, error

    name = data["name"].strip()
    description = (data.get("description") or "").strip()
    frequency = (data.get("frequency") or "daily").strip().lower()
    if frequency not in VALID_FREQUENCIES:
        frequency = "daily"

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO habits (name, description, frequency)
        VALUES (?, ?, ?);
    """, (name, description, frequency))
    db.commit()

    habit_id = cursor.lastrowid
    return get_habit_by_id(db, habit_id), None


def get_habit_by_id(db, habit_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single habit with calculated streak and today's status."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM habits WHERE id = ?;", (habit_id,))
    row = cursor.fetchone()
    if not row:
        return None

    today_str = date.today().isoformat()
    cursor.execute("SELECT date FROM habit_logs WHERE habit_id = ?;", (habit_id,))
    log_rows = cursor.fetchall()
    completed_dates = {r["date"] for r in log_rows}

    current_streak, longest_streak = calculate_habit_streaks(completed_dates)
    is_completed_today = today_str in completed_dates
    history = get_habit_history_last_7_days(completed_dates)

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "frequency": row["frequency"],
        "created_at": row["created_at"],
        "is_completed_today": is_completed_today,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_completions": len(completed_dates),
        "history_7_days": history
    }


def get_habits(db) -> List[Dict[str, Any]]:
    """Retrieve all habits with real streak calculations and today's completion status."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM habits ORDER BY id ASC;")
    habit_rows = cursor.fetchall()

    today_str = date.today().isoformat()
    result = []

    for row in habit_rows:
        h_id = row["id"]
        cursor.execute("SELECT date FROM habit_logs WHERE habit_id = ?;", (h_id,))
        log_rows = cursor.fetchall()
        completed_dates = {r["date"] for r in log_rows}

        current_streak, longest_streak = calculate_habit_streaks(completed_dates)
        is_completed_today = today_str in completed_dates
        history = get_habit_history_last_7_days(completed_dates)

        result.append({
            "id": h_id,
            "name": row["name"],
            "description": row["description"] or "",
            "frequency": row["frequency"],
            "created_at": row["created_at"],
            "is_completed_today": is_completed_today,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_completions": len(completed_dates),
            "history_7_days": history
        })

    return result


def update_habit(db, habit_id: int, data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Update habit details."""
    existing = get_habit_by_id(db, habit_id)
    if not existing:
        return None, "Habit not found."

    is_valid, error = validate_habit_data(data, is_update=True)
    if not is_valid:
        return None, error

    name = data.get("name", existing["name"]).strip()
    description = (data.get("description", existing["description"]) or "").strip()
    frequency = data.get("frequency", existing["frequency"]).strip().lower()
    if frequency not in VALID_FREQUENCIES:
        frequency = existing["frequency"]

    cursor = db.cursor()
    cursor.execute("""
        UPDATE habits
        SET name = ?, description = ?, frequency = ?
        WHERE id = ?;
    """, (name, description, frequency, habit_id))
    db.commit()

    return get_habit_by_id(db, habit_id), None


def delete_habit(db, habit_id: int) -> bool:
    """Delete habit and its logs."""
    cursor = db.cursor()
    # Delete logs explicitly in case foreign keys cascade is not configured or in in-memory mode
    cursor.execute("DELETE FROM habit_logs WHERE habit_id = ?;", (habit_id,))
    cursor.execute("DELETE FROM habits WHERE id = ?;", (habit_id,))
    db.commit()
    return cursor.rowcount > 0


def toggle_habit_completion(db, habit_id: int, target_date: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Toggle completion for a habit on a given date (defaults to today).
    If already completed for date, remove completion record (undo).
    If not completed, add record.
    Prevents duplicate completion records.
    """
    existing = get_habit_by_id(db, habit_id)
    if not existing:
        return None, "Habit not found."

    if not target_date:
        target_date = date.today().isoformat()
    else:
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            return None, "Invalid date format. Expected YYYY-MM-DD."

    cursor = db.cursor()
    cursor.execute("SELECT id FROM habit_logs WHERE habit_id = ? AND date = ?;", (habit_id, target_date))
    existing_log = cursor.fetchone()

    if existing_log:
        # Undo completion
        cursor.execute("DELETE FROM habit_logs WHERE habit_id = ? AND date = ?;", (habit_id, target_date))
        db.commit()
        toggled_status = False
    else:
        # Mark completed (using INSERT OR IGNORE to safeguard against race conditions)
        cursor.execute("""
            INSERT OR IGNORE INTO habit_logs (habit_id, date)
            VALUES (?, ?);
        """, (habit_id, target_date))
        db.commit()
        toggled_status = True

    updated_habit = get_habit_by_id(db, habit_id)
    return {
        "habit": updated_habit,
        "target_date": target_date,
        "is_completed": toggled_status
    }, None


def get_habit_stats(db) -> Dict[str, Any]:
    """Calculate habit statistics for today."""
    today_str = date.today().isoformat()
    habits = get_habits(db)
    total_habits = len(habits)

    completed_today = sum(1 for h in habits if h["is_completed_today"])
    pending_today = total_habits - completed_today

    completion_rate = 0
    if total_habits > 0:
        completion_rate = round((completed_today / total_habits) * 100)

    # Highest current streak across all habits
    max_streak = max((h["current_streak"] for h in habits), default=0)

    return {
        "total": total_habits,
        "completed_today": completed_today,
        "pending_today": pending_today,
        "completion_rate": completion_rate,
        "max_current_streak": max_streak
    }
