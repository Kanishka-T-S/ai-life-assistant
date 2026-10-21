import os
import re
import time
import logging
from datetime import date
from typing import Any, Dict, List, Optional
from services.task_service import get_tasks, get_task_stats
from services.habit_service import get_habits, get_habit_stats

logger = logging.getLogger(__name__)

# Try importing the official Google GenAI SDK
try:
    from google import genai
    from google.genai import types, errors
    HAS_GENAI_SDK = True
except ImportError:
    genai = None
    types = None
    errors = None
    HAS_GENAI_SDK = False

# ==========================================
# QUOTA & RATE LIMIT CONFIGURATION & STATE
# ==========================================
QUOTA_FRIENDLY_MESSAGE = (
    "Live AI is temporarily unavailable because the API quota has been reached. "
    "You can still use Tasks and Habits."
)
DEFAULT_QUOTA_COOLDOWN_SECONDS = 60

_quota_exhausted_until: float = 0.0
_quota_exhaustion_reason: str = ""


def is_quota_exhausted() -> bool:
    """Return True if the Gemini API quota is currently marked as exhausted."""
    return time.time() < _quota_exhausted_until


def set_quota_exhausted(cooldown_seconds: int = DEFAULT_QUOTA_COOLDOWN_SECONDS, reason: str = "") -> None:
    """Mark the Gemini API quota as exhausted for a given cooldown window."""
    global _quota_exhausted_until, _quota_exhaustion_reason
    _quota_exhausted_until = time.time() + max(1, cooldown_seconds)
    _quota_exhaustion_reason = reason or "429 RESOURCE_EXHAUSTED"


def reset_quota_state() -> None:
    """Reset the quota exhaustion state (used for recovery and automated testing)."""
    global _quota_exhausted_until, _quota_exhaustion_reason
    _quota_exhausted_until = 0.0
    _quota_exhaustion_reason = ""


def get_quota_remaining_cooldown() -> int:
    """Return remaining cooldown in seconds, or 0 if quota is available."""
    remaining = _quota_exhausted_until - time.time()
    return max(0, int(remaining))


def is_quota_or_rate_limit_error(exc: Exception) -> bool:
    """
    Detect whether an exception or error represents a 429 RESOURCE_EXHAUSTED
    or quota/rate-limit error from the Gemini API.
    """
    if exc is None:
        return False

    # Check status code or code attribute on exception
    code = getattr(exc, "code", None)
    if code == 429:
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True

    # Check google.genai ClientError / APIError specifics if available
    if HAS_GENAI_SDK and errors is not None:
        try:
            if isinstance(exc, (errors.APIError, errors.ClientError)):
                if getattr(exc, "code", None) == 429:
                    return True
        except Exception:
            pass

    # Inspect string representations
    msg = str(exc)
    msg_upper = msg.upper()
    msg_lower = msg.lower()

    if "RESOURCE_EXHAUSTED" in msg_upper:
        return True
    if "429" in msg:
        return True
    if "QUOTA" in msg_upper and any(word in msg_lower for word in ["exceeded", "exhausted", "reached", "limit"]):
        return True
    if "RATE LIMIT" in msg_upper or "RATELIMIT" in msg_upper or "TOO MANY REQUESTS" in msg_upper:
        return True

    return False


def sanitize_error_message(error_str: str, api_key: Optional[str] = None) -> str:
    """
    Redact any accidental credential leaks from error messages or logs.
    Never exposes raw API keys.
    """
    if not error_str:
        return ""
    sanitized = str(error_str)
    if api_key and api_key.strip():
        sanitized = sanitized.replace(api_key.strip(), "[REDACTED_API_KEY]")
    # Redact typical Google API key pattern (AIzaSy...)
    sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_API_KEY]", sanitized)
    return sanitized



