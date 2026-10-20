from datetime import date, timedelta
from services.habit_service import calculate_habit_streaks


def test_streak_calculation_logic():
    """Unit test for streak calculation edge cases."""
    today = date.today()
    d0 = today.isoformat()
    d1 = (today - timedelta(days=1)).isoformat()
    d2 = (today - timedelta(days=2)).isoformat()
    d3 = (today - timedelta(days=3)).isoformat()
    d5 = (today - timedelta(days=5)).isoformat()
    d6 = (today - timedelta(days=6)).isoformat()

    # Empty
    assert calculate_habit_streaks(set()) == (0, 0)

    # Completed today only
    assert calculate_habit_streaks({d0}) == (1, 1)

    # Completed today and yesterday
    assert calculate_habit_streaks({d0, d1}) == (2, 2)

    # 3 consecutive days up to today
    assert calculate_habit_streaks({d0, d1, d2}) == (3, 3)

    # Completed yesterday but not today yet (streak is alive for today)
    assert calculate_habit_streaks({d1, d2}) == (2, 2)

    # Broken streak: 5 days ago and 6 days ago (2 days streak in past), but missed recent days
    assert calculate_habit_streaks({d5, d6}) == (0, 2)


def test_create_habit_success(client):
    """Test creating a valid habit."""
    payload = {
        "name": "Morning 10-Minute Walk",
        "description": "Get morning sunlight and brisk walk",
        "frequency": "daily"
    }
    response = client.post("/api/habits", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["habit"]["name"] == "Morning 10-Minute Walk"
    assert data["habit"]["current_streak"] == 0
    assert data["habit"]["is_completed_today"] is False


def test_create_habit_validation(client):
    """Test habit input validation."""
    # Empty name
    res_empty = client.post("/api/habits", json={"name": ""})
    assert res_empty.status_code == 400
    assert "name is required" in res_empty.get_json()["error"].lower()

    # Invalid frequency
    res_freq = client.post("/api/habits", json={
        "name": "Drink Water",
        "frequency": "hourly"  # Not in daily, weekdays, weekly
    })
    assert res_freq.status_code == 400
    assert "invalid frequency" in res_freq.get_json()["error"].lower()


def test_habit_toggle_and_duplicate_prevention(client):
    """Test toggling habit completion for today and undo behavior."""
    res_create = client.post("/api/habits", json={"name": "Read 10 Pages"})
    habit_id = res_create.get_json()["habit"]["id"]

    # 1. Mark completed for today
    res_toggle1 = client.post(f"/api/habits/{habit_id}/toggle", json={})
    assert res_toggle1.status_code == 200
    data1 = res_toggle1.get_json()
    assert data1["data"]["is_completed"] is True
    assert data1["data"]["habit"]["is_completed_today"] is True
    assert data1["data"]["habit"]["current_streak"] == 1

    # 2. Toggle again (undo today)
    res_toggle2 = client.post(f"/api/habits/{habit_id}/toggle", json={})
    assert res_toggle2.status_code == 200
    data2 = res_toggle2.get_json()
    assert data2["data"]["is_completed"] is False
    assert data2["data"]["habit"]["is_completed_today"] is False
    assert data2["data"]["habit"]["current_streak"] == 0


def test_habit_history_and_deletion(client):
    """Test updating and deleting habits."""
    res_create = client.post("/api/habits", json={"name": "Nightly Meditation"})
    habit_id = res_create.get_json()["habit"]["id"]

    # Update habit
    res_update = client.put(f"/api/habits/{habit_id}", json={
        "name": "Nightly Meditation & Breathwork",
        "frequency": "weekdays"
    })
    assert res_update.status_code == 200
    assert res_update.get_json()["habit"]["name"] == "Nightly Meditation & Breathwork"
    assert res_update.get_json()["habit"]["frequency"] == "weekdays"

    # Delete habit
    res_del = client.delete(f"/api/habits/{habit_id}")
    assert res_del.status_code == 200

    # Ensure 404
    res_get = client.get(f"/api/habits/{habit_id}")
    assert res_get.status_code == 404
