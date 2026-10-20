from datetime import date


def test_ai_chat_validation(client):
    """Test AI endpoint input validation."""
    # Missing prompt
    res1 = client.post("/api/chat", json={})
    assert res1.status_code == 400
    assert "prompt is required" in res1.get_json()["error"].lower()

    # Empty prompt
    res2 = client.post("/api/chat", json={"prompt": "   "})
    assert res2.status_code == 400

    # Overly long prompt (> 2000 chars)
    res3 = client.post("/api/chat", json={"prompt": "A" * 2500})
    assert res3.status_code == 400
    assert "too long" in res3.get_json()["error"].lower()


def test_ai_chat_demo_mode_fallback(client):
    """Test AI endpoint behavior in Demo Mode when no API key is configured."""
    response = client.post("/api/chat", json={"prompt": "Plan my day."})
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["is_demo"] is True
    assert "Demo Mode" in data["model"]
    assert "Plan" in data["response"]
    assert data["notice"] is not None


def test_ai_chat_suggested_prompts(client):
    """Test all suggested prompts return meaningful structured answers."""
    # Seed a task first
    client.post("/api/tasks", json={
        "title": "Study Python Unit Tests",
        "priority": "High",
        "category": "Study",
        "due_date": date.today().isoformat()
    })

    prompts = [
        "Plan my day.",
        "Help me prioritize my tasks.",
        "Suggest a productive daily routine.",
        "Help me build a study habit.",
        "Summarize my pending tasks."
    ]

    for p in prompts:
        res = client.post("/api/chat", json={"prompt": p})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert len(data["response"]) > 50  # meaningful response


def test_daily_planner_summary_endpoint(client):
    """Test the daily planner structured data endpoint."""
    today = date.today().isoformat()
    client.post("/api/tasks", json={
        "title": "Today Urgent Task",
        "due_date": today,
        "priority": "High"
    })

    res = client.get("/api/planner/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "disclaimer" in data
    assert len(data["today_tasks"]) == 1
    assert data["today_tasks"][0]["title"] == "Today Urgent Task"
