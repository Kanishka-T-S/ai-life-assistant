from datetime import date, timedelta


def test_home_page(client):
    """Test that the main dashboard page loads successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"AI Life Assistant" in response.data


def test_404_error_page_and_json(client):
    """Test 404 responses for web and API."""
    res_web = client.get("/non-existent-page")
    assert res_web.status_code == 404
    assert b"Page Not Found" in res_web.data

    res_api = client.get("/api/non-existent-endpoint")
    assert res_api.status_code == 404
    data = res_api.get_json()
    assert data["success"] is False


def test_create_task_success(client):
    """Test creating a valid task."""
    payload = {
        "title": "Complete Hackathon Submission",
        "description": "Prepare demo video and devpost description",
        "due_date": date.today().isoformat(),
        "priority": "High",
        "category": "Project"
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["task"]["title"] == "Complete Hackathon Submission"
    assert data["task"]["priority"] == "High"
    assert data["task"]["is_completed"] is False


def test_create_task_validation_errors(client):
    """Test server-side input validation for tasks."""
    # Empty title
    res_empty_title = client.post("/api/tasks", json={"title": "   "})
    assert res_empty_title.status_code == 400
    assert "title is required" in res_empty_title.get_json()["error"].lower()

    # Invalid priority
    res_invalid_priority = client.post("/api/tasks", json={
        "title": "Valid Title",
        "priority": "SuperUrgent"
    })
    assert res_invalid_priority.status_code == 400
    assert "invalid priority" in res_invalid_priority.get_json()["error"].lower()

    # Invalid due date format
    res_invalid_date = client.post("/api/tasks", json={
        "title": "Valid Title",
        "due_date": "20-10-2026"  # wrong format (not YYYY-MM-DD)
    })
    assert res_invalid_date.status_code == 400
    assert "invalid due date format" in res_invalid_date.get_json()["error"].lower()


def test_list_and_filter_tasks(client):
    """Test retrieving tasks with status and priority filters."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    # Insert test tasks
    client.post("/api/tasks", json={
        "title": "Task Today High",
        "due_date": today.isoformat(),
        "priority": "High",
        "category": "Work"
    })
    client.post("/api/tasks", json={
        "title": "Task Overdue Low",
        "due_date": yesterday.isoformat(),
        "priority": "Low",
        "category": "Personal"
    })
    client.post("/api/tasks", json={
        "title": "Task Future Medium",
        "due_date": tomorrow.isoformat(),
        "priority": "Medium",
        "category": "Work"
    })

    # Test all
    res_all = client.get("/api/tasks")
    assert res_all.status_code == 200
    assert len(res_all.get_json()["tasks"]) == 3

    # Test filter by priority
    res_high = client.get("/api/tasks?priority=High")
    assert len(res_high.get_json()["tasks"]) == 1
    assert res_high.get_json()["tasks"][0]["title"] == "Task Today High"

    # Test filter overdue
    res_overdue = client.get("/api/tasks?status=overdue")
    assert len(res_overdue.get_json()["tasks"]) == 1
    assert res_overdue.get_json()["tasks"][0]["title"] == "Task Overdue Low"

    # Test search query
    res_search = client.get("/api/tasks?search=Overdue")
    assert len(res_search.get_json()["tasks"]) == 1
    assert res_search.get_json()["tasks"][0]["title"] == "Task Overdue Low"


def test_update_and_toggle_task(client):
    """Test editing task details and toggling completion."""
    res_create = client.post("/api/tasks", json={"title": "Draft Presentation"})
    task_id = res_create.get_json()["task"]["id"]

    # Toggle to completed
    res_toggle = client.patch(f"/api/tasks/{task_id}/toggle")
    assert res_toggle.status_code == 200
    assert res_toggle.get_json()["task"]["is_completed"] is True

    # Toggle back to pending
    res_toggle2 = client.patch(f"/api/tasks/{task_id}/toggle")
    assert res_toggle2.status_code == 200
    assert res_toggle2.get_json()["task"]["is_completed"] is False

    # Update task details
    res_update = client.put(f"/api/tasks/{task_id}", json={
        "title": "Updated Presentation Title",
        "priority": "High"
    })
    assert res_update.status_code == 200
    assert res_update.get_json()["task"]["title"] == "Updated Presentation Title"
    assert res_update.get_json()["task"]["priority"] == "High"


def test_delete_task(client):
    """Test deleting a task."""
    res_create = client.post("/api/tasks", json={"title": "Temporary Task"})
    task_id = res_create.get_json()["task"]["id"]

    # Delete
    res_del = client.delete(f"/api/tasks/{task_id}")
    assert res_del.status_code == 200
    assert res_del.get_json()["success"] is True

    # Verify 404 on subsequent get
    res_get = client.get(f"/api/tasks/{task_id}")
    assert res_get.status_code == 404
