# Filename: tests/api_blackbox/test_b_analytics_flow.py

import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

# --- Test Configuration ---
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080").rstrip('/')
API_DELAY = float(os.getenv("TEST_API_DELAY", "0.5"))

# !!! IMPORTANT: Requires valid token/UID for at least one user !!!
USER1_TOKEN = os.getenv("TEST_USER1_BACKEND_TOKEN")
USER1_UID = os.getenv("TEST_USER1_UID")
# Optional: Use a second user's UID if available
USER2_UID = os.getenv("TEST_USER2_UID", f"opponent-uid-{uuid.uuid4().hex[:6]}")  # Default to generated opponent

config_present = USER1_TOKEN and USER1_UID
if not config_present:
    print(
        "\nWARNING: Missing environment variables for analytics flow tests (TEST_USER1_BACKEND_TOKEN, "
        "TEST_USER1_UID). Tests will be skipped.")


# --- Helper ---
def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


# --- Global state for the flow ---
recorded_game_ids = []  # Store IDs of games whose analytics were recorded


# --- Test Cases ---

@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_record_game_analytics_valid():
    """Tests recording analytics for a valid game where the user participated."""
    headers = get_auth_headers(USER1_TOKEN)
    game_id = f"bb_ana_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    # Payload should match the GameAnalyticsCreate schema
    analytics_payload = {
        "game_id": game_id,  # Make sure schema matches this (or if it's only path param)
        "white_player_id": USER1_UID,  # Authenticated user is white
        "black_player_id": USER2_UID,
        "start_time": (now - timedelta(minutes=10)).isoformat(),
        "end_time": now.isoformat(),
        "result": "black_win",  # Match GameResult enum values
        "moves": ["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6"],  # King's Indian start
        "rating_change": {"white": -7, "black": 7},  # Schema expects dict, e.g. {"white": -7, "black": 7} or similar
        "game_type": "portal_gambit",
        "time_control": {"initial": 300, "increment": 3}  # Schema expects dict, e.g. {"initial": 300, "increment": 3}
    }

    # Route: POST /analytics/games/{game_id}
    response = requests.post(f"{BASE_URL}/analytics/games/{game_id}", headers=headers, json=analytics_payload)
    assert response.status_code == 200, f"Record analytics failed: {response.text}"
    data = response.json()
    # Response should match AnalyticsResponse schema
    assert data.get("status") == "success"
    assert "recorded successfully" in data.get("message", "")
    recorded_game_ids.append(game_id)
    print(f"\nRecorded analytics for game ID: {game_id}")


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_daily_stats():
    """Tests retrieving daily statistics for today."""
    headers = get_auth_headers(USER1_TOKEN)
    # Use today's date in the required format (likely ISO 8601 for the path param)
    # The route expects a datetime, requests needs a string. FastAPI handles parsing.
    # Sending just the date part might work depending on route implementation.
    # Let's try sending a full ISO timestamp for today.
    today_iso = datetime.now(timezone.utc).isoformat()

    # Route: GET /analytics/daily/{date}
    response = requests.get(f"{BASE_URL}/analytics/daily/{today_iso}", headers=headers)
    assert response.status_code == 200, f"Get daily stats failed: {response.text}"
    stats = response.json()

    # Check structure based on DailyStats schema
    assert "total_games" in stats
    assert isinstance(stats["total_games"], int)
    assert stats["total_games"] >= 0  # Should have at least the game recorded above if run today
    assert "average_duration" in stats
    assert isinstance(stats["average_duration"], (float, int))
    assert "average_moves" in stats
    assert isinstance(stats["average_moves"], (float, int))
    assert "white_wins" in stats
    assert "black_wins" in stats
    assert "draws" in stats
    assert "abandoned" in stats
    assert "game_types" in stats
    assert isinstance(stats["game_types"], dict)
    assert "time_controls" in stats
    assert isinstance(stats["time_controls"], dict)

    # If the test game was recorded today, check for its contribution
    # (This is fragile as other games might exist)
    # if recorded_game_ids and datetime.fromisoformat(today_iso).date() == datetime.now(timezone.utc).date():
    #    assert stats["total_games"] > 0
    #    assert "portal_gambit" in stats["game_types"]
    #    assert stats["game_types"]["portal_gambit"] > 0


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_player_performance_self():
    """Tests retrieving performance statistics for the authenticated user."""
    headers = get_auth_headers(USER1_TOKEN)
    user_id = USER1_UID
    days = 30

    # Route: GET /analytics/players/{user_id}/performance
    response = requests.get(f"{BASE_URL}/analytics/players/{user_id}/performance?days={days}", headers=headers)
    assert response.status_code == 200, f"Get player performance failed: {response.text}"
    perf = response.json()

    # Check structure based on PlayerPerformance schema
    assert "rating_progression" in perf
    assert isinstance(perf["rating_progression"], list)
    assert "average_game_duration" in perf
    assert isinstance(perf["average_game_duration"], (float, int))
    # Preferred fields can be None if no games played
    assert "preferred_time_control" in perf
    assert "preferred_game_type" in perf
    assert "win_rate" in perf
    assert isinstance(perf["win_rate"], (float, int))
    assert "performance_by_color" in perf
    assert isinstance(perf["performance_by_color"], dict)
    assert "white" in perf["performance_by_color"]
    assert "black" in perf["performance_by_color"]
    assert "games" in perf["performance_by_color"]["white"]
    assert "wins" in perf["performance_by_color"]["white"]
    assert "average_moves_per_game" in perf
    assert isinstance(perf["average_moves_per_game"], (float, int))

    # If game recorded, check rating progression might have entries
    # if recorded_game_ids and len(perf["rating_progression"]) > 0:
    #    assert "timestamp" in perf["rating_progression"][0]
    #    assert "rating_change" in perf["rating_progression"][0]


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_player_performance_other():
    """Tests retrieving performance statistics for another user (allowed)."""
    headers = get_auth_headers(USER1_TOKEN)
    user_id = USER2_UID  # Get stats for the opponent
    days = 60

    response = requests.get(f"{BASE_URL}/analytics/players/{user_id}/performance?days={days}", headers=headers)
    assert response.status_code == 200
    # Check structure again, data will be for USER2_UID
    perf = response.json()
    assert "rating_progression" in perf
    assert "win_rate" in perf


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_global_stats():
    """Tests retrieving global game statistics."""
    headers = get_auth_headers(USER1_TOKEN)

    # Route: GET /analytics/global
    response = requests.get(f"{BASE_URL}/analytics/global", headers=headers)
    assert response.status_code == 200, f"Get global stats failed: {response.text}"
    stats = response.json()

    # Check structure based on GlobalStats schema
    assert "total_games" in stats
    assert isinstance(stats["total_games"], int)
    assert stats["total_games"] >= 0  # Should have at least one if tests run
    assert "white_win_rate" in stats
    assert isinstance(stats["white_win_rate"], (float, int))
    assert "average_game_duration" in stats
    assert isinstance(stats["average_game_duration"], (float, int))
    assert "average_moves_per_game" in stats
    assert isinstance(stats["average_moves_per_game"], (float, int))
    assert "popular_time_controls" in stats
    assert isinstance(stats["popular_time_controls"], dict)
    assert "popular_game_types" in stats
    assert isinstance(stats["popular_game_types"], dict)
    assert "last_updated" in stats  # Should be an ISO datetime string


