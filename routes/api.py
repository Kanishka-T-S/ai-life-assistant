import time
import logging
from datetime import date
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
from database import get_db
from services.task_service import (
    create_task,
    get_tasks,
    get_task_by_id,
    update_task,
    toggle_task_completion,
    delete_task,
    get_task_stats
)
from services.habit_service import (
    create_habit,
    get_habits,
    get_habit_by_id,
    update_habit,
    delete_habit,
    toggle_habit_completion,
    get_habit_stats
)
from services.ai_service import (
    chat_with_assistant,
    is_quota_exhausted,
    reset_quota_state,
    get_quota_remaining_cooldown
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

DAILY_QUOTES = [
    {"quote": "Small daily improvements over time lead to stunning results.", "author": "Robin Sharma"},
    {"quote": "Focus on being productive instead of busy.", "author": "Tim Ferriss"},
    {"quote": "You do not rise to the level of your goals. You fall to the level of your systems.", "author": "James Clear"},
    {"quote": "Action is the foundational key to all success.", "author": "Pablo Picasso"},
    {"quote": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"quote": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"quote": "Discipline is choosing between what you want now and what you want most.", "author": "Abraham Lincoln"},
]


# ==========================================
# DASHBOARD STATS
# ==========================================
@api_bp.route("/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    """Return aggregated stats for tasks, habits, and productivity."""
    db = get_db()
    today = date.today()
    today_iso = today.isoformat()
    today_formatted = today.strftime("%A, %B %d, %Y")

    task_stats = get_task_stats(db)
    habit_stats = get_habit_stats(db)

    # Calculate overall productivity score (0 - 100)
    # Balanced between today's task completion and today's habit completion
    weights = []
    if task_stats["today_total"] > 0:
        weights.append(task_stats["today_completion_rate"])
    elif task_stats["total"] > 0:
        weights.append(task_stats["completion_rate"])

    if habit_stats["total"] > 0:
        weights.append(habit_stats["completion_rate"])

    if weights:
        productivity_score = round(sum(weights) / len(weights))
    else:
        productivity_score = 0

    # Pick daily quote based on day of year
    day_of_year = today.timetuple().tm_yday
    quote_obj = DAILY_QUOTES[day_of_year % len(DAILY_QUOTES)]

    # Fetch next 5 upcoming pending tasks
    upcoming_tasks = get_tasks(db, status_filter="pending", sort_by="due_date_asc")[:5]

    # Check whether Gemini key is set and quota status
    has_api_key = bool(current_app.config.get("GEMINI_API_KEY", "").strip())
    quota_exhausted = is_quota_exhausted()

    if not has_api_key:
        ai_model_desc = "Demo Mode (Simulated)"
    elif quota_exhausted:
        ai_model_desc = "Quota Reached (Demo Fallback Available)"
    else:
        ai_model_desc = current_app.config.get("GEMINI_MODEL", "gemini-3.8-flash")

    return jsonify({
        "success": True,
        "date": {
            "iso": today_iso,
            "formatted": today_formatted
        },
        "tasks": task_stats,
        "habits": habit_stats,
        "productivity_score": productivity_score,
        "daily_quote": quote_obj,
        "upcoming_tasks": upcoming_tasks,
        "ai_status": {
            "is_demo": not has_api_key,
            "quota_exhausted": quota_exhausted,
            "cooldown_remaining_sec": get_quota_remaining_cooldown(),
            "model": ai_model_desc
        }
    }), 200


# ==========================================
# TASK MANAGEMENT ENDPOINTS
# ==========================================
@api_bp.route("/tasks", methods=["GET"])
def list_tasks():
    """Retrieve tasks with optional filtering, search, and sorting."""
    db = get_db()
    status_filter = request.args.get("status", "all")
    priority_filter = request.args.get("priority", "all")
    category_filter = request.args.get("category", "all")
    search_query = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "due_date_asc")

    tasks = get_tasks(
        db,
        status_filter=status_filter,
        priority_filter=priority_filter,
        category_filter=category_filter,
        search_query=search_query,
        sort_by=sort_by
    )
    return jsonify({"success": True, "count": len(tasks), "tasks": tasks}), 200


@api_bp.route("/tasks", methods=["POST"])
def add_task():
    """Create a new task."""
    data = request.get_json(silent=True) or {}
    db = get_db()
    task, error = create_task(db, data)
    if error:
        return jsonify({"success": False, "error": error}), 400
    return jsonify({"success": True, "task": task}), 201


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id: int):
    """Get single task by ID."""
    db = get_db()
    task = get_task_by_id(db, task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found."}), 404
    return jsonify({"success": True, "task": task}), 200


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def edit_task(task_id: int):
    """Update task details."""
    data = request.get_json(silent=True) or {}
    db = get_db()
    task, error = update_task(db, task_id, data)
    if error:
        status_code = 404 if error == "Task not found." else 400
        return jsonify({"success": False, "error": error}), status_code
    return jsonify({"success": True, "task": task}), 200


@api_bp.route("/tasks/<int:task_id>/toggle", methods=["PATCH"])
def toggle_task(task_id: int):
    """Toggle completed/pending status of a task."""
    db = get_db()
    task, error = toggle_task_completion(db, task_id)
    if error:
        return jsonify({"success": False, "error": error}), 404
    return jsonify({"success": True, "task": task}), 200


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def remove_task(task_id: int):
    """Delete a task."""
    db = get_db()
    deleted = delete_task(db, task_id)
    if not deleted:
        return jsonify({"success": False, "error": "Task not found."}), 404
    return jsonify({"success": True, "message": "Task deleted successfully."}), 200


# ==========================================
# HABIT TRACKER ENDPOINTS
# ==========================================
@api_bp.route("/habits", methods=["GET"])
def list_habits():
    """Retrieve all habits with streaks and today's status."""
    db = get_db()
    habits = get_habits(db)
    return jsonify({"success": True, "count": len(habits), "habits": habits}), 200


@api_bp.route("/habits", methods=["POST"])
def add_habit():
    """Create a new habit."""
    data = request.get_json(silent=True) or {}
    db = get_db()
    habit, error = create_habit(db, data)
    if error:
        return jsonify({"success": False, "error": error}), 400
    return jsonify({"success": True, "habit": habit}), 201


@api_bp.route("/habits/<int:habit_id>", methods=["GET"])
def get_habit(habit_id: int):
    """Get single habit with streak details."""
    db = get_db()
    habit = get_habit_by_id(db, habit_id)
    if not habit:
        return jsonify({"success": False, "error": "Habit not found."}), 404
    return jsonify({"success": True, "habit": habit}), 200


@api_bp.route("/habits/<int:habit_id>", methods=["PUT"])
def edit_habit(habit_id: int):
    """Update habit details."""
    data = request.get_json(silent=True) or {}
    db = get_db()
    habit, error = update_habit(db, habit_id, data)
    if error:
        status_code = 404 if error == "Habit not found." else 400
        return jsonify({"success": False, "error": error}), status_code
    return jsonify({"success": True, "habit": habit}), 200


@api_bp.route("/habits/<int:habit_id>", methods=["DELETE"])
def remove_habit(habit_id: int):
    """Delete a habit."""
    db = get_db()
    deleted = delete_habit(db, habit_id)
    if not deleted:
        return jsonify({"success": False, "error": "Habit not found."}), 404
    return jsonify({"success": True, "message": "Habit deleted successfully."}), 200


@api_bp.route("/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle_habit(habit_id: int):
    """Toggle completion for today or given date."""
    data = request.get_json(silent=True) or {}
    target_date = data.get("date")
    db = get_db()
    result, error = toggle_habit_completion(db, habit_id, target_date)
    if error:
        status_code = 404 if error == "Habit not found." else 400
        return jsonify({"success": False, "error": error}), status_code
    return jsonify({"success": True, "data": result}), 200


# ==========================================
# DAILY PLANNER SUMMARY
# ==========================================
@api_bp.route("/planner/summary", methods=["GET"])
def get_planner_summary():
    """Retrieve structured data for the Daily Planner view."""
    db = get_db()
    today_str = date.today().isoformat()

    overdue_tasks = get_tasks(db, status_filter="overdue")
    today_tasks = get_tasks(db, status_filter="today", sort_by="priority_desc")
    pending_tasks = get_tasks(db, status_filter="pending", sort_by="priority_desc")
    habits = get_habits(db)

    return jsonify({
        "success": True,
        "date": today_str,
        "overdue_tasks": overdue_tasks,
        "today_tasks": today_tasks,
        "high_priority_pending": [t for t in pending_tasks if t["priority"] == "High"],
        "active_habits": habits,
        "disclaimer": "AI-generated schedules and priority lists are smart suggestions for guidance, not guaranteed calendar syncs."
    }), 200


# ==========================================
# AI CHAT ASSISTANT
# ==========================================
@api_bp.route("/chat", methods=["POST"])
def chat():
    """Conversational AI assistant endpoint with latency tracking and quota/rate-limit handling."""
    start_req = time.perf_counter()
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    history = data.get("history", [])
    fallback_to_demo = bool(
        data.get("fallback_to_demo") or data.get("use_demo") or data.get("allow_demo_fallback")
    )

    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"success": False, "error": "Message prompt is required."}), 400

    if len(prompt.strip()) > 2000:
        return jsonify({"success": False, "error": "Message is too long. Limit is 2000 characters."}), 400

    db = get_db()
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    model_name = current_app.config.get("GEMINI_MODEL", "gemini-3.8-flash")
    timeout_sec = current_app.config.get("GEMINI_TIMEOUT_SECONDS", 10)

    result = chat_with_assistant(
        prompt=prompt,
        db=db,
        session_history=history,
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=timeout_sec,
        fallback_to_demo=fallback_to_demo
    )

    total_latency = time.perf_counter() - start_req
    api_latency = result.get("api_latency", 0.0)

    # Log measured latency
    print(f"[Latency] /api/chat total: {total_latency:.3f}s | Gemini API: {api_latency:.3f}s | Model: {result.get('model')}")
    logger.info(
        "/api/chat total: %.3fs | Gemini API: %.3fs | Model: %s",
        total_latency, api_latency, result.get("model")
    )

    result["timing"] = {
        "api_latency_sec": round(api_latency, 3),
        "total_latency_sec": round(total_latency, 3)
    }

    if not result.get("success"):
        if result.get("is_quota_exhausted"):
            status_code = 429
        elif result.get("is_timeout"):
            status_code = 504
        elif not result.get("is_demo"):
            status_code = 503
        else:
            status_code = 400
        return jsonify(result), status_code

    return jsonify(result), 200


@api_bp.route("/ai/status", methods=["GET"])
def get_ai_status():
    """Return status of live Gemini integration and quota state."""
    has_api_key = bool(current_app.config.get("GEMINI_API_KEY", "").strip())
    quota_exhausted = is_quota_exhausted()
    return jsonify({
        "success": True,
        "has_api_key": has_api_key,
        "is_quota_exhausted": quota_exhausted,
        "cooldown_remaining_sec": get_quota_remaining_cooldown(),
        "model": current_app.config.get("GEMINI_MODEL", "gemini-3.8-flash")
    }), 200


@api_bp.route("/ai/reset-quota", methods=["POST"])
def reset_quota():
    """Admin/testing endpoint to reset quota cooldown."""
    reset_quota_state()
    return jsonify({
        "success": True,
        "message": "AI quota cooldown has been reset."
    }), 200
