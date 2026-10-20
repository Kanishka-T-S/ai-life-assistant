from datetime import date


def test_dashboard_stats_empty(client):
    """Test dashboard stats when database is fresh."""
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["tasks"]["total"] == 0
    assert data["tasks"]["pending"] == 0
    assert data["habits"]["total"] == 0
    assert data["productivity_score"] == 0
    assert data["ai_status"]["is_demo"] is True


def test_dashboard_stats_with_data(client):
    """Test dashboard stats calculation with real tasks and habits."""
    today = date.today().isoformat()

    # Create 2 tasks
    res_t1 = client.post("/api/tasks", json={
        "title": "Task 1",
        "due_date": today,
        "priority": "High"
    })
    t1_id = res_t1.get_json()["task"]["id"]

    client.post("/api/tasks", json={
        "title": "Task 2",
        "due_date": today,
        "priority": "Medium"
    })

    # Complete Task 1
    client.patch(f"/api/tasks/{t1_id}/toggle")

    # Create 2 habits
    res_h1 = client.post("/api/habits", json={"name": "Habit 1"})
    h1_id = res_h1.get_json()["habit"]["id"]
    client.post("/api/habits", json={"name": "Habit 2"})

    # Complete Habit 1 for today
    client.post(f"/api/habits/{h1_id}/toggle", json={})

    # Fetch dashboard stats
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.get_json()

    assert data["tasks"]["total"] == 2
    assert data["tasks"]["completed"] == 1
    assert data["tasks"]["pending"] == 1
    assert data["tasks"]["today_total"] == 2
    assert data["tasks"]["today_completed"] == 1

    assert data["habits"]["total"] == 2
    assert data["habits"]["completed_today"] == 1
    assert data["habits"]["completion_rate"] == 50

    # Productivity score: (50% tasks + 50% habits) / 2 = 50%
    assert data["productivity_score"] == 50

    # Verify upcoming tasks only has pending task
    assert len(data["upcoming_tasks"]) == 1
    assert data["upcoming_tasks"][0]["title"] == "Task 2"
