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


def test_ai_chat_timing_included(client):
    """Test that timing metadata is included in chat responses."""
    response = client.post("/api/chat", json={"prompt": "Plan my day."})
    assert response.status_code == 200
    data = response.get_json()
    assert "timing" in data
    assert "api_latency_sec" in data["timing"]
    assert "total_latency_sec" in data["timing"]
    assert isinstance(data["timing"]["total_latency_sec"], (int, float))


def test_ai_chat_timeout_handling(app):
    """Test graceful handling of upstream timeouts without fake live responses."""
    from unittest.mock import patch
    with app.test_client() as client:
        with patch("services.ai_service.genai.Client") as mock_genai:
            mock_instance = mock_genai.return_value
            mock_instance.models.generate_content.side_effect = TimeoutError("Deadline exceeded")

            app.config["GEMINI_API_KEY"] = "test_key_for_timeout"
            try:
                res = client.post("/api/chat", json={"prompt": "Test timeout"})
                assert res.status_code == 504
                data = res.get_json()
                assert data["success"] is False
                assert data["is_timeout"] is True
                assert "timed out" in data["error"].lower()
            finally:
                app.config["GEMINI_API_KEY"] = ""


def test_ai_chat_upstream_error_handling(app):
    """Test graceful handling of upstream API errors without fake live responses."""
    from unittest.mock import patch
    with app.test_client() as client:
        with patch("services.ai_service.genai.Client") as mock_genai:
            mock_instance = mock_genai.return_value
            mock_instance.models.generate_content.side_effect = Exception("503 UNAVAILABLE: high demand")

            app.config["GEMINI_API_KEY"] = "test_key_for_error"
            try:
                res = client.post("/api/chat", json={"prompt": "Test 503 error"})
                assert res.status_code == 503
                data = res.get_json()
                assert data["success"] is False
                assert "high demand" in data["error"].lower() or "error" in data["error"].lower()
            finally:
                app.config["GEMINI_API_KEY"] = ""