def build_system_context(db) -> str:
    """
    Assemble a lightweight, minimal context containing only relevant pending tasks
    and today's habit summary to minimize prompt token overhead and latency.
    """
    today_str = date.today().isoformat()
    cursor = db.cursor()

    # Fetch top pending tasks (limit to 5: prioritize overdue, today, High priority)
    cursor.execute("""
        SELECT title, priority, due_date, category
        FROM tasks
        WHERE is_completed = 0
        ORDER BY
            CASE WHEN due_date != '' AND due_date < ? THEN 0
                 WHEN due_date = ? THEN 1
                 WHEN priority = 'High' THEN 2
                 WHEN priority = 'Medium' THEN 3
                 ELSE 4 END ASC,
            due_date ASC
        LIMIT 5;
    """, (today_str, today_str))
    task_rows = cursor.fetchall()

    tasks_context = []
    for r in task_rows:
        due = f" (due {r['due_date']})" if r["due_date"] else ""
        tasks_context.append(f"- [{r['priority']}] {r['title']}{due}")

    # Fetch today's habit status in a single query
    cursor.execute("""
        SELECT h.name,
               CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END as completed_today
        FROM habits h
        LEFT JOIN habit_logs l ON h.id = l.habit_id AND l.date = ?
        LIMIT 5;
    """, (today_str,))
    habit_rows = cursor.fetchall()

    total_habits = len(habit_rows)
    done_habits = sum(1 for h in habit_rows if h["completed_today"])
    pending_habits = [h["name"] for h in habit_rows if not h["completed_today"]]

    habits_summary = f"{done_habits}/{total_habits} done today"
    if pending_habits:
        habits_summary += f" (pending: {', '.join(pending_habits[:3])})"

    task_str = "\n".join(tasks_context) if tasks_context else "None"
    return f"Today: {today_str}\nPending Tasks:\n{task_str}\nHabits: {habits_summary}"


