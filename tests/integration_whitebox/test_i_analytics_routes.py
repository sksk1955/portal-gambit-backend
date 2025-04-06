# Filename: tests/integration_whitebox/test_i_analytics_routes.py
import uuid
from datetime import datetime, timezone, timedelta

from models.game_history import GameResult  # For result values
# Import models/schemas for validation
from schemas.analytics_schemas import (
    DailyStats, PlayerPerformance, GlobalStats
)


# Fixtures: client, mock_analytics_service, test_user_1_uid, test_user_2_uid from conftest.py

# --- Test Cases for /analytics/games/{game_id} POST ---

def test_record_game_analytics_success(client, mock_analytics_service, test_user_1_uid, test_user_2_uid):
    """Test successfully recording analytics for a game the user participated in."""
    # Arrange
    game_id = f"int_ana_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    # Payload must match GameAnalyticsCreate schema
    analytics_payload = {
        "game_id": game_id,  # Note: Also in path, check if schema needs it
        "white_player_id": test_user_1_uid,  # Matches authenticated user
        "black_player_id": test_user_2_uid,
        "start_time": (now - timedelta(minutes=7)).isoformat(),
        "end_time": now.isoformat(),
        "result": GameResult.WHITE_WIN.value,
        "moves": ["e4", "e5", "Nf3", "Nc6"],
        "rating_change": {"white": 9, "black": -9},
        "game_type": "portal_gambit",
        "time_control": {"initial": 600, "increment": 0}
    }
    # Mock service success
    mock_analytics_service.record_game_analytics.return_value = True

    # Act
    response = client.post(f"/analytics/games/{game_id}", json=analytics_payload)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Game analytics recorded successfully"}
    # Verify service call
    mock_analytics_service.record_game_analytics.assert_called_once()
    call_arg = mock_analytics_service.record_game_analytics.call_args[0][0]
    # Service receives a dictionary matching the payload + game_id from path
    assert isinstance(call_arg, dict)
    assert call_arg['game_id'] == game_id
    assert call_arg['white_player_id'] == test_user_1_uid
    assert call_arg['result'] == GameResult.WHITE_WIN.value  # Ensure correct data passed


def test_record_game_analytics_forbidden(client, mock_analytics_service, test_user_1_uid):
    """Test recording analytics for a game the user did NOT participate in."""
    # Arrange
    game_id = f"int_ana_forbidden_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    analytics_payload = {
        "game_id": game_id,
        "white_player_id": "other_player_A",  # Not authenticated user
        "black_player_id": "other_player_B",  # Not authenticated user
        "start_time": (now - timedelta(minutes=3)).isoformat(),
        "end_time": now.isoformat(),
        "result": GameResult.DRAW.value,
        "moves": ["c4", "c5"],
        "rating_change": {"white": 0, "black": 0},
        "game_type": "standard",
        "time_control": {"initial": 180, "increment": 2}
    }

    # Act
    response = client.post(f"/analytics/games/{game_id}", json=analytics_payload)

    # Assert: Route should return 403
    assert response.status_code == 403
    assert "Can only record analytics for games you participated in" in response.json().get("detail", "")
    mock_analytics_service.record_game_analytics.assert_not_called()


def test_record_game_analytics_service_fails(client, mock_analytics_service, test_user_1_uid):
    """Test recording analytics when the service layer returns False."""
    # Arrange: Payload is valid (contains all required fields), but service fails
    game_id = f"int_ana_fail_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=6)
    analytics_payload = {
        "game_id": game_id,  # Required
        "white_player_id": test_user_1_uid,  # Required
        "black_player_id": "opponent_p2_fail",  # Required
        "start_time": start_time.isoformat(),  # Required
        "end_time": now.isoformat(),  # Required
        "result": GameResult.DRAW.value,  # Required
        "moves": ["e4", "e5", "Nf3"],  # Required
        "rating_change": {"white": 0, "black": 0},  # Required
        "game_type": "portal_gambit_fail",  # Required
        "time_control": {"initial": 300, "increment": 1}  # Required
    }
    mock_analytics_service.record_game_analytics.return_value = False  # Simulate failure

    # Act
    response = client.post(f"/analytics/games/{game_id}", json=analytics_payload)

    # Assert: Check response reflects service failure
    assert response.status_code == 500  # Route succeeded (service failed)
    assert "Failed to record game analytics" in response.json().get("detail", "")
    mock_analytics_service.record_game_analytics.assert_called_once()
    # Optional: Check the argument passed
    call_arg = mock_analytics_service.record_game_analytics.call_args[0][0]
    assert isinstance(call_arg, dict)
    assert call_arg['game_id'] == game_id
    assert call_arg['result'] == GameResult.DRAW.value


def test_record_game_analytics_validation_error(client, mock_analytics_service):
    """Test recording analytics with missing required fields in payload."""
    # Arrange: Missing 'black_player_id', 'result', 'moves', etc.
    game_id = f"int_ana_invalid_{uuid.uuid4().hex}"
    analytics_payload = {
        "game_id": game_id,
        "white_player_id": "some_user",  # Need at least one field
    }

    # Act
    response = client.post(f"/analytics/games/{game_id}", json=analytics_payload)

    # Assert: FastAPI validation should return 422
    assert response.status_code == 422
    mock_analytics_service.record_game_analytics.assert_not_called()


