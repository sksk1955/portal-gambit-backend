# Filename: tests/api_blackbox/test_b_history_flow.py

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
# Optional: Use a second user's UID if available for between_players tests
USER2_UID = os.getenv("TEST_USER2_UID", f"opponent-uid-{uuid.uuid4().hex[:6]}")  # Default to generated opponent

config_present = USER1_TOKEN and USER1_UID
if not config_present:
    print(
        "\nWARNING: Missing environment variables for history flow tests (TEST_USER1_BACKEND_TOKEN, TEST_USER1_UID). "
        "Tests will be skipped.")


# --- Helper ---
def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


# --- Global state for the flow ---
# Store IDs of games archived during the tests for later retrieval/verification
archived_game_ids = []


# --- Fixture for Optional Cleanup ---
# Note: Deleting history might not be a feature, so cleanup is less common here.
# We'll rely on unique game IDs per run.

# --- Test Cases ---

@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_archive_game_valid():
    """Tests archiving a valid game where the user participated."""
    headers = get_auth_headers(USER1_TOKEN)
    game_id = f"bb_hist_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    # Payload must match the GameHistory model structure
    game_payload = {
        "game_id": game_id,
        "white_player_id": USER1_UID,  # Authenticated user is white
        "black_player_id": USER2_UID,  # Can be any opponent ID
        "start_time": (now - timedelta(minutes=20)).isoformat(),
        "end_time": now.isoformat(),
        "result": "white_win",  # Match GameResult enum values
        "winner_id": USER1_UID,
        "moves": ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],  # Sicilian Najdorf start
        "initial_position": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "white_rating": 1300,
        "black_rating": 1280,
        "rating_change": {"white": 9, "black": -9},
        "game_type": "portal_gambit",
        "time_control": {"initial": 900, "increment": 10}
    }

    response = requests.post(f"{BASE_URL}/history/games", headers=headers, json=game_payload)
    assert response.status_code == 200, f"Archive game failed: {response.text}"
    data = response.json()
    assert data.get("status") == "success"
    assert "archived successfully" in data.get("message", "")
    archived_game_ids.append(game_id)  # Store for later tests
    print(f"\nArchived game ID: {game_id}")