def generate_demo_response(prompt: str, db) -> str:
    """
    Generate rich, deterministic, contextual responses when running in Demo Mode
    (e.g., when no Gemini API key is configured).
    """
    prompt_lower = prompt.lower().strip()
    task_stats = get_task_stats(db)
    habit_stats = get_habit_stats(db)
    pending_tasks = get_tasks(db, status_filter="pending", sort_by="priority_desc")
    overdue_tasks = get_tasks(db, status_filter="overdue")
    habits = get_habits(db)
    today_str = date.today().strftime("%A, %B %d")

    # 1. "Plan my day"
    if any(k in prompt_lower for k in ["plan my day", "daily plan", "schedule my day", "plan today"]):
        high_p = [t for t in pending_tasks if t["priority"] == "High"]
        med_p = [t for t in pending_tasks if t["priority"] == "Medium"]
        low_p = [t for t in pending_tasks if t["priority"] == "Low"]

        plan = f"### 📅 Suggested Daily Plan for {today_str}\n\n"
        if overdue_tasks:
            plan += f"⚠️ **Attention:** You have **{len(overdue_tasks)} overdue task(s)**. Let's tackle these first!\n\n"

        plan += "Here is your suggested focus roadmap for today:\n\n"
        plan += "**🌅 Morning (Peak Energy & Focus):**\n"
        if high_p:
            plan += f"- **High Priority Focus:** {high_p[0]['title']} ({high_p[0]['category']})\n"
        else:
            plan += "- Deep work session on your primary goal\n"
        if habits:
            plan += f"- Morning Habit: Check in on *{habits[0]['name']}*\n"

        plan += "\n**☀️ Afternoon (Productive Momentum):**\n"
        if len(high_p) > 1:
            plan += f"- Tackle: {high_p[1]['title']}\n"
        elif med_p:
            plan += f"- Work on: {med_p[0]['title']} ({med_p[0]['category']})\n"
        else:
            plan += "- Complete routine admin and ongoing projects\n"

        plan += "\n**🌆 Evening (Wrap-up & Recharge):**\n"
        if low_p:
            plan += f"- Light task: {low_p[0]['title']}\n"
        plan += f"- Review today's habit completions ({habit_stats['completed_today']}/{habit_stats['total']} completed)\n"
        plan += "- Prep tomorrow's top 3 priorities\n\n"
        plan += "> *Note: This schedule is an AI-suggested guide. Adjust blocks to fit your natural energy rhythms.*"
        return plan

    # 2. "Help me prioritize my tasks"
    if any(k in prompt_lower for k in ["prioritize", "priority", "what should i do first"]):
        if not pending_tasks:
            return "🎉 **Great job!** You currently have no pending tasks. Take a moment to celebrate or use the **'+ New Task'** button to map out your upcoming goals."

        resp = "### 🎯 Prioritization Breakdown\n\n"
        if overdue_tasks:
            resp += f"🔥 **Urgent & Overdue ({len(overdue_tasks)}):**\n"
            for t in overdue_tasks[:3]:
                resp += f"- **{t['title']}** (Was due {t['due_date']})\n"
            resp += "\n"

        high_tasks = [t for t in pending_tasks if t["priority"] == "High"]
        med_tasks = [t for t in pending_tasks if t["priority"] == "Medium"]
        low_tasks = [t for t in pending_tasks if t["priority"] == "Low"]

        if high_tasks:
            resp += f"⚡ **High Priority (Do Today - Next):**\n"
            for t in high_tasks[:3]:
                due = f" — Due: {t['due_date']}" if t['due_date'] else ""
                resp += f"- **{t['title']}** [{t['category']}]{due}\n"
            resp += "\n"

        if med_tasks:
            resp += f"📋 **Medium Priority (Schedule Next):**\n"
            for t in med_tasks[:3]:
                resp += f"- {t['title']} [{t['category']}]\n"
            resp += "\n"

        if low_tasks:
            resp += f"💡 **Low Priority (When time permits):**\n"
            for t in low_tasks[:2]:
                resp += f"- {t['title']}\n"
            resp += "\n"

        resp += "**Next Action Step:** Pick the first item from the High Priority list and work on it for 25 uninterrupted minutes."
        return resp

    # 3. "Summarize my pending tasks"
    if any(k in prompt_lower for k in ["summarize", "summary", "pending tasks", "list my tasks"]):
        if not pending_tasks:
            return "You have **0 pending tasks** right now! All your recorded tasks are completed."

        summary = f"### 📊 Pending Tasks Summary\n\n"
        summary += f"You have **{len(pending_tasks)} pending task(s)** across your workspace:\n\n"
        for i, t in enumerate(pending_tasks[:8], 1):
            due_badge = f" (📅 {t['due_date']})" if t['due_date'] else " (No due date)"
            summary += f"{i}. **[{t['priority']}]** {t['title']} — *{t['category']}*{due_badge}\n"

        if len(pending_tasks) > 8:
            summary += f"\n*...and {len(pending_tasks) - 8} more in your task list.*\n"

        summary += f"\n**Overdue:** {len(overdue_tasks)} | **High Priority:** {task_stats['high_priority_pending']}"
        return summary

    # 4. "Help me build a study habit" or habit building
    if any(k in prompt_lower for k in ["study habit", "build a habit", "build habit", "habit"]):
        return (
            "### 📚 Science-Backed Habit Building Guide\n\n"
            "To build an enduring habit (like studying or reading), use the **Atomic Habits 4-Step Loop**:\n\n"
            "1. **Make it Obvious (The Cue):** Anchor your habit to an existing routine. *Example: 'Right after I pour my morning coffee, I will open my study notes for 15 minutes.'*\n"
            "2. **Make it Easy (Low Friction):** Start ridiculously small. Don't commit to 2 hours on day one; commit to **10 minutes** so starting requires zero willpower.\n"
            "3. **Make it Attractive:** Pair the habit with something enjoyable (e.g., favorite instrumental playlist or a warm beverage).\n"
            "4. **Make it Satisfying (The Reward):** Mark your completion right here in the **Habit Tracker**! Watching your streak counter grow provides immediate dopamine.\n\n"
            "💡 *Tip: Click '+ New Habit' in the sidebar to add your study habit now.*"
        )

    # 5. "Suggest a productive daily routine"
    if any(k in prompt_lower for k in ["routine", "productive routine", "daily routine"]):
        return (
            "### ⚡ The Ideal 3-Phase Productivity Routine\n\n"
            "Here is a balanced daily rhythm designed for sustainable focus:\n\n"
            "**1. Morning Clarity Window (first 90 mins):**\n"
            "- Hydrate and avoid instant notifications/social media.\n"
            "- Review today's 3 Must-Win tasks.\n"
            "- Complete a 50-minute deep work sprint while willpower is highest.\n\n"
            "**2. Afternoon Momentum Engine:**\n"
            "- Group communication, meetings, and secondary tasks.\n"
            "- Use the 25/5 Pomodoro method to avoid cognitive fatigue.\n"
            "- Take a brief 10-minute walk after lunch to restore focus.\n\n"
            "**3. Evening Reset (last 30 mins of workday):**\n"
            "- Check off completed tasks and habits.\n"
            "- Clear your workspace.\n"
            "- Jot down your top task for tomorrow so your mind can rest."
        )

    # General questions fallback
    return (
        f"Hello! I am your **AI Life Assistant**. "
        f"You currently have **{task_stats['pending']} pending task(s)** and **{habit_stats['completed_today']}/{habit_stats['total']} habits** completed today.\n\n"
        f"Regarding *\"{prompt}\"*: As your companion, I can help you plan schedules, break down complex projects, prioritize tasks, and maintain streaks.\n\n"
        f"Try asking:\n"
        f"- *'Plan my day.'*\n"
        f"- *'Help me prioritize my tasks.'*\n"
        f"- *'Summarize my pending tasks.'*\n"
        f"- *'Suggest a productive daily routine.'*"
    )


