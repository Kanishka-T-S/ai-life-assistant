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


def test_is_quota_or_rate_limit_error_detection():
    """Test detection of 429 RESOURCE_EXHAUSTED and rate limit errors across formats."""
    from services.ai_service import is_quota_or_rate_limit_error

    # 1. Status / code attribute checks
    class CustomErrorWithCode(Exception):
        code = 429

    class CustomErrorWithStatusCode(Exception):
        status_code = 429

    assert is_quota_or_rate_limit_error(CustomErrorWithCode("Rate limited")) is True
    assert is_quota_or_rate_limit_error(CustomErrorWithStatusCode("Too many requests")) is True

    # 2. String representation checks
    assert is_quota_or_rate_limit_error(Exception("429 RESOURCE_EXHAUSTED: Quota exceeded")) is True
    assert is_quota_or_rate_limit_error(Exception("Quota exceeded for quota metric 'Queries'")) is True
    assert is_quota_or_rate_limit_error(Exception("Rate limit reached for model gemini-3.8-flash")) is True
    assert is_quota_or_rate_limit_error(Exception("Too many requests. Please wait.")) is True

    # 3. Negative checks (should NOT be detected as quota errors)
    assert is_quota_or_rate_limit_error(None) is False
    assert is_quota_or_rate_limit_error(ValueError("Invalid argument")) is False
    assert is_quota_or_rate_limit_error(TimeoutError("Deadline exceeded")) is False
    assert is_quota_or_rate_limit_error(Exception("503 Service Unavailable")) is False


def test_ai_chat_quota_exhausted_friendly_message(app):
    """Test that 429 RESOURCE_EXHAUSTED returns the required friendly message and 429 status."""
    from unittest.mock import patch
    from services.ai_service import reset_quota_state, is_quota_exhausted

    reset_quota_state()
    with app.test_client() as client:
        with patch("services.ai_service.genai.Client") as mock_genai:
            mock_instance = mock_genai.return_value
            mock_instance.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota reached")

            app.config["GEMINI_API_KEY"] = "test_key_for_quota"
            try:
                res = client.post("/api/chat", json={"prompt": "Plan my day."})
                assert res.status_code == 429
                data = res.get_json()
                assert data["success"] is False
                assert data["is_quota_exhausted"] is True
                assert data["fallback_available"] is True
                # Required friendly message verification
                assert "Live AI is temporarily unavailable because the API quota has been reached. You can still use Tasks and Habits." in data["error"]
                assert is_quota_exhausted() is True
            finally:
                app.config["GEMINI_API_KEY"] = ""
                reset_quota_state()


def test_ai_chat_avoids_repeated_retries_during_quota_cooldown(app):
    """Test that requests during quota cooldown avoid calling the live Gemini API repeatedly."""
    from unittest.mock import patch
    from services.ai_service import set_quota_exhausted, reset_quota_state

    set_quota_exhausted(cooldown_seconds=60)
    with app.test_client() as client:
        with patch("services.ai_service.genai.Client") as mock_genai:
            app.config["GEMINI_API_KEY"] = "test_key_for_cooldown"
            try:
                # Call /api/chat while quota is known to be exhausted
                res = client.post("/api/chat", json={"prompt": "Plan my day."})
                assert res.status_code == 429
                data = res.get_json()
                assert data["success"] is False
                assert data["is_quota_exhausted"] is True
                assert "Live AI is temporarily unavailable because the API quota has been reached" in data["error"]
                # Crucial check: genai.Client must NOT be called at all
                mock_genai.assert_not_called()
            finally:
                app.config["GEMINI_API_KEY"] = ""
                reset_quota_state()


def test_ai_chat_explicit_demo_fallback_when_quota_exhausted(app):
    """Test that existing Demo Mode can be explicitly used as a fallback, clearly labeled as simulated."""
    from unittest.mock import patch
    from services.ai_service import set_quota_exhausted, reset_quota_state

    set_quota_exhausted(cooldown_seconds=60)
    with app.test_client() as client:
        with patch("services.ai_service.genai.Client") as mock_genai:
            app.config["GEMINI_API_KEY"] = "test_key_for_fallback"
            try:
                res = client.post("/api/chat", json={
                    "prompt": "Plan my day.",
                    "fallback_to_demo": True
                })
                assert res.status_code == 200
                data = res.get_json()
                assert data["success"] is True
                assert data["is_demo"] is True
                assert data["is_quota_fallback"] is True
                assert "Demo Mode" in data["model"]
                assert "Simulated" in data["model"]
                assert "Plan" in data["response"]
                assert "Tasks and Habits" in data["notice"]
                # Must not have called live Gemini client
                mock_genai.assert_not_called()
            finally:
                app.config["GEMINI_API_KEY"] = ""
                reset_quota_state()


