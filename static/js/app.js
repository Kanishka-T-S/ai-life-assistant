/**
 * AI Life Assistant - Core Frontend Application
 * Handles Dashboard, Task CRUD, Habit Tracking & Streaks, Daily Planner, and Conversational AI Chat.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ==========================================
  // STATE MANAGEMENT
  // ==========================================
  const state = {
    currentTab: "dashboard",
    tasks: [],
    habits: [],
    dashboardStats: null,
    taskFilters: {
      status: "all",
      priority: "all",
      category: "all",
      search: "",
      sortBy: "due_date_asc"
    },
    chatHistory: [],
    isChatWaiting: false,
    aiStatus: { is_demo: true, model: "Demo Mode" }
  };

  // ==========================================
  // DOM REFERENCES
  // ==========================================
  // Navigation
  const navLinks = document.querySelectorAll(".nav-link");
  const viewPanels = document.querySelectorAll(".view-panel");
  const mobileMenuBtn = document.getElementById("mobileMenuBtn");
  const sidebar = document.getElementById("sidebar");

  // Top bar elements
  const greetingHeading = document.getElementById("greetingHeading");
  const greetingDate = document.getElementById("greetingDate");

  // AI status badges
  const sidebarAiStatus = document.getElementById("sidebarAiStatus");
  const chatAiBadge = document.getElementById("chatAiBadge");

  // Dashboard elements
  const statPendingTasks = document.getElementById("statPendingTasks");
  const statCompletedTasks = document.getElementById("statCompletedTasks");
  const statHabitsToday = document.getElementById("statHabitsToday");
  const statProductivityScore = document.getElementById("statProductivityScore");
  const productivityProgressBar = document.getElementById("productivityProgressBar");
  const productivityScoreText = document.getElementById("productivityScoreText");
  const dailyQuoteText = document.getElementById("dailyQuoteText");
  const dailyQuoteAuthor = document.getElementById("dailyQuoteAuthor");
  const upcomingTasksList = document.getElementById("upcomingTasksList");
  const dashboardHabitHighlights = document.getElementById("dashboardHabitHighlights");

  // Task View elements
  const taskListEl = document.getElementById("taskList");
  const taskSearchInput = document.getElementById("taskSearchInput");
  const taskSortSelect = document.getElementById("taskSortSelect");
  const taskPriorityFilter = document.getElementById("taskPriorityFilter");
  const taskFilterChips = document.querySelectorAll(".task-filter-chip");
  const openAddTaskModalBtn = document.getElementById("openAddTaskModalBtn");

  // Habit View elements
  const habitGridEl = document.getElementById("habitGrid");
  const habitCompletionRateText = document.getElementById("habitCompletionRateText");
  const habitProgressBar = document.getElementById("habitProgressBar");
  const openAddHabitModalBtn = document.getElementById("openAddHabitModalBtn");

  // Daily Planner elements
  const plannerOverdueAlert = document.getElementById("plannerOverdueAlert");
  const plannerOverdueList = document.getElementById("plannerOverdueList");
  const plannerMorningList = document.getElementById("plannerMorningList");
  const plannerAfternoonList = document.getElementById("plannerAfternoonList");
  const plannerEveningList = document.getElementById("plannerEveningList");
  const askAiPlanBtn = document.getElementById("askAiPlanBtn");

  // Chat elements
  const chatMessagesEl = document.getElementById("chatMessages");
  const chatInputEl = document.getElementById("chatInput");
  const sendChatBtn = document.getElementById("sendChatBtn");
  const clearChatBtn = document.getElementById("clearChatBtn");
  const promptChips = document.querySelectorAll(".prompt-chip");

  // Modals
  const taskModal = document.getElementById("taskModal");
  const taskModalTitle = document.getElementById("taskModalTitle");
  const taskForm = document.getElementById("taskForm");
  const taskIdInput = document.getElementById("taskId");
  const taskTitleInput = document.getElementById("taskTitle");
  const taskDescInput = document.getElementById("taskDesc");
  const taskDueDateInput = document.getElementById("taskDueDate");
  const taskPrioritySelect = document.getElementById("taskPriority");
  const taskCategoryInput = document.getElementById("taskCategory");

  const habitModal = document.getElementById("habitModal");
  const habitModalTitle = document.getElementById("habitModalTitle");
  const habitForm = document.getElementById("habitForm");
  const habitIdInput = document.getElementById("habitId");
  const habitNameInput = document.getElementById("habitName");
  const habitDescInput = document.getElementById("habitDesc");
  const habitFrequencySelect = document.getElementById("habitFrequency");

  const confirmModal = document.getElementById("confirmModal");
  const confirmModalTitle = document.getElementById("confirmModalTitle");
  const confirmModalMessage = document.getElementById("confirmModalMessage");
  const confirmActionBtn = document.getElementById("confirmActionBtn");

  // ==========================================
  // HELPER UTILITIES
  // ==========================================
  function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icon = type === "success" ? "✓" : type === "error" ? "⚠️" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let safe = escapeHtml(text);

    // Headers
    safe = safe.replace(/^### (.*$)/gim, "<h4>$1</h4>");
    safe = safe.replace(/^## (.*$)/gim, "<h3>$1</h3>");
    safe = safe.replace(/^# (.*$)/gim, "<h2>$1</h2>");

    // Bold & italic
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/\*(.*?)\*/g, "<em>$1</em>");

    // Blockquote
    safe = safe.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

    // Bullet points
    safe = safe.replace(/^\- (.*$)/gim, "<li>$1</li>");
    safe = safe.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

    // Line breaks
    safe = safe.replace(/\n\n/g, "<br><br>");
    safe = safe.replace(/\n/g, "<br>");

    return safe;
  }

  function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }

  // ==========================================
  // NAVIGATION & TAB SWITCHING
  // ==========================================
  function switchTab(targetTab) {
    state.currentTab = targetTab;

    navLinks.forEach((link) => {
      const tab = link.getAttribute("data-tab");
      if (tab === targetTab) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    viewPanels.forEach((panel) => {
      if (panel.id === `view-${targetTab}`) {
        panel.classList.add("active");
      } else {
        panel.classList.remove("active");
      }
    });

    // Mobile sidebar auto-close
    sidebar.classList.remove("mobile-open");

    // Refresh data according to tab
    if (targetTab === "dashboard") {
      fetchDashboardStats();
    } else if (targetTab === "tasks") {
      fetchTasks();
    } else if (targetTab === "habits") {
      fetchHabits();
    } else if (targetTab === "planner") {
      fetchPlannerSummary();
    } else if (targetTab === "chat") {
      setTimeout(() => chatInputEl.focus(), 150);
    }
  }

  navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const tab = link.getAttribute("data-tab");
      if (tab) switchTab(tab);
    });
  });

  // Mobile menu button
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("mobile-open");
    });
  }

  // Quick Action Buttons on Dashboard
  document.querySelectorAll("[data-quick-action]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const action = btn.getAttribute("data-quick-action");
      if (action === "add-task") {
        openTaskModal();
      } else if (action === "habits") {
        switchTab("habits");
      } else if (action === "ai-chat") {
        switchTab("chat");
      }
    });
  });

  // ==========================================
  // API INTEGRATION: DASHBOARD
  // ==========================================
  async function fetchDashboardStats() {
    try {
      const res = await fetch("/api/dashboard/stats");
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed to load stats");

      state.dashboardStats = data;
      renderDashboard(data);
    } catch (err) {
      console.error("Dashboard stats error:", err);
      showToast("Could not load dashboard statistics.", "error");
    }
  }

  function renderDashboard(data) {
    // Greeting
    greetingHeading.textContent = `${getGreeting()}, Ready to conquer today?`;
    greetingDate.textContent = data.date.formatted;

    // AI Status Badge
    state.aiStatus = data.ai_status;
    updateAiStatusBadges();

    // Stats
    statPendingTasks.textContent = data.tasks.pending;
    statCompletedTasks.textContent = `${data.tasks.completed} / ${data.tasks.total}`;
    statHabitsToday.textContent = `${data.habits.completed_today} / ${data.habits.total}`;
    statProductivityScore.textContent = `${data.productivity_score}%`;

    // Productivity bar
    if (productivityProgressBar) {
      productivityProgressBar.style.width = `${data.productivity_score}%`;
    }
    if (productivityScoreText) {
      productivityScoreText.textContent = `${data.productivity_score}% Completed`;
    }

    // Daily quote
    if (data.daily_quote) {
      dailyQuoteText.textContent = `“${data.daily_quote.quote}”`;
      dailyQuoteAuthor.textContent = `— ${data.daily_quote.author}`;
    }

    // Upcoming tasks preview
    renderUpcomingTasks(data.upcoming_tasks);
  }

  function updateAiStatusBadges() {
    const isLive = !state.aiStatus.is_demo;
    const statusHtml = isLive
      ? `<span class="status-dot"></span> <span>Live Gemini AI</span>`
      : `<span class="status-dot"></span> <span>Demo Mode (Simulated AI)</span>`;

    if (sidebarAiStatus) {
      sidebarAiStatus.className = `ai-status-pill ${isLive ? "live" : ""}`;
      sidebarAiStatus.innerHTML = statusHtml;
      sidebarAiStatus.title = isLive
        ? "Connected to live Gemini API"
        : "Running in Demo Mode. Add GEMINI_API_KEY in .env for live Gemini AI.";
    }

    if (chatAiBadge) {
      chatAiBadge.className = `badge ${isLive ? "badge-priority-Low" : "badge-priority-Medium"}`;
      chatAiBadge.textContent = isLive ? "⚡ Live Gemini AI" : "🤖 Demo Mode (Simulated)";
    }
  }

  function renderUpcomingTasks(tasks) {
    if (!upcomingTasksList) return;

    if (!tasks || tasks.length === 0) {
      upcomingTasksList.innerHTML = `
        <div class="empty-state" style="padding: 24px;">
          <div class="empty-state-icon">🎉</div>
          <h3>No Pending Tasks</h3>
          <p>You're completely caught up! Add a new task to keep building momentum.</p>
          <button class="btn btn-primary btn-sm" onclick="document.getElementById('openAddTaskModalBtn').click()">+ Add Task</button>
        </div>
      `;
      return;
    }

    upcomingTasksList.innerHTML = tasks
      .map(
        (t) => `
        <div class="task-item ${t.is_completed ? "completed" : ""}" data-task-id="${t.id}">
          <div class="custom-checkbox ${t.is_completed ? "checked" : ""}" onclick="window.toggleTaskItem(${t.id})">
            ${t.is_completed ? "✓" : ""}
          </div>
          <div class="task-content">
            <div class="task-title">${escapeHtml(t.title)}</div>
            <div class="task-meta">
              <span class="badge badge-priority-${t.priority}">${t.priority}</span>
              <span class="badge badge-category">${escapeHtml(t.category)}</span>
              ${
                t.due_date
                  ? `<span class="badge badge-due ${t.is_overdue ? "overdue" : t.is_today ? "today" : ""}">
                      ${t.is_overdue ? "⚠️ Overdue: " : t.is_today ? "📅 Today" : "📅 "}${t.due_date}
                    </span>`
                  : ""
              }
            </div>
          </div>
        </div>
      `
      )
      .join("");
  }

  // ==========================================
  // API INTEGRATION: TASKS
  // ==========================================
  async function fetchTasks() {
    try {
      const params = new URLSearchParams({
        status: state.taskFilters.status,
        priority: state.taskFilters.priority,
        category: state.taskFilters.category,
        search: state.taskFilters.search,
        sort_by: state.taskFilters.sortBy
      });

      const res = await fetch(`/api/tasks?${params.toString()}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      state.tasks = data.tasks;
      renderTaskList(data.tasks);
    } catch (err) {
      console.error("Fetch tasks error:", err);
      showToast("Failed to load tasks.", "error");
    }
  }

  function renderTaskList(tasks) {
    if (!taskListEl) return;

    if (!tasks || tasks.length === 0) {
      taskListEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📋</div>
          <h3>No Tasks Found</h3>
          <p>No tasks match your current filters. Create a new task or adjust your filters.</p>
          <button class="btn btn-primary" onclick="window.openTaskModal()">+ Add New Task</button>
        </div>
      `;
      return;
    }

    taskListEl.innerHTML = tasks
      .map(
        (t) => `
        <div class="task-item ${t.is_completed ? "completed" : ""}" data-task-id="${t.id}">
          <div class="custom-checkbox ${t.is_completed ? "checked" : ""}" onclick="window.toggleTaskItem(${t.id})" title="Toggle completion">
            ${t.is_completed ? "✓" : ""}
          </div>
          <div class="task-content">
            <div class="task-title">${escapeHtml(t.title)}</div>
            ${t.description ? `<div class="task-desc">${escapeHtml(t.description)}</div>` : ""}
            <div class="task-meta">
              <span class="badge badge-priority-${t.priority}">${t.priority}</span>
              <span class="badge badge-category">${escapeHtml(t.category)}</span>
              ${
                t.due_date
                  ? `<span class="badge badge-due ${t.is_overdue ? "overdue" : t.is_today ? "today" : ""}">
                      ${t.is_overdue ? "⚠️ Overdue: " : t.is_today ? "📅 Today" : "📅 "}${t.due_date}
                    </span>`
                  : ""
              }
            </div>
          </div>
          <div class="task-actions">
            <button class="btn btn-secondary btn-icon" onclick="window.editTaskItem(${t.id})" title="Edit task">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
            </button>
            <button class="btn btn-danger btn-icon" onclick="window.confirmDeleteTask(${t.id}, '${escapeHtml(t.title).replace(/'/g, "\\'")}')" title="Delete task">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
          </div>
        </div>
      `
      )
      .join("");
  }

  // Window-level handlers for inline HTML events
  window.toggleTaskItem = async function (taskId) {
    try {
      const res = await fetch(`/api/tasks/${taskId}/toggle`, { method: "PATCH" });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      showToast(
        data.task.is_completed ? "Task marked completed! 🎉" : "Task marked pending.",
        "success"
      );
      if (state.currentTab === "tasks") {
        fetchTasks();
      } else {
        fetchDashboardStats();
      }
    } catch (err) {
      showToast("Failed to toggle task.", "error");
    }
  };

  window.openTaskModal = function (task = null) {
    taskForm.reset();
    if (task) {
      taskModalTitle.textContent = "Edit Task";
      taskIdInput.value = task.id;
      taskTitleInput.value = task.title;
      taskDescInput.value = task.description || "";
      taskDueDateInput.value = task.due_date || "";
      taskPrioritySelect.value = task.priority || "Medium";
      taskCategoryInput.value = task.category || "General";
    } else {
      taskModalTitle.textContent = "Create New Task";
      taskIdInput.value = "";
      taskPrioritySelect.value = "Medium";
      taskCategoryInput.value = "General";
    }
    taskModal.classList.add("open");
    taskTitleInput.focus();
  };

  window.editTaskItem = function (taskId) {
    const task = state.tasks.find((t) => t.id === taskId);
    if (task) {
      window.openTaskModal(task);
    }
  };

  window.confirmDeleteTask = function (taskId, title) {
    confirmModalTitle.textContent = "Delete Task";
    confirmModalMessage.textContent = `Are you sure you want to delete "${title}"? This action cannot be undone.`;
    confirmActionBtn.onclick = async () => {
      try {
        const res = await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        closeModal(confirmModal);
        showToast("Task deleted successfully.", "success");
        fetchTasks();
      } catch (err) {
        showToast("Failed to delete task.", "error");
      }
    };
    confirmModal.classList.add("open");
  };

  // Task form submission (Create or Edit)
  if (taskForm) {
    taskForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const taskId = taskIdInput.value;
      const payload = {
        title: taskTitleInput.value.trim(),
        description: taskDescInput.value.trim(),
        due_date: taskDueDateInput.value,
        priority: taskPrioritySelect.value,
        category: taskCategoryInput.value.trim() || "General"
      };

      if (!payload.title) {
        showToast("Task title is required.", "error");
        return;
      }

      try {
        let res;
        if (taskId) {
          res = await fetch(`/api/tasks/${taskId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        } else {
          res = await fetch("/api/tasks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        }

        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        closeModal(taskModal);
        showToast(taskId ? "Task updated." : "Task created!", "success");
        fetchTasks();
      } catch (err) {
        showToast(err.message || "Failed to save task.", "error");
      }
    });
  }

  // Filter chips
  taskFilterChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      taskFilterChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.taskFilters.status = chip.getAttribute("data-status");
      fetchTasks();
    });
  });

  // Priority filter
  if (taskPriorityFilter) {
    taskPriorityFilter.addEventListener("change", () => {
      state.taskFilters.priority = taskPriorityFilter.value;
      fetchTasks();
    });
  }

  // Sort select
  if (taskSortSelect) {
    taskSortSelect.addEventListener("change", () => {
      state.taskFilters.sortBy = taskSortSelect.value;
      fetchTasks();
    });
  }

  // Search input with debounce
  let searchTimeout = null;
  if (taskSearchInput) {
    taskSearchInput.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.taskFilters.search = taskSearchInput.value.trim();
        fetchTasks();
      }, 250);
    });
  }

  if (openAddTaskModalBtn) {
    openAddTaskModalBtn.addEventListener("click", () => window.openTaskModal());
  }

  // ==========================================
  // API INTEGRATION: HABITS
  // ==========================================
  async function fetchHabits() {
    try {
      const res = await fetch("/api/habits");
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      state.habits = data.habits;
      renderHabitList(data.habits);
    } catch (err) {
      console.error("Fetch habits error:", err);
      showToast("Failed to load habits.", "error");
    }
  }

  function renderHabitList(habits) {
    if (!habitGridEl) return;

    // Progress bar in Habit view header
    const total = habits.length;
    const completedToday = habits.filter((h) => h.is_completed_today).length;
    const rate = total > 0 ? Math.round((completedToday / total) * 100) : 0;

    if (habitCompletionRateText) {
      habitCompletionRateText.textContent = `${completedToday} of ${total} habits completed today (${rate}%)`;
    }
    if (habitProgressBar) {
      habitProgressBar.style.width = `${rate}%`;
    }

    if (habits.length === 0) {
      habitGridEl.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-state-icon">🌱</div>
          <h3>No Habits Tracked Yet</h3>
          <p>Habits shape your future. Build your first productive habit today!</p>
          <button class="btn btn-primary" onclick="window.openHabitModal()">+ Add New Habit</button>
        </div>
      `;
      return;
    }

    habitGridEl.innerHTML = habits
      .map(
        (h) => `
        <div class="habit-card" data-habit-id="${h.id}">
          <div class="habit-card-top">
            <div>
              <div class="habit-name">${escapeHtml(h.name)}</div>
              ${h.description ? `<div class="habit-desc">${escapeHtml(h.description)}</div>` : ""}
            </div>
            <span class="streak-pill ${h.current_streak > 0 ? "active-streak" : ""}">
              🔥 ${h.current_streak}d streak
            </span>
          </div>

          <!-- 7-day mini visual history -->
          <div class="history-dots-row">
            ${h.history_7_days
              .map(
                (day) => `
              <div class="history-dot-item" title="${day.date}: ${day.completed ? "Completed" : "Missed"}">
                <span class="dot-label">${day.day_name}</span>
                <span class="dot-circle ${day.completed ? "completed" : ""}"></span>
              </div>
            `
              )
              .join("")}
          </div>

          <div class="habit-card-footer">
            <button class="habit-toggle-btn ${h.is_completed_today ? "done" : ""}" onclick="window.toggleHabitItem(${h.id})">
              ${h.is_completed_today ? "✓ Done Today" : "○ Mark Done Today"}
            </button>
            <div class="task-actions">
              <button class="btn btn-secondary btn-icon" onclick="window.editHabitItem(${h.id})" title="Edit habit">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
              </button>
              <button class="btn btn-danger btn-icon" onclick="window.confirmDeleteHabit(${h.id}, '${escapeHtml(h.name).replace(/'/g, "\\'")}')" title="Delete habit">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
              </button>
            </div>
          </div>
        </div>
      `
      )
      .join("");
  }

  window.toggleHabitItem = async function (habitId) {
    try {
      const res = await fetch(`/api/habits/${habitId}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      showToast(
        data.data.is_completed ? "Habit logged for today! 🔥" : "Habit completion undone.",
        "success"
      );
      fetchHabits();
    } catch (err) {
      showToast("Failed to record habit completion.", "error");
    }
  };

  window.openHabitModal = function (habit = null) {
    habitForm.reset();
    if (habit) {
      habitModalTitle.textContent = "Edit Habit";
      habitIdInput.value = habit.id;
      habitNameInput.value = habit.name;
      habitDescInput.value = habit.description || "";
      habitFrequencySelect.value = habit.frequency || "daily";
    } else {
      habitModalTitle.textContent = "Create New Habit";
      habitIdInput.value = "";
      habitFrequencySelect.value = "daily";
    }
    habitModal.classList.add("open");
    habitNameInput.focus();
  };

  window.editHabitItem = function (habitId) {
    const habit = state.habits.find((h) => h.id === habitId);
    if (habit) window.openHabitModal(habit);
  };

  window.confirmDeleteHabit = function (habitId, name) {
    confirmModalTitle.textContent = "Delete Habit";
    confirmModalMessage.textContent = `Are you sure you want to delete habit "${name}" and all its streak history?`;
    confirmActionBtn.onclick = async () => {
      try {
        const res = await fetch(`/api/habits/${habitId}`, { method: "DELETE" });
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        closeModal(confirmModal);
        showToast("Habit deleted.", "success");
        fetchHabits();
      } catch (err) {
        showToast("Failed to delete habit.", "error");
      }
    };
    confirmModal.classList.add("open");
  };

  if (habitForm) {
    habitForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const habitId = habitIdInput.value;
      const payload = {
        name: habitNameInput.value.trim(),
        description: habitDescInput.value.trim(),
        frequency: habitFrequencySelect.value
      };

      if (!payload.name) {
        showToast("Habit name is required.", "error");
        return;
      }

      try {
        let res;
        if (habitId) {
          res = await fetch(`/api/habits/${habitId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        } else {
          res = await fetch("/api/habits", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        }

        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        closeModal(habitModal);
        showToast(habitId ? "Habit updated." : "Habit created!", "success");
        fetchHabits();
      } catch (err) {
        showToast(err.message || "Failed to save habit.", "error");
      }
    });
  }

  if (openAddHabitModalBtn) {
    openAddHabitModalBtn.addEventListener("click", () => window.openHabitModal());
  }

  // ==========================================
  // API INTEGRATION: DAILY PLANNER
  // ==========================================
  async function fetchPlannerSummary() {
    try {
      const res = await fetch("/api/planner/summary");
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      renderPlanner(data);
    } catch (err) {
      console.error("Planner error:", err);
      showToast("Failed to load daily plan.", "error");
    }
  }

  function renderPlanner(data) {
    // Overdue tasks banner
    if (data.overdue_tasks && data.overdue_tasks.length > 0) {
      plannerOverdueAlert.style.display = "block";
      plannerOverdueList.innerHTML = data.overdue_tasks
        .map(
          (t) => `
          <div class="task-item" style="padding: 10px 14px; margin-bottom: 6px;">
            <div class="task-content">
              <strong>${escapeHtml(t.title)}</strong>
              <div class="task-meta">
                <span class="badge badge-due overdue">Due: ${t.due_date}</span>
                <span class="badge badge-priority-${t.priority}">${t.priority}</span>
              </div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="window.toggleTaskItem(${t.id})">Mark Done</button>
          </div>
        `
        )
        .join("");
    } else {
      plannerOverdueAlert.style.display = "none";
    }

    // Distribute today's tasks and high priority tasks into suggested blocks
    const allPending = [
      ...data.today_tasks.filter((t) => !t.is_completed),
      ...data.high_priority_pending.filter((t) => !t.is_today)
    ];

    const morningTasks = allPending.slice(0, 2);
    const afternoonTasks = allPending.slice(2, 4);
    const eveningTasks = allPending.slice(4);

    renderPlannerBlock(plannerMorningList, morningTasks, "Deep Focus Block");
    renderPlannerBlock(plannerAfternoonList, afternoonTasks, "Execution & Follow-up");
    renderPlannerBlock(plannerEveningList, eveningTasks, "Wrap-up & Review");
  }

  function renderPlannerBlock(container, tasks, defaultDesc) {
    if (!container) return;
    if (tasks.length === 0) {
      container.innerHTML = `<p style="font-size: 0.82rem; color: var(--text-dim); font-style: italic;">No specific tasks assigned. Good time for ${defaultDesc.toLowerCase()}.</p>`;
      return;
    }
    container.innerHTML = tasks
      .map(
        (t) => `
        <div class="task-item" style="padding: 10px 14px; margin-bottom: 8px;">
          <div class="task-content">
            <span style="font-weight: 600; font-size: 0.88rem;">${escapeHtml(t.title)}</span>
            <div class="task-meta">
              <span class="badge badge-priority-${t.priority}">${t.priority}</span>
              <span class="badge badge-category">${escapeHtml(t.category)}</span>
            </div>
          </div>
        </div>
      `
      )
      .join("");
  }

  if (askAiPlanBtn) {
    askAiPlanBtn.addEventListener("click", () => {
      switchTab("chat");
      sendChatMessage("Plan my day.");
    });
  }

  // ==========================================
  // API INTEGRATION: AI CHAT ASSISTANT
  // ==========================================
  async function sendChatMessage(promptText) {
    const prompt = (promptText || chatInputEl.value).trim();
    if (!prompt || state.isChatWaiting) return;

    chatInputEl.value = "";
    chatInputEl.style.height = "auto";

    // Append user message bubble
    appendChatBubble("user", prompt);
    state.chatHistory.push({ role: "user", content: prompt });

    // Show typing indicator
    state.isChatWaiting = true;
    showTypingIndicator();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt,
          history: state.chatHistory.slice(-4)
        })
      });

      const data = await res.json();
      removeTypingIndicator();
      state.isChatWaiting = false;

      if (!data.success) {
        appendChatBubble("assistant", `⚠️ Error: ${data.error || "Unable to generate response."}`);
        return;
      }

      state.chatHistory.push({ role: "assistant", content: data.response });
      appendChatBubble("assistant", data.response, data.is_demo, data.notice);
    } catch (err) {
      removeTypingIndicator();
      state.isChatWaiting = false;
      appendChatBubble("assistant", "⚠️ Connection error. Please ensure the server is running and try again.");
    }
  }

  function appendChatBubble(role, text, isDemo = false, notice = null) {
    if (!chatMessagesEl) return;

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;

    if (role === "user") {
      bubble.textContent = text;
    } else {
      bubble.innerHTML = formatMarkdown(text);

      if (isDemo) {
        const metaDiv = document.createElement("div");
        metaDiv.className = "chat-bubble-meta";
        metaDiv.innerHTML = `<span class="demo-mode-tag">🤖 Demo Mode (Simulated AI)</span>`;
        bubble.appendChild(metaDiv);
      }

      if (notice) {
        const noticeDiv = document.createElement("div");
        noticeDiv.style.fontSize = "0.75rem";
        noticeDiv.style.color = "var(--text-dim)";
        noticeDiv.style.marginTop = "6px";
        noticeDiv.style.fontStyle = "italic";
        noticeDiv.textContent = notice;
        bubble.appendChild(noticeDiv);
      }
    }

    chatMessagesEl.appendChild(bubble);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }

  function showTypingIndicator() {
    removeTypingIndicator();
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.id = "chatTypingIndicator";
    indicator.innerHTML = `
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    `;
    chatMessagesEl.appendChild(indicator);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  }

  function removeTypingIndicator() {
    const el = document.getElementById("chatTypingIndicator");
    if (el) el.remove();
  }

  // Chat event listeners
  if (sendChatBtn) {
    sendChatBtn.addEventListener("click", () => sendChatMessage());
  }

  if (chatInputEl) {
    chatInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });

    // Auto-grow textarea
    chatInputEl.addEventListener("input", () => {
      chatInputEl.style.height = "auto";
      chatInputEl.style.height = Math.min(chatInputEl.scrollHeight, 120) + "px";
    });
  }

  // Prompt chips
  promptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt") || chip.textContent.trim();
      sendChatMessage(prompt);
    });
  });

  // Clear chat
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      confirmModalTitle.textContent = "Clear Chat History";
      confirmModalMessage.textContent = "Are you sure you want to clear your current conversation? All messages will be reset.";
      confirmActionBtn.onclick = () => {
        state.chatHistory = [];
        chatMessagesEl.innerHTML = `
          <div class="chat-bubble assistant">
            👋 Hello! I am your <strong>AI Life Assistant</strong>. Ask me anything, or pick one of the suggested prompts below to plan your day, prioritize tasks, or build habits.
          </div>
        `;
        closeModal(confirmModal);
        showToast("Conversation cleared.", "info");
      };
      confirmModal.classList.add("open");
    });
  }

  // ==========================================
  // MODAL MANAGEMENT & CLOSING
  // ==========================================
  function closeModal(modal) {
    if (modal) modal.classList.remove("open");
  }

  document.querySelectorAll(".modal-close-trigger").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const modal = btn.closest(".modal-backdrop");
      closeModal(modal);
    });
  });

  // Close modal when clicking outside modal-window
  document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeModal(backdrop);
    });
  });

  // Close modals on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.open").forEach(closeModal);
    }
  });

  // ==========================================
  // INITIALIZATION
  // ==========================================
  fetchDashboardStats();
});