def chat_with_assistant(
    prompt: str,
    db,
    session_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    fallback_to_demo: bool = False,
    cooldown_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main conversational assistant handler with latency measurement, fast timeout,
    and graceful handling of 429 RESOURCE_EXHAUSTED quota and rate limit errors.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        return {
            "success": False,
            "error": "Message prompt cannot be empty.",
            "response": "",
            "is_demo": True,
            "is_quota_fallback": False,
            "model": "None",
            "api_latency": 0.0
        }

    clean_prompt = prompt.strip()
    system_context = build_system_context(db)

    # Check if API key is provided
    if api_key is None:
        effective_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    else:
        effective_api_key = str(api_key).strip()

    if model_name is None:
        effective_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    else:
        effective_model = str(model_name).strip()

    effective_timeout = timeout_seconds or int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "15"))

    # Standard Demo Mode when no API key configured
    if not effective_api_key or not HAS_GENAI_SDK:
        t_demo_start = time.perf_counter()
        demo_text = generate_demo_response(clean_prompt, db)
        demo_latency = time.perf_counter() - t_demo_start
        return {
            "success": True,
            "response": demo_text,
            "is_demo": True,
            "is_quota_fallback": False,
            "is_timeout_fallback": False,
            "model": "Demo Mode (Simulated Assistant)",
            "api_latency": round(demo_latency, 4),
            "notice": "Operating in Demo Mode. To connect live Gemini AI, set GEMINI_API_KEY in your .env file."
        }

    # Avoid repeatedly retrying requests when the quota is known to be exhausted
    if is_quota_exhausted():
        logger.info("Skipping live Gemini API call: quota cooldown active (%ds remaining).", get_quota_remaining_cooldown())
        if fallback_to_demo:
            t_demo_start = time.perf_counter()
            demo_text = generate_demo_response(clean_prompt, db)
            demo_latency = time.perf_counter() - t_demo_start
            return {
                "success": True,
                "response": demo_text,
                "is_demo": True,
                "is_quota_fallback": True,
                "is_timeout_fallback": False,
                "model": "Demo Mode (Simulated Assistant - Quota Fallback)",
                "api_latency": round(demo_latency, 4),
                "notice": QUOTA_FRIENDLY_MESSAGE
            }
        else:
            return {
                "success": False,
                "error": QUOTA_FRIENDLY_MESSAGE,
                "is_quota_exhausted": True,
                "cooldown_remaining": get_quota_remaining_cooldown(),
                "fallback_available": True,
                "is_demo": False,
                "is_quota_fallback": False,
                "is_timeout_fallback": False,
                "model": effective_model,
                "api_latency": 0.0,
                "notice": "Live AI request paused because API quota was reached. Demo Mode is available as a simulated fallback."
            }

    # Live Gemini API execution with latency timing and timeout limits
    start_api = time.perf_counter()
    try:
        client = genai.Client(api_key=effective_api_key)

        system_instruction = (
            "You are AI Life Assistant – a smart, practical everyday productivity companion. "
            "Keep answers concise, direct, and actionable (maximum 2-3 short paragraphs or bullet points). "
            "Ground recommendations in the user's provided tasks and habits. "
            "Clarify that schedules are flexible suggestions."
        )

        retry_options = types.HttpRetryOptions(attempts=1)
        http_options = types.HttpOptions(
            timeout=effective_timeout * 1000,
            retry_options=retry_options
        )

        config = types.GenerateContentConfig(
            max_output_tokens=800,
            temperature=0.7,
            system_instruction=f"{system_instruction}\n\n{system_context}",
            http_options=http_options
        )

        # Include at most the last 2 turns of conversation history to prevent latency bloat
        user_content = clean_prompt
        if session_history and isinstance(session_history, list):
            recent_turns = []
            for item in session_history[-2:]:
                r = "User" if item.get("role") == "user" else "Assistant"
                c = item.get("content", "").strip()
                if c:
                    recent_turns.append(f"{r}: {c[:200]}")
            if recent_turns:
                user_content = f"Recent History:\n{chr(10).join(recent_turns)}\n\nQuestion: {clean_prompt}"

        used_model = effective_model
        try:
            response = client.models.generate_content(
                model=effective_model,
                contents=user_content,
                config=config
            )
        except Exception as initial_exc:
            err_str = str(initial_exc).lower()
            # Do not retry if quota is exhausted, if request timed out, or if already on primary model
            is_quota = is_quota_or_rate_limit_error(initial_exc)
            is_to = (
                "timeout" in err_str
                or "deadline_exceeded" in err_str
                or "504" in err_str
                or isinstance(initial_exc, TimeoutError)
            )
            can_failover = (
                not is_quota
                and not is_to
                and effective_model != "gemini-3.5-flash-lite"
                and ("not_found" in err_str or "404" in err_str or "503" in err_str or "unavailable" in err_str)
            )
            if can_failover:
                logger.warning(
                    "Model '%s' failed (%s). Attempting failover to 'gemini-3.5-flash-lite'.",
                    effective_model,
                    type(initial_exc).__name__
                )
                used_model = "gemini-3.5-flash-lite"
                response = client.models.generate_content(
                    model=used_model,
                    contents=user_content,
                    config=config
                )
            else:
                raise initial_exc

        api_latency = time.perf_counter() - start_api

        # Safe extraction of text from response object
        reply_text = ""
        try:
            if hasattr(response, "text") and response.text:
                reply_text = response.text.strip()
        except Exception:
            pass

        if not reply_text and hasattr(response, "candidates") and response.candidates:
            try:
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts") and candidate.content.parts:
                        parts_text = [p.text for p in candidate.content.parts if hasattr(p, "text") and p.text]
                        if parts_text:
                            reply_text = "".join(parts_text).strip()
                            break
            except Exception:
                pass

        if not reply_text:
            reply_text = "I was unable to generate a response. Please try again."

        return {
            "success": True,
            "response": reply_text,
            "is_demo": False,
            "is_quota_fallback": False,
            "is_timeout_fallback": False,
            "model": used_model,
            "api_latency": round(api_latency, 3),
            "notice": None
        }

    except Exception as exc:
        api_latency = time.perf_counter() - start_api
        error_msg = sanitize_error_message(str(exc), effective_api_key)

        # 1. Detect quota exhaustion / rate limits (429 RESOURCE_EXHAUSTED)
        if is_quota_or_rate_limit_error(exc):
            effective_cooldown = cooldown_seconds or DEFAULT_QUOTA_COOLDOWN_SECONDS
            set_quota_exhausted(effective_cooldown, reason=error_msg[:120])
            logger.warning(
                "Gemini API quota exhausted (429 RESOURCE_EXHAUSTED) in %.2fs. Entering %ds cooldown. (%s)",
                api_latency,
                effective_cooldown,
                error_msg[:120]
            )

            if fallback_to_demo:
                t_demo_start = time.perf_counter()
                demo_text = generate_demo_response(clean_prompt, db)
                demo_latency = time.perf_counter() - t_demo_start
                return {
                    "success": True,
                    "response": demo_text,
                    "is_demo": True,
                    "is_quota_fallback": True,
                    "model": "Demo Mode (Simulated Assistant - Quota Fallback)",
                    "api_latency": round(demo_latency, 4),
                    "notice": QUOTA_FRIENDLY_MESSAGE
                }
            else:
                return {
                    "success": False,
                    "error": QUOTA_FRIENDLY_MESSAGE,
                    "is_quota_exhausted": True,
                    "cooldown_remaining": get_quota_remaining_cooldown(),
                    "fallback_available": True,
                    "is_demo": False,
                    "is_quota_fallback": False,
                    "model": effective_model,
                    "api_latency": round(api_latency, 3),
                    "notice": "Live AI quota reached. Demo Mode can be used explicitly as a simulated fallback."
                }


        # 2. Check for timeouts
        is_timeout = (
            "timeout" in error_msg.lower()
            or "deadline_exceeded" in error_msg.lower()
            or "504" in error_msg
            or (
                errors is not None
                and hasattr(errors, "httpx")
                and isinstance(
                    exc, (TimeoutError, errors.httpx.TimeoutException)
                )
            )
            or isinstance(exc, TimeoutError)
        )

        if is_timeout and fallback_to_demo:
            t_demo_start = time.perf_counter()
            demo_text = generate_demo_response(clean_prompt, db)
            demo_latency = time.perf_counter() - t_demo_start

            return {
                "success": True,
                "response": demo_text,
                "is_demo": True,
                "is_quota_fallback": False,
                "is_timeout_fallback": True,
                "model": "Demo Mode (Simulated Assistant - Timeout Fallback)",
                "api_latency": round(demo_latency, 4),
                "notice": (
                    f"Live Gemini AI timed out after {effective_timeout}s. "
                    "This response is simulated Demo Mode output."
                )
            }

        elif is_timeout:
            user_error = (
                f"The AI request timed out after {effective_timeout}s. "
                "Google's servers may be experiencing high demand. Please try again."
            )
        elif "503" in error_msg or "unavailable" in error_msg.lower():
            user_error = (
                "The Gemini model is temporarily experiencing high demand upstream. "
                "Please try again in a few moments."
            )
        else:
            user_error = f"Live Gemini AI encountered an error: {error_msg[:120]}."

        logger.warning(
            "Gemini API call to model '%s' failed in %.2fs (%s: %s).",
            effective_model,
            api_latency,
            type(exc).__name__,
            error_msg[:200]
        )

        return {
            "success": False,
            "error": user_error,
            "is_timeout": is_timeout,
            "is_quota_exhausted": False,
            "is_demo": False,
            "is_quota_fallback": False,
            "is_timeout_fallback": False,
            "model": effective_model,
            "api_latency": round(api_latency, 3),
            "notice": f"Upstream error: {error_msg[:100]}"
        }