def test_api_key_never_exposed_in_quota_or_generic_errors(app):
    """Test that API keys are strictly redacted and never leaked in errors, logs, or notices."""
    from unittest.mock import patch
    from services.ai_service import reset_quota_state

    secret_key = "AIzaSySecretFakeKey1234567890abcdef"
    reset_quota_state()
    with app.test_client() as client:
        with patch("services.ai_service.genai.Client") as mock_genai:
            mock_instance = mock_genai.return_value
            # Upstream error that accidentally echoes the API key
            mock_instance.models.generate_content.side_effect = Exception(
                f"Request to https://generativelanguage.googleapis.com/v1beta/models?key={secret_key} failed: 429 RESOURCE_EXHAUSTED"
            )

            app.config["GEMINI_API_KEY"] = secret_key
            try:
                res = client.post("/api/chat", json={"prompt": "Test sensitive key redaction"})
                response_text = res.get_data(as_text=True)
                assert secret_key not in response_text
                assert "[REDACTED_API_KEY]" in response_text or secret_key not in response_text
            finally:
                app.config["GEMINI_API_KEY"] = ""
                reset_quota_state()


def test_tasks_and_habits_remain_fully_functional_when_quota_exhausted(client):
    """Verify that task management, habit tracking, and dashboard remain 100% operational when AI quota is exhausted."""
    from services.ai_service import set_quota_exhausted, reset_quota_state, is_quota_exhausted
    from datetime import date

    set_quota_exhausted(cooldown_seconds=60)
    assert is_quota_exhausted() is True

    try:
        # 1. Create a task
        task_res = client.post("/api/tasks", json={
            "title": "Quota Fallback Task Verification",
            "priority": "High",
            "category": "Work",
            "due_date": date.today().isoformat()
        })
        assert task_res.status_code == 201
        task_id = task_res.get_json()["task"]["id"]

        # 2. Toggle the task
        toggle_res = client.patch(f"/api/tasks/{task_id}/toggle")
        assert toggle_res.status_code == 200
        assert toggle_res.get_json()["task"]["is_completed"] == 1

        # 3. Create a habit
        habit_res = client.post("/api/habits", json={
            "name": "Daily Habit During Quota",
            "frequency": "daily"
        })
        assert habit_res.status_code == 201
        habit_id = habit_res.get_json()["habit"]["id"]

        # 4. Toggle habit completion
        toggle_h_res = client.post(f"/api/habits/{habit_id}/toggle", json={})
        assert toggle_h_res.status_code == 200
        assert toggle_h_res.get_json()["data"]["is_completed"] is True

        # 5. Dashboard stats still work smoothly with quota status reflected
        stats_res = client.get("/api/dashboard/stats")
        assert stats_res.status_code == 200
        stats = stats_res.get_json()
        assert stats["success"] is True
        assert stats["ai_status"]["quota_exhausted"] is True
        assert stats["tasks"]["completed"] >= 1
    finally:
        reset_quota_state()


def test_ai_status_and_reset_quota_endpoints(client):
    """Test /api/ai/status and /api/ai/reset-quota endpoints."""
    from services.ai_service import set_quota_exhausted, is_quota_exhausted

    # Set quota exhausted
    set_quota_exhausted(cooldown_seconds=120)
    assert is_quota_exhausted() is True

    # Check status endpoint
    status_res = client.get("/api/ai/status")
    assert status_res.status_code == 200
    status_data = status_res.get_json()
    assert status_data["success"] is True
    assert status_data["is_quota_exhausted"] is True
    assert status_data["cooldown_remaining_sec"] > 0

    # Call reset endpoint
    reset_res = client.post("/api/ai/reset-quota")
    assert reset_res.status_code == 200
    assert reset_res.get_json()["success"] is True

    # Check that quota is now reset
    assert is_quota_exhausted() is False
    status_res2 = client.get("/api/ai/status")
    assert status_res2.get_json()["is_quota_exhausted"] is False



def test_ai_chat_timeout_fallback_when_requested(client, monkeypatch):
    from unittest.mock import patch
    import services.ai_service as ai_service

    # Ensure the Gemini request is not skipped.
    monkeypatch.setattr(ai_service, "HAS_GENAI_SDK", True)
    monkeypatch.setattr(ai_service, "is_quota_exhausted", lambda: False)

    # The route reads the API key from Flask configuration.
    client.application.config["GEMINI_API_KEY"] = "test-dummy-key"

    with patch("services.ai_service.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content.side_effect = (
            TimeoutError("Deadline exceeded")
        )

        response = client.post(
            "/api/chat",
            json={
                "prompt": "Plan my day",
                "fallback_to_demo": True,
            },
        )

    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["is_demo"] is True
    assert data["is_timeout_fallback"] is True
    assert "Timeout Fallback" in data["model"]