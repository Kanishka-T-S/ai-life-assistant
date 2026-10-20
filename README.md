# AI Life Assistant – Your Smart Everyday Companion

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg?logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-API_Enabled-4285F4.svg?logo=google&logoColor=white)](https://aistudio.google.com/)
[![Pytest](https://img.shields.io/badge/Tests-18_Passed-success.svg?logo=pytest)](https://pytest.org/)

**AI Life Assistant** is an intelligent, full-stack personal productivity dashboard and conversational companion. Built for the **Amazon Developer Hackathon (Alexa+ Simulated Experience Track)**, it provides an original, simulated conversational intelligence experience that helps users seamlessly organize daily commitments, cultivate long-term habits, plan focus schedules, and receive context-aware productivity coaching.

> **Hackathon Note:** This application is an independent simulation created for the *Alexa+ Simulated Experience* track. It provides an original productivity companion experience using the official Google Gemini SDK and does not use unofficial Amazon APIs or claim access to unintegrated Amazon services.

---

## 🌟 Key Features

### 1. 📊 Real-Time Interactive Dashboard
- **Dynamic Metrics:** Live counts for Pending Tasks, Completed Tasks, Active Habits, and Habit Completions Today directly from SQLite.
- **Productivity Progress Meter:** Real-time composite score combining task execution and habit streaks.
- **Daily Motivational Quote:** Curated inspirational wisdom rotated daily.
- **Quick-Action Strip:** One-click shortcuts to add tasks, log habits, or chat with the AI assistant.
- **Upcoming Tasks Feed:** Quick view of the next pending deadlines with inline completion checkboxes.

### 2. 🤖 Context-Aware AI Assistant & Demo Mode
- **Dual Operating Modes:**
  - **Live Gemini AI:** Powered by the official Google Gemini SDK (`google-genai`) with models like `gemini-3.8-flash`. The backend grounds the model with the user's real task list, overdue items, and habit streaks.
  - **Demo Mode (Simulated AI):** Zero-configuration fallback! If no `GEMINI_API_KEY` is present, the app automatically runs in a clearly labeled Demo Mode with deterministic, context-rich responses tailored to the user's data.
- **Suggested Prompt Chips:**
  - *"Plan my day."*
  - *"Help me prioritize my tasks."*
  - *"Suggest a productive daily routine."*
  - *"Help me build a study habit."*
  - *"Summarize my pending tasks."*
- **Conversational Memory:** Preserves multi-turn session context.
- **Keyboard Shortcuts:** Press `Enter` to send, `Shift + Enter` for a new line.

### 3. 📋 Complete Task Management (CRUD)
- **Create, Read, Update, Delete:** Add tasks with Title, Description, Due Date, Priority (`High`, `Medium`, `Low`), and Category (`Work`, `Personal`, `Study`, `Health`, etc.).
- **Live Filtering:** Filter by `All`, `Due Today`, `Pending`, `Completed`, or `Overdue`.
- **Search & Sort:** Instant debounced search across titles, descriptions, and categories; sort by Due Date (Earliest/Latest), Priority, or Date Added.
- **Inline Toggling:** Checkbox to immediately mark tasks completed or pending.

### 4. 🔥 Habit Tracker & Streak Engine
- **Accurate Streak Calculation:** Computes true continuous calendar streaks from SQLite completion logs.
- **Duplicate Prevention:** Database-level `UNIQUE(habit_id, date)` constraints prevent duplicate completions.
- **One-Click Toggle:** Click to mark done for today or undo accidental clicks.
- **7-Day Visual History:** Micro indicator circles showing completion status across the past 7 days.

### 5. 📅 Personalized Daily Planner
- **Overdue Attention Alert:** Automatically flags overdue tasks requiring immediate action.
- **Structured Time Blocks:** Breaks down focus into Morning Focus, Afternoon Execution, and Evening Wrap-up.
- **AI Integration:** One-click button to *"✨ Ask AI to Optimize My Day"*.
- **Ethical Assistant Guarantee:** Includes a clear disclaimer that AI schedules are suggestions for guidance, never modifying tasks without user confirmation.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, Vanilla CSS3 (Custom Design System, Glassmorphism, Dark Mode), Vanilla JavaScript |
| **Backend** | Python 3.12, Flask 3.1 |
| **Database** | SQLite3 with parameterized queries & foreign keys |
| **AI Integration** | Official Google GenAI Python SDK (`google-genai` v2.31+) with Demo Mode fallback |
| **Testing** | Pytest 9.1 with isolated test database fixtures |
| **Configuration** | Python-dotenv (`.env`) |

---

## 📁 Project Architecture

```
ai-life-assistant/
├── app.py                     # Flask application factory, entry point & error handlers
├── config.py                  # Environment loader & configuration classes
├── database.py                # SQLite connection lifecycle & schema migrations
├── requirements.txt           # Python package dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Excludes .env, virtual environments, *.db, and caches
├── routes/
│   ├── __init__.py
│   └── api.py                 # RESTful API endpoints (/api/tasks, /api/habits, /api/chat, etc.)
├── services/
│   ├── __init__.py
│   ├── task_service.py        # Task CRUD, search, filter, and stats calculation logic
│   ├── habit_service.py       # Habit tracking, streak computation, and 7-day history
│   └── ai_service.py          # Gemini API integration & rich deterministic demo mode
├── static/
│   ├── css/
│   │   └── style.css          # Modern dark-mode vanilla CSS design system
│   └── js/
│       └── app.js             # Interactive frontend client, modals, toast notifications, chat
├── templates/
│   ├── index.html             # Main responsive dashboard & SPA views
│   ├── 404.html               # Custom 404 Not Found error page
│   └── 500.html               # Custom 500 Internal Server Error page
└── tests/
    ├── __init__.py
    ├── conftest.py            # Test fixtures with temporary isolated database
    ├── test_tasks.py          # Task CRUD, filters, and validation tests
    ├── test_habits.py         # Habit tracking, duplicate prevention, and streak tests
    ├── test_dashboard.py      # Aggregated dashboard metrics tests
    └── test_ai.py             # Chat validation, demo mode, and prompt tests
```

---

## 🚀 Beginner-Friendly Setup Guide (Windows)

Follow these step-by-step instructions in **PowerShell** or **Command Prompt**:

### Step 1: Open the Project Directory
```powershell
cd C:\Users\kavin\Desktop\ai-life-assistant
```

### Step 2: Create and Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate in PowerShell
.venv\Scripts\Activate.ps1

# (Or in standard Command Prompt: .venv\Scripts\activate.bat)
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create your local `.env` configuration file from the template:
```powershell
copy .env.example .env
```
*(By default, `GEMINI_API_KEY` is left blank. The app will immediately work in **Demo Mode** with smart simulated AI. To use live Gemini AI, open `.env` in any text editor and paste your free key from [Google AI Studio](https://aistudio.google.com/)).*

### Step 5: Run the Application
```powershell
python app.py
```
Open your web browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 Running Automated Tests

The application includes an extensive automated test suite covering all endpoints, validations, calculations, and demo fallbacks with an isolated temporary test database.

To execute the tests:
```powershell
pytest -v
```

### Expected Output:
```
tests/test_ai.py::test_ai_chat_validation PASSED                         [  5%]
tests/test_ai.py::test_ai_chat_demo_mode_fallback PASSED                 [ 11%]
tests/test_ai.py::test_ai_chat_suggested_prompts PASSED                  [ 16%]
tests/test_ai.py::test_daily_planner_summary_endpoint PASSED             [ 22%]
tests/test_dashboard.py::test_dashboard_stats_empty PASSED               [ 27%]
tests/test_dashboard.py::test_dashboard_stats_with_data PASSED           [ 33%]
tests/test_habits.py::test_streak_calculation_logic PASSED               [ 38%]
tests/test_habits.py::test_create_habit_success PASSED                   [ 44%]
tests/test_habits.py::test_create_habit_validation PASSED                [ 50%]
tests/test_habits.py::test_habit_toggle_and_duplicate_prevention PASSED  [ 55%]
tests/test_habits.py::test_habit_history_and_deletion PASSED             [ 61%]
tests/test_tasks.py::test_home_page PASSED                               [ 66%]
tests/test_tasks.py::test_404_error_page_and_json PASSED                 [ 72%]
tests/test_tasks.py::test_create_task_success PASSED                     [ 77%]
tests/test_tasks.py::test_create_task_validation_errors PASSED           [ 83%]
tests/test_tasks.py::test_list_and_filter_tasks PASSED                   [ 88%]
tests/test_tasks.py::test_update_and_toggle_task PASSED                  [ 94%]
tests/test_tasks.py::test_delete_task PASSED                             [100%]

============================= 18 passed in 1.29s ==============================
```

---

## 💡 Example AI Assistant Prompts

Try asking these directly in the **AI Assistant** tab:

1. **Daily Planning:**
   > *"Plan my day."*
   > → *Produces an organized Morning, Afternoon, and Evening schedule grounded in your actual pending and overdue tasks.*

2. **Task Prioritization:**
   > *"Help me prioritize my tasks."*
   > → *Categorizes your tasks into urgent, high-impact, and low-friction action items.*

3. **Routine Optimization:**
   > *"Suggest a productive daily routine."*
   > → *Provides a realistic three-phase rhythm for deep work, admin execution, and mental recharge.*

4. **Habit Building:**
   > *"Help me build a study habit."*
   > → *Explains the 4-step Atomic Habits framework (Cue, Craving, Response, Reward) with practical tips.*

5. **Task Summary:**
   > *"Summarize my pending tasks."*
   > → *Lists your top upcoming commitments with categories and deadlines.*

---

## 🔒 Security & Reliability

- **No Secrets in Source:** `.env` and `.db` files are strictly excluded via `.gitignore`.
- **Parameterized SQL:** All queries use `?` parameter substitution to prevent SQL injection.
- **Server-Side Validation:** Validates title length, priority categories, and ISO date formats before touching the database.
- **XSS Protection:** Frontend encodes user content safely to prevent script injection.
- **Database Isolation:** Automated tests use dynamic temporary databases so your personal data is never altered.

---

## 📤 Publishing to GitHub

To push this codebase to your GitHub account:

```powershell
# 1. Stage all project files (ignoring .env and databases automatically)
git add .

# 2. Create the initial commit
git commit -m "feat: complete AI Life Assistant application with tests and documentation"

# 3. Create a new repository on GitHub (e.g., ai-life-assistant)
# 4. Link your remote repository and push:
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/ai-life-assistant.git
git push -u origin main
```

---

## 🏆 Devpost Project Summary

*(Ready to copy and paste into your hackathon submission)*

> **Inspiration:** Traditional to-do apps are static lists that demand endless manual reorganization. We envisioned an intelligent, empathetic companion that doesn't just store tasks, but actively helps you structure your day, protect your focus, and maintain long-term habits.
>
> **What it does:** *AI Life Assistant* is an everyday companion featuring an interactive dashboard, comprehensive task manager, habit streak tracker, structured daily planner, and a context-aware AI chat assistant. Powered by Google Gemini API (with an offline Demo Mode fallback), it dynamically analyzes your real task workload to recommend realistic schedules, prioritize urgent items, and celebrate habit streaks.
>
> **How we built it:** Frontend crafted in Vanilla HTML5/CSS3/JavaScript using a custom glassmorphism design system. Backend built on Python 3.12 and Flask with SQLite3 for lightweight persistence. AI intelligence integrated using the official Google GenAI Python SDK (`google-genai`). Pytest automated tests ensure robust reliability.
>
> **Challenges & Accomplishments:** Designing an accurate calendar streak algorithm that accounts for pending vs. completed days without false streak breaks, and grounding the AI prompt with live database context while maintaining a seamless Demo Mode when no API key is provided.
>
> **What's next:** Adding voice interaction simulation, exportable calendar summaries, and multi-week habit trend visual analytics.