# --- Test Cases for /analytics/daily/{date} GET ---

def test_get_daily_stats_success(client, mock_analytics_service):
    """Test getting daily stats when service returns data."""
    # Arrange
    test_date_str = "2024-02-15T12:00:00Z"  # Valid ISO date string
    # Mock service to return DailyStats object (use fixture or create instance)
    mock_stats = DailyStats(
        total_games=10, average_duration=500.0, average_moves=55.0, white_wins=4,
        black_wins=5, draws=1, abandoned=0, game_types={'portal': 10}, time_controls={'300/5': 10}
    )
    mock_analytics_service.get_daily_stats.return_value = mock_stats

    # Act
    response = client.get(f"/analytics/daily/{test_date_str}")

    # Assert: Response should be the serialized DailyStats data
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total_games"] == mock_stats.total_games
    assert response_data["white_wins"] == mock_stats.white_wins
    assert response_data["game_types"] == mock_stats.game_types
    # Assert service call (FastAPI parses path date string to datetime)
    mock_analytics_service.get_daily_stats.assert_called_once()
    call_arg = mock_analytics_service.get_daily_stats.call_args[0][0]
    assert isinstance(call_arg, datetime)
    assert call_arg.year == 2024
    assert call_arg.month == 2
    assert call_arg.day == 15


def test_get_daily_stats_invalid_date(client, mock_analytics_service):
    """Test getting daily stats with an invalid date format in path."""
    # Arrange
    invalid_date_str = "15-Feb-2024"

    # Act
    response = client.get(f"/analytics/daily/{invalid_date_str}")

    # Assert: FastAPI path param validation should fail
    assert response.status_code == 422
    mock_analytics_service.get_daily_stats.assert_not_called()


# --- Test Cases for /analytics/players/{user_id}/performance GET ---

def test_get_player_performance_success(client, mock_analytics_service, test_user_2_uid):
    """Test getting player performance when service returns data."""
    # Arrange
    user_id_to_get = test_user_2_uid
    days = 90
    # Mock service returns PlayerPerformance object
    mock_perf = PlayerPerformance(
        rating_progression=[{'ts': '...', 'change': 5}], average_game_duration=600.0,
        preferred_time_control='900/10', preferred_game_type='portal', win_rate=0.65,
        performance_by_color={'white': {'games': 10, 'wins': 7}, 'black': {'games': 12, 'wins': 7}},
        average_moves_per_game=62.0
    )
    mock_analytics_service.get_player_performance.return_value = mock_perf

    # Act
    response = client.get(f"/analytics/players/{user_id_to_get}/performance?days={days}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    # Check some key fields match serialized mock data
    assert response_data["win_rate"] == mock_perf.win_rate
    assert response_data["preferred_game_type"] == mock_perf.preferred_game_type
    assert response_data["performance_by_color"]["white"]["wins"] == 7
    # Assert service call with correct params
    mock_analytics_service.get_player_performance.assert_called_once_with(user_id_to_get, days)


def test_get_player_performance_default_days(client, mock_analytics_service, test_user_1_uid):
    """Test getting player performance using the default days parameter."""
    # Arrange
    user_id_to_get = test_user_1_uid
    default_days = 30  # From route definition default
    mock_analytics_service.get_player_performance.return_value = PlayerPerformance(rating_progression=[],
                                                                                   average_game_duration=0,
                                                                                   preferred_time_control=None,
                                                                                   preferred_game_type=None, win_rate=0,
                                                                                   performance_by_color={},
                                                                                   average_moves_per_game=0)

    # Act: Call without explicit days param
    response = client.get(f"/analytics/players/{user_id_to_get}/performance")

    # Assert
    assert response.status_code == 200
    assert response.json()["win_rate"] == 0  # Check against mock return
    # Verify service called with default days
    mock_analytics_service.get_player_performance.assert_called_once_with(user_id_to_get, default_days)


# --- Test Cases for /analytics/global GET ---

def test_get_global_stats_success(client, mock_analytics_service):
    """Test getting global stats when service returns data."""
    # Arrange: Mock service returns GlobalStats object
    now = datetime.now(timezone.utc)
    mock_global = GlobalStats(
        total_games=5000, white_win_rate=0.485, average_game_duration=550.0,
        average_moves_per_game=58.2, popular_time_controls={'600/5': 2000},
        popular_game_types={'portal': 4800}, last_updated=now
    )
    mock_analytics_service.get_global_stats.return_value = mock_global

    # Act
    response = client.get("/analytics/global")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    # Check response matches serialized mock data
    assert response_data["total_games"] == mock_global.total_games
    assert response_data["white_win_rate"] == mock_global.white_win_rate
    assert response_data["last_updated"] == mock_global.last_updated.isoformat().replace('+00:00', 'Z')
    # Assert service call
    mock_analytics_service.get_global_stats.assert_called_once_with()
