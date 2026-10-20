import os
import logging
from datetime import date
from typing import Any, Dict, List, Optional
from services.task_service import get_tasks, get_task_stats
from services.habit_service import get_habits, get_habit_stats

logger = logging.getLogger(__name__)

# Try importing the official Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False


def build_system_context(db) -> str:
    """
    Assemble real database context (today's tasks, pending tasks, overdue tasks,
    and active habits) to ground the AI's responses in user data.
    """
    today_str = date.today().strftime("%A, %B %d, %Y")
    task_stats = get_task_stats(db)
    habit_stats = get_habit_stats(db)

    pending_tasks = get_tasks(db, status_filter="pending", sort_by="priority_desc")
    overdue_tasks = get_tasks(db, status_filter="overdue")
    habits = get_habits(db)

    task_summary_lines = []
    for t in pending_tasks[:10]:
        due = f", due: {t['due_date']}" if t['due_date'] else ""
        task_summary_lines.append(f"- [{t['priority']}] {t['title']} ({t['category']}{due})")

    habit_summary_lines = []
    for h in habits:
        status = "Completed today" if h["is_completed_today"] else "Pending today"
        habit_summary_lines.append(f"- {h['name']} ({status}, streak: {h['current_streak']} days)")

    overdue_count = len(overdue_tasks)

    context = f"""
Current Date: {today_str}
Assistant Persona: AI Life Assistant – Your Smart Everyday Companion.
Tone: Encouraging, concise, practical, structured, friendly.

User's Real Productivity Data:
- Pending Tasks: {task_stats['pending']} (Overdue: {overdue_count}, High Priority: {task_stats['high_priority_pending']})
- Tasks Due Today: {task_stats['today_total']} ({task_stats['today_completed']} completed)
- Active Habits: {habit_stats['total']} ({habit_stats['completed_today']} completed today)

Top Pending Tasks:
{chr(10).join(task_summary_lines) if task_summary_lines else "No pending tasks."}

Active Habits:
{chr(10).join(habit_summary_lines) if habit_summary_lines else "No habits configured yet."}

Important Rules:
1. Always base daily plans and task recommendations on the user's actual tasks and habits listed above.
2. AI-generated schedules and recommendations are suggestions for guidance, NOT calendar commitments.
3. Never claim to automatically create, modify, or delete user tasks or habits without their explicit confirmation.
4. Keep advice actionable and avoid overwhelming the user with long walls of text.
"""
    return context.strip()


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
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main conversational assistant handler.
    1. If a valid Gemini API key is configured and SDK is present, calls the live Gemini API
       with rich system instructions and real database context.
    2. If no key is set or if an API error occurs, seamlessly provides a clearly labeled
       Demo Mode response.
    """
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        return {
            "success": False,
            "error": "Message prompt cannot be empty.",
            "response": "",
            "is_demo": True,
            "model": "None"
        }

    clean_prompt = prompt.strip()
    system_context = build_system_context(db)

    # Check if API key is provided
    if api_key is None:
        effective_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    else:
        effective_api_key = str(api_key).strip()

    if model_name is None:
        effective_model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
    else:
        effective_model = str(model_name).strip()

    if not effective_api_key or not HAS_GENAI_SDK:
        # Running in Demo Mode
        demo_text = generate_demo_response(clean_prompt, db)
        return {
            "success": True,
            "response": demo_text,
            "is_demo": True,
            "model": "Demo Mode (Simulated Assistant)",
            "notice": "Operating in Demo Mode. To connect live Gemini AI, set GEMINI_API_KEY in your .env file."
        }

    # Live Gemini API execution
    try:
        client = genai.Client(api_key=effective_api_key)

        # Build prompt with system context and conversation context
        full_prompt = f"{system_context}\n\nUser Question: {clean_prompt}"

        # If previous history exists, format the last 2 turns
        if session_history and isinstance(session_history, list):
            history_snippets = []
            for item in session_history[-4:]:
                role = "User" if item.get("role") == "user" else "Assistant"
                content = item.get("content", "")
                history_snippets.append(f"{role}: {content}")
            if history_snippets:
                full_prompt = f"{system_context}\n\nRecent Conversation:\n{chr(10).join(history_snippets)}\n\nUser Question: {clean_prompt}"

        response = client.models.generate_content(
            model=effective_model,
            contents=full_prompt,
        )

        reply_text = response.text if hasattr(response, "text") and response.text else "I was unable to generate a response. Please try again."

        return {
            "success": True,
            "response": reply_text,
            "is_demo": False,
            "model": effective_model,
            "notice": None
        }

    except Exception as exc:
        # Graceful fallback on API error (e.g. quota, high demand, offline)
        error_msg = str(exc)
        # Redact any accidental credential leak from error messages
        if effective_api_key and effective_api_key in error_msg:
            error_msg = error_msg.replace(effective_api_key, "[REDACTED_API_KEY]")

        logger.warning(
            "Gemini API call to model '%s' failed (%s: %s). Falling back to Demo Mode.",
            effective_model,
            type(exc).__name__,
            error_msg[:200]
        )
        print(f"[Gemini API Warning] Model '{effective_model}' unavailable ({type(exc).__name__}: {error_msg[:120]}). Falling back to Demo Mode.")

        fallback_response = generate_demo_response(clean_prompt, db)
        return {
            "success": True,
            "response": fallback_response,
            "is_demo": True,
            "model": "Demo Mode (API Fallback)",
            "notice": f"Live Gemini API was unavailable ({error_msg[:120]}...). Served high-fidelity Demo Mode response."
        }
