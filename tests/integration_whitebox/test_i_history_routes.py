# Filename: tests/integration_whitebox/test_i_history_routes.py
import uuid
from datetime import datetime, timezone, timedelta

# Import models/schemas for validation
from models.game_history import GameHistory, GameResult
from schemas.history_schemas import (
    UserGameStats, OpeningStats
)


# Fixtures: client, mock_history_service, sample_game_history,
# test_user_1_uid, test_user_2_uid from conftest.py

# --- Test Cases for /history/games POST ---

def test_archive_game_success(client, mock_history_service, test_user_1_uid, test_user_2_uid):
    """Test successfully archiving a game where the authenticated user participated."""
    # Arrange: Create payload matching GameHistory model
    now = datetime.now(timezone.utc)
    game_payload = {
        "game_id": f"int_hist_{uuid.uuid4().hex}",
        "white_player_id": test_user_1_uid,  # Authenticated user
        "black_player_id": test_user_2_uid,
        "start_time": (now - timedelta(minutes=12)).isoformat(),
        "end_time": now.isoformat(),
        "result": GameResult.BLACK_WIN.value,  # Use enum value
        "winner_id": test_user_2_uid,
        "moves": ["d4", "Nf6", "c4", "e6"],
        "initial_position": "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
        "white_rating": 1400,
        "black_rating": 1410,
        "rating_change": {"white": -6, "black": 6},
        "game_type": "portal_gambit",
        "time_control": {"initial": 1800, "increment": 15}
    }
    # Mock service success
    mock_history_service.archive_game.return_value = True

    # Act
    response = client.post("/history/games", json=game_payload)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Game archived successfully"}
    # Verify service called with a GameHistory object
    mock_history_service.archive_game.assert_called_once()
    call_arg = mock_history_service.archive_game.call_args[0][0]
    assert isinstance(call_arg, GameHistory)
    assert call_arg.game_id == game_payload["game_id"]
    assert call_arg.white_player_id == test_user_1_uid


def test_archive_game_forbidden(client, mock_history_service, test_user_1_uid):
    """Test archiving a game where the authenticated user did NOT participate."""
    # Arrange
    now = datetime.now(timezone.utc)
    game_payload = {
        "game_id": f"int_hist_forbidden_{uuid.uuid4().hex}",
        "white_player_id": "other_player_1",  # Not authenticated user
        "black_player_id": "other_player_2",  # Not authenticated user
        "start_time": (now - timedelta(minutes=5)).isoformat(),
        "end_time": now.isoformat(),
        "result": GameResult.DRAW.value,
        "winner_id": None,
        "moves": ["e4", "e5"],
        "white_rating": 1000, "black_rating": 1000,
        "rating_change": {"white": 0, "black": 0},
        "game_type": "standard", "time_control": {"initial": 60, "increment": 0}
    }

    # Act
    response = client.post("/history/games", json=game_payload)

    # Assert: Route should return 403
    assert response.status_code == 403
    assert "Can only archive games you participated in" in response.json().get("detail", "")
    mock_history_service.archive_game.assert_not_called()


def test_archive_game_service_fails(client, mock_history_service, test_user_1_uid):
    """Test archiving when the service layer returns False."""
    # Arrange: Payload is valid (contains all required fields), but service fails
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=5)
    game_payload = {
        "game_id": "fail_game_archive",  # Required
        "white_player_id": test_user_1_uid,  # Required
        "black_player_id": "opponent_p2",  # Required
        "start_time": start_time.isoformat(),  # Optional (can be sent)
        "end_time": now.isoformat(),  # Required
        "result": GameResult.DRAW.value,  # Required
        "winner_id": None,  # Optional
        "moves": ["e4", "e5"],  # Required
        "initial_position": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Optional (has default)
        "white_rating": 1190,  # Required
        "black_rating": 1185,  # Required
        "rating_change": {"white": 0, "black": 0},  # Required
        "game_type": "portal_gambit",  # Optional (has default)
        "time_control": {"initial": 300, "increment": 0}  # Required
    }
    mock_history_service.archive_game.return_value = False  # Simulate failure

    # Act
    response = client.post("/history/games", json=game_payload)

    # Assert
    assert response.status_code == 200  # Route succeeded
    assert response.json() == {"status": "error", "message": "Failed to archive game"}
    mock_history_service.archive_game.assert_called_once()
    # Optional check on the argument passed to the service
    call_arg = mock_history_service.archive_game.call_args[0][0]
    assert isinstance(call_arg, GameHistory)
    assert call_arg.game_id == "fail_game_archive"
    assert call_arg.result == GameResult.DRAW