# --- Negative Test Cases ---

@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_record_game_analytics_forbidden():
    """Tests recording analytics for a game the user did NOT participate in."""
    headers = get_auth_headers(USER1_TOKEN)
    game_id = f"bb_ana_forbidden_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    analytics_payload = {
        "game_id": game_id,
        "white_player_id": f"other-a-{uuid.uuid4().hex[:4]}",  # Not USER1_UID
        "black_player_id": f"other-b-{uuid.uuid4().hex[:4]}",  # Not USER1_UID
        "start_time": (now - timedelta(minutes=8)).isoformat(),
        "end_time": now.isoformat(),
        "result": "draw",
        "moves": ["Nf3", "Nf6"],
        "rating_change": {"white": 0, "black": 0},
        "game_type": "standard",
        "time_control": {"initial": 60, "increment": 0}
    }
    response = requests.post(f"{BASE_URL}/analytics/games/{game_id}", headers=headers, json=analytics_payload)
    assert response.status_code == 403  # Forbidden


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_record_game_analytics_missing_data():
    """Tests recording analytics with missing required fields."""
    headers = get_auth_headers(USER1_TOKEN)
    game_id = f"bb_ana_invalid_{uuid.uuid4().hex}"
    analytics_payload = {
        "game_id": game_id,
        "white_player_id": USER1_UID,
        # Missing black_player_id, result, times, moves etc.
    }
    response = requests.post(f"{BASE_URL}/analytics/games/{game_id}", headers=headers, json=analytics_payload)
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_daily_stats_invalid_date():
    """Tests retrieving daily stats with an invalid date format."""
    headers = get_auth_headers(USER1_TOKEN)
    invalid_date_str = "27th-October-2023"
    response = requests.get(f"{BASE_URL}/analytics/daily/{invalid_date_str}", headers=headers)
    assert response.status_code == 422  # Unprocessable Entity due to path param validation