@pytest.mark.skipif(not config_present or not archived_game_ids, reason="Requires token/UID and an archived game")
def test_api_get_archived_game_valid():
    """Tests retrieving a specific game that was just archived."""
    headers = get_auth_headers(USER1_TOKEN)
    game_id = archived_game_ids[-1]  # Get the most recently archived game
    response = requests.get(f"{BASE_URL}/history/games/{game_id}", headers=headers)
    assert response.status_code == 200, f"Get game failed: {response.text}"
    game_data = response.json()
    # Verify key fields match the archived game
    assert game_data["game_id"] == game_id
    assert game_data["white_player_id"] == USER1_UID
    assert game_data["black_player_id"] == USER2_UID
    assert game_data["result"] == "white_win"
    assert len(game_data["moves"]) == 10
    assert game_data["rating_change"]["white"] == 9


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_user_games():
    """Tests retrieving the list of games for the authenticated user."""
    # This assumes test_api_archive_game_valid ran and archived at least one game
    headers = get_auth_headers(USER1_TOKEN)
    limit = 5
    response = requests.get(f"{BASE_URL}/history/users/{USER1_UID}/games?limit={limit}", headers=headers)
    assert response.status_code == 200
    user_games = response.json()
    assert isinstance(user_games, list)
    assert len(user_games) <= limit
    # Check if the recently archived game(s) are present (likely at the start)
    if archived_game_ids:
        found = any(game["game_id"] in archived_game_ids for game in user_games)
        assert found, f"Archived games ({archived_game_ids}) not found in user's history"
        # Verify sorting (most recent first)
        if len(user_games) > 1:
            # Parse end_time strings to datetime objects for comparison
            time_format = "%Y-%m-%dT%H:%M:%S.%f%z" if '.' in user_games[0]["end_time"] else "%Y-%m-%dT%H:%M:%S%z"
            try:
                dt1 = datetime.strptime(user_games[0]["end_time"].replace("Z", "+00:00"), time_format)
                dt2 = datetime.strptime(user_games[1]["end_time"].replace("Z", "+00:00"), time_format)
                assert dt1 >= dt2, "User games not sorted by end_time descending"
            except ValueError as e:
                print(f"Warning: Could not parse datetime for sorting check: {e}")


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_games_between_players():
    """Tests retrieving games between User1 and User2."""
    # Assumes at least one game was archived between USER1_UID and USER2_UID
    headers = get_auth_headers(USER1_TOKEN)
    limit = 10
    player1 = USER1_UID
    player2 = USER2_UID
    response = requests.get(f"{BASE_URL}/history/games/between/{player1}/{player2}?limit={limit}", headers=headers)
    assert response.status_code == 200
    between_games = response.json()
    assert isinstance(between_games, list)
    assert len(between_games) <= limit
    if archived_game_ids:
        found = any(game["game_id"] in archived_game_ids for game in between_games)
        assert found, f"Archived game between {player1} and {player2} not found"
        # Verify participants are correct
        for game in between_games:
            assert (game["white_player_id"] == player1 and game["black_player_id"] == player2) or \
                   (game["white_player_id"] == player2 and game["black_player_id"] == player1)


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_user_stats():
    """Tests retrieving game statistics for the user."""
    headers = get_auth_headers(USER1_TOKEN)
    days = 90
    response = requests.get(f"{BASE_URL}/history/users/{USER1_UID}/stats?days={days}", headers=headers)
    assert response.status_code == 200
    stats = response.json()
    # Check structure based on UserGameStats schema
    assert "total_games" in stats
    assert isinstance(stats["total_games"], int)
    assert stats["total_games"] >= 0  # Should be non-negative
    assert "wins" in stats
    assert "losses" in stats
    assert "draws" in stats
    assert "white_games" in stats
    assert "black_games" in stats
    assert "rating_change" in stats
    assert "average_game_length" in stats
    assert "total_moves" in stats
    # Basic sanity check
    assert stats["wins"] + stats["losses"] + stats["draws"] <= stats["total_games"]
    assert stats["white_games"] + stats["black_games"] == stats["total_games"]


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_popular_openings():
    """Tests retrieving popular openings."""
    headers = get_auth_headers(USER1_TOKEN)
    limit = 5
    response = requests.get(f"{BASE_URL}/history/openings/popular?limit={limit}", headers=headers)
    assert response.status_code == 200
    openings = response.json()
    assert isinstance(openings, list)
    assert len(openings) <= limit
    # Check structure based on OpeningStats schema if results exist
    if openings:
        opening = openings[0]
        assert "moves" in opening  # String of first few moves
        assert isinstance(opening["moves"], str)
        assert "count" in opening  # How many times played
        assert isinstance(opening["count"], int)
        assert "wins" in opening  # How many non-abandoned games with this opening
        assert isinstance(opening["wins"], int)
        # Check sorting (most popular first)
        if len(openings) > 1:
            assert openings[0]["count"] >= openings[1]["count"]


# --- Negative Test Cases ---

@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_archive_game_forbidden():
    """Tests archiving a game where the user did NOT participate."""
    headers = get_auth_headers(USER1_TOKEN)
    game_id = f"bb_hist_forbidden_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    game_payload = {
        "game_id": game_id,
        "white_player_id": f"other-player-a-{uuid.uuid4().hex[:4]}",  # Not USER1_UID
        "black_player_id": f"other-player-b-{uuid.uuid4().hex[:4]}",  # Not USER1_UID
        "start_time": (now - timedelta(minutes=5)).isoformat(),
        "end_time": now.isoformat(),
        "result": "draw",
        "winner_id": None,
        "moves": ["e4", "e5"],
        "initial_position": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "white_rating": 1100, "black_rating": 1110,
        "rating_change": {"white": 0, "black": 0},
        "game_type": "standard",
        "time_control": {"initial": 180, "increment": 0}
    }
    response = requests.post(f"{BASE_URL}/history/games", headers=headers, json=game_payload)
    assert response.status_code == 403  # Forbidden


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_archive_game_missing_data():
    """Tests archiving a game with missing required fields."""
    headers = get_auth_headers(USER1_TOKEN)
    game_payload = {
        "game_id": f"bb_hist_invalid_{uuid.uuid4().hex}",
        "white_player_id": USER1_UID,
        # Missing black_player_id, result, end_time, moves etc.
    }
    response = requests.post(f"{BASE_URL}/history/games", headers=headers, json=game_payload)
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.skipif(not config_present, reason="Requires token/UID for User1")
def test_api_get_non_existent_game():
    """Tests retrieving a game ID that doesn't exist."""
    headers = get_auth_headers(USER1_TOKEN)
    non_existent_id = f"non-existent-game-{uuid.uuid4().hex}"
    response = requests.get(f"{BASE_URL}/history/games/{non_existent_id}", headers=headers)
    assert response.status_code == 404  # Not Found