def test_archive_game_validation_error(client, mock_history_service, test_user_1_uid):
    """Test archiving with missing required fields in payload."""
    # Arrange: Missing 'black_player_id', 'result', 'moves', etc.
    game_payload = {
        "game_id": "invalid_game",
        "white_player_id": test_user_1_uid,
    }

    # Act
    response = client.post("/history/games", json=game_payload)

    # Assert: FastAPI validation should return 422
    assert response.status_code == 422
    mock_history_service.archive_game.assert_not_called()


# --- Test Cases for /history/games/{game_id} GET ---

def test_get_game_found(client, mock_history_service, sample_game_history):
    """Test retrieving a specific game when found by the service."""
    # Arrange: Mock service returns the sample game
    game_id = sample_game_history.game_id
    mock_history_service.get_game.return_value = sample_game_history

    # Act
    response = client.get(f"/history/games/{game_id}")

    # Assert: Response should be the serialized game data
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["game_id"] == game_id
    assert response_data["white_player_id"] == sample_game_history.white_player_id
    assert response_data["result"] == sample_game_history.result.value
    # Compare a datetime field
    assert response_data["end_time"] == sample_game_history.end_time.isoformat().replace('+00:00', 'Z')
    # Assert service call
    mock_history_service.get_game.assert_called_once_with(game_id)


def test_get_game_not_found(client, mock_history_service):
    """Test retrieving a game when the service returns None."""
    # Arrange: Mock service returns None
    game_id = "non_existent_game_id"
    mock_history_service.get_game.return_value = None

    # Act
    response = client.get(f"/history/games/{game_id}")

    # Assert: Route should return 404
    assert response.status_code == 404
    assert "Game not found" in response.json().get("detail", "")
    mock_history_service.get_game.assert_called_once_with(game_id)


# --- Test Cases for /history/users/{user_id}/games GET ---

def test_get_user_games_success(client, mock_history_service, sample_game_history, test_user_1_uid):
    """Test getting user games when service returns data."""
    # Arrange
    user_id_to_get = test_user_1_uid
    limit = 15
    # Mock service returns list with sample game
    mock_history_service.get_user_games.return_value = [sample_game_history]

    # Act
    response = client.get(f"/history/users/{user_id_to_get}/games?limit={limit}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["game_id"] == sample_game_history.game_id
    # Assert service call with correct params from path and query
    mock_history_service.get_user_games.assert_called_once_with(user_id_to_get, limit)


def test_get_user_games_default_limit(client, mock_history_service, test_user_1_uid):
    """Test getting user games using the default limit."""
    # Arrange
    user_id_to_get = test_user_1_uid
    default_limit = 50  # From GameHistoryParams schema default
    mock_history_service.get_user_games.return_value = []  # Return empty list for simplicity

    # Act: Call without explicit limit query param
    response = client.get(f"/history/users/{user_id_to_get}/games")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    # Verify service called with the default limit
    mock_history_service.get_user_games.assert_called_once_with(user_id_to_get, default_limit)


# --- Test Cases for /history/games/between/{player1_id}/{player2_id} GET ---

def test_get_games_between_players_success(client, mock_history_service, sample_game_history, test_user_1_uid,
                                           test_user_2_uid):
    """Test getting games between two players when service returns data."""
    # Arrange
    player1 = test_user_1_uid
    player2 = test_user_2_uid
    limit = 8
    # Mock service returns list with sample game
    mock_history_service.get_games_between_players.return_value = [sample_game_history]

    # Act
    response = client.get(f"/history/games/between/{player1}/{player2}?limit={limit}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["game_id"] == sample_game_history.game_id
    # Assert service call with correct params
    mock_history_service.get_games_between_players.assert_called_once_with(player1, player2, limit)


def test_get_games_between_players_default_limit(client, mock_history_service, test_user_1_uid, test_user_2_uid):
    """Test getting games between players using the default limit."""
    # Arrange
    player1 = test_user_1_uid
    player2 = test_user_2_uid
    default_limit = 10  # From GamesBetweenPlayersParams schema default
    mock_history_service.get_games_between_players.return_value = []

    # Act: Call without explicit limit
    response = client.get(f"/history/games/between/{player1}/{player2}")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    # Verify service called with default limit
    mock_history_service.get_games_between_players.assert_called_once_with(player1, player2, default_limit)


# --- Test Cases for /history/users/{user_id}/stats GET ---

def test_get_user_stats_success(client, mock_history_service, test_user_1_uid):
    """Test getting user stats when service returns data."""
    # Arrange
    user_id_to_get = test_user_1_uid
    days = 60
    # Mock service returns UserGameStats data (use fixture or create dict)
    mock_stats_data = UserGameStats(
        total_games=25, wins=15, losses=8, draws=2, white_games=12, black_games=13,
        rating_change=45, average_game_length=750.5, total_moves=1200
    )
    mock_history_service.get_user_stats.return_value = mock_stats_data

    # Act
    response = client.get(f"/history/users/{user_id_to_get}/stats?days={days}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    # Check response structure matches UserGameStats
    assert response_data["total_games"] == mock_stats_data.total_games
    assert response_data["wins"] == mock_stats_data.wins
    assert response_data["rating_change"] == mock_stats_data.rating_change
    # Assert service call
    mock_history_service.get_user_stats.assert_called_once_with(user_id_to_get, days)


def test_get_user_stats_default_days(client, mock_history_service, test_user_1_uid):
    """Test getting user stats using the default days parameter."""
    # Arrange
    user_id_to_get = test_user_1_uid
    default_days = 30  # From UserStatsParams schema default
    mock_history_service.get_user_stats.return_value = UserGameStats(total_games=0, wins=0, losses=0, draws=0,
                                                                     white_games=0, black_games=0, rating_change=0,
                                                                     average_game_length=0, total_moves=0)

    # Act: Call without explicit days
    response = client.get(f"/history/users/{user_id_to_get}/stats")

    # Assert
    assert response.status_code == 200
    assert response.json()["total_games"] == 0  # Check against mock return
    # Verify service called with default days
    mock_history_service.get_user_stats.assert_called_once_with(user_id_to_get, default_days)


# --- Test Cases for /history/openings/popular GET ---

def test_get_popular_openings_success(client, mock_history_service):
    """Test getting popular openings when service returns data."""
    # Arrange
    limit = 3
    # Mock service returns list of OpeningStats data
    mock_openings_data = [
        OpeningStats(moves="e4 c5 Nf3", count=50, wins=28),
        OpeningStats(moves="d4 Nf6 c4", count=40, wins=20),
        OpeningStats(moves="e4 e5 Nf3", count=35, wins=19),
    ]
    mock_history_service.get_popular_openings.return_value = mock_openings_data

    # Act
    response = client.get(f"/history/openings/popular?limit={limit}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 3
    assert response_data[0]["moves"] == "e4 c5 Nf3"
    assert response_data[0]["count"] == 50
    # Assert service call
    mock_history_service.get_popular_openings.assert_called_once_with(limit)


def test_get_popular_openings_default_limit(client, mock_history_service):
    """Test getting popular openings using the default limit."""
    # Arrange
    default_limit = 10  # From PopularOpeningsParams schema default
    mock_history_service.get_popular_openings.return_value = []

    # Act: Call without explicit limit
    response = client.get("/history/openings/popular")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    # Verify service called with default limit
    mock_history_service.get_popular_openings.assert_called_once_with(default_limit)
