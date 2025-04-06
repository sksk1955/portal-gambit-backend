from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from models.game_history import GameHistory, GameResult  # Import model and enum
from services.base_service import BaseService  # Import BaseService
# Import the class to test and its dependencies/models
from services.history_service import HistoryService


@pytest.fixture
def history_service(mock_db_client):
    """Creates an instance of the HistoryService with the mocked DB client."""
    return HistoryService(mock_db_client)


# --- Test Cases ---

@pytest.mark.asyncio
async def test_archive_game_success(history_service, mock_db_client, sample_game_history):
    """Test successfully archiving a game."""
    game_data = sample_game_history
    # Mock the underlying set_document call used by archive_game
    with patch.object(BaseService, 'set_document', new_callable=AsyncMock) as mock_set:
        mock_set.return_value = True
        result = await history_service.archive_game(game_data)

    assert result is True
    # Assert BaseService.set_document was called correctly
    mock_set.assert_called_once_with(
        history_service.collection,  # 'game_history'
        game_data.game_id,
        game_data.model_dump()  # Changed from dict() to model_dump()
    )


@pytest.mark.asyncio
async def test_archive_game_failure(history_service, mock_db_client, sample_game_history):
    """Test game archiving when the database set operation fails."""
    game_data = sample_game_history
    with patch.object(BaseService, 'set_document', new_callable=AsyncMock) as mock_set:
        mock_set.return_value = False  # Simulate failure
        result = await history_service.archive_game(game_data)

    assert result is False
    mock_set.assert_called_once()  # Ensure it was attempted


@pytest.mark.asyncio
async def test_get_game_found(history_service, mock_db_client, sample_game_history):
    """Test retrieving an existing game."""
    game_id = sample_game_history.game_id
    mock_data_dict = sample_game_history.model_dump()
    with patch.object(BaseService, 'get_document', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_data_dict
        game = await history_service.get_game(game_id)

    assert game is not None
    assert isinstance(game, GameHistory)
    assert game.game_id == game_id
    assert game.white_player_id == sample_game_history.white_player_id
    mock_get.assert_called_once_with(history_service.collection, game_id)


@pytest.mark.asyncio
async def test_get_game_not_found(history_service, mock_db_client):
    """Test retrieving a non-existent game."""
    game_id = "non_existent_game"
    with patch.object(BaseService, 'get_document', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        game = await history_service.get_game(game_id)

    assert game is None
    mock_get.assert_called_once_with(history_service.collection, game_id)


@pytest.mark.asyncio
async def test_get_user_games(history_service, sample_game_history, test_user_1_uid):
    user_id = test_user_1_uid
    limit = 20
    sample_game_history.white_player_id = user_id
    mock_return_data = [sample_game_history.model_dump(mode='json')]  # Use mode='json'

    # Mock BaseService.query_collection
    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query_coll:
        # FIX: Simulate results for *two* calls
        mock_query_coll.side_effect = [
            mock_return_data,  # Games where user is white
            []  # Games where user is black
        ]
        results = await history_service.get_user_games(user_id, limit)

    assert len(results) == 1
    assert isinstance(results[0], GameHistory)
    assert results[0].game_id == sample_game_history.game_id
    assert user_id == results[0].white_player_id  # In this specific mock setup

    # FIX: Verify the calls to the mocked BaseService.query_collection
    assert mock_query_coll.call_count == 2
    # Check first call (user as white)
    call1_args, call1_kwargs = mock_query_coll.call_args_list[0]
    assert call1_args[0] == history_service.collection  # Positional collection arg
    assert call1_kwargs['filters'] == [('white_player_id', '==', user_id)]
    assert call1_kwargs['order_by'] == ('end_time', 'DESCENDING')
    assert call1_kwargs['limit'] == limit
    # Check second call (user as black)
    call2_args, call2_kwargs = mock_query_coll.call_args_list[1]
    assert call2_args[0] == history_service.collection  # Positional collection arg
    assert call2_kwargs['filters'] == [('black_player_id', '==', user_id)]
    assert call2_kwargs['order_by'] == ('end_time', 'DESCENDING')
    assert call2_kwargs['limit'] == limit


@pytest.mark.asyncio
async def test_get_games_between_players(history_service, sample_game_history, test_user_1_uid, test_user_2_uid):
    player1_id = test_user_1_uid
    player2_id = test_user_2_uid
    limit = 5
    sample_game_history.white_player_id = player1_id
    sample_game_history.black_player_id = player2_id
    mock_return_data = [sample_game_history.model_dump(mode='json')]  # Use mode='json'

    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query_coll:
        mock_query_coll.side_effect = [mock_return_data, []]
        results = await history_service.get_games_between_players(player1_id, player2_id, limit)

    assert len(results) == 1
    assert isinstance(results[0], GameHistory)
    assert results[0].game_id == sample_game_history.game_id
    assert (results[0].white_player_id == player1_id and results[0].black_player_id == player2_id)

    # Verify query_collection was called twice with appropriate filters
    assert mock_query_coll.call_count == 2
    # FIX: Check positional args and kwargs for filters, limit, order_by
    # Call 1
    call1_args, call1_kwargs = mock_query_coll.call_args_list[0]
    expected_filters1 = [('white_player_id', '==', player1_id), ('black_player_id', '==', player2_id)]
    assert call1_args[0] == history_service.collection
    assert call1_kwargs['filters'] == expected_filters1
    assert call1_kwargs['limit'] == limit
    assert call1_kwargs['order_by'] == ('end_time', 'DESCENDING')
    # Call 2
    call2_args, call2_kwargs = mock_query_coll.call_args_list[1]
    expected_filters2 = [('white_player_id', '==', player2_id), ('black_player_id', '==', player1_id)]
    assert call2_args[0] == history_service.collection
    assert call2_kwargs['filters'] == expected_filters2
    assert call2_kwargs['limit'] == limit
    assert call2_kwargs['order_by'] == ('end_time', 'DESCENDING')


@pytest.mark.asyncio
async def test_get_user_stats_calculation(history_service, test_user_1_uid):
    # ... (Arrange game data, using mode='json') ...
    user_id = test_user_1_uid
    days = 30
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    game1_data = GameHistory(
        game_id="g1", white_player_id=user_id, black_player_id="p2", result=GameResult.WHITE_WIN,
        start_time=start_date + timedelta(days=1, minutes=-10), end_time=start_date + timedelta(days=1),
        moves=["e4"] * 20, rating_change={'white': 8, 'black': -8}, white_rating=0, black_rating=0, time_control={}
    ).model_dump(mode='json')  # Use mode='json'
    game2_data = GameHistory(
        game_id="g2", white_player_id="p3", black_player_id=user_id, result=GameResult.BLACK_WIN,
        start_time=start_date + timedelta(days=2, minutes=-15), end_time=start_date + timedelta(days=2),
        moves=["d4"] * 30, rating_change={'white': -7, 'black': 7}, white_rating=0, black_rating=0, time_control={}
    ).model_dump(mode='json')  # Use mode='json'
    game3_data = GameHistory(
        game_id="g3", white_player_id=user_id, black_player_id="p4", result=GameResult.DRAW,
        start_time=start_date + timedelta(days=3, minutes=-5), end_time=start_date + timedelta(days=3),
        moves=["c4"] * 10, rating_change={'white': 0, 'black': 0}, white_rating=0, black_rating=0, time_control={}
    ).model_dump(mode='json')  # Use mode='json'

    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query_coll:
        mock_query_coll.side_effect = [[game1_data, game3_data], [game2_data]]
        stats = await history_service.get_user_stats(user_id, days)

    # ... (Verify stats totals) ...
    assert stats['total_games'] == 3
    assert stats['wins'] == 2
    assert stats['losses'] == 0
    assert stats['draws'] == 1

    # FIX: Parse ISO strings before calculating duration
    dur1 = (datetime.fromisoformat(game1_data['end_time']) - datetime.fromisoformat(
        game1_data['start_time'])).total_seconds()
    dur2 = (datetime.fromisoformat(game2_data['end_time']) - datetime.fromisoformat(
        game2_data['start_time'])).total_seconds()
    dur3 = (datetime.fromisoformat(game3_data['end_time']) - datetime.fromisoformat(
        game3_data['start_time'])).total_seconds()
    expected_total_duration = dur1 + dur2 + dur3
    assert stats['average_game_length'] == pytest.approx(expected_total_duration / 3)


@pytest.mark.asyncio
async def test_get_popular_openings(history_service):
    # ... (Arrange game data, using mode='json') ...
    limit = 2
    now = datetime.now(timezone.utc)
    game1_data = GameHistory(game_id="op1", moves=["e4", "e5", "Nf3", "Nc6"], end_time=now, result=GameResult.WHITE_WIN,
                             winner_id="p1", white_player_id="p1", black_player_id="p2",
                             start_time=now - timedelta(minutes=1), white_rating=0, black_rating=0, rating_change={},
                             time_control={}).model_dump(mode='json')
    game2_data = GameHistory(game_id="op2", moves=["d4", "d5", "c4", "e6"], end_time=now, result=GameResult.DRAW,
                             white_player_id="p3", black_player_id="p4", start_time=now - timedelta(minutes=1),
                             white_rating=0, black_rating=0, rating_change={}, time_control={}).model_dump(mode='json')
    game3_data = GameHistory(game_id="op3", moves=["e4", "e5", "Nf3", "Nf6"], end_time=now, result=GameResult.BLACK_WIN,
                             winner_id="p6", white_player_id="p5", black_player_id="p6",
                             start_time=now - timedelta(minutes=1), white_rating=0, black_rating=0, rating_change={},
                             time_control={}).model_dump(mode='json')
    game4_data = GameHistory(game_id="op4", moves=["e4", "e5", "Nf3", "Nc6", "Bb5"], end_time=now,
                             result=GameResult.WHITE_WIN, winner_id="p7", white_player_id="p7", black_player_id="p8",
                             start_time=now - timedelta(minutes=1), white_rating=0, black_rating=0, rating_change={},
                             time_control={}).model_dump(mode='json')
    game5_data = GameHistory(game_id="op5", moves=["e4", "c5"], end_time=now, result=GameResult.ABANDONED,
                             white_player_id="p9", black_player_id="p10", start_time=now - timedelta(minutes=1),
                             white_rating=0, black_rating=0, rating_change={}, time_control={}).model_dump(mode='json')

    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query_coll:
        mock_query_coll.return_value = [game1_data, game2_data, game3_data, game4_data, game5_data]
        openings = await history_service.get_popular_openings(limit)

    assert len(openings) == limit
    opening1 = next((op for op in openings if op['moves'] == "e4 e5 Nf3"), None)
    assert opening1 is not None
    assert opening1['count'] == 3
    # FIX: Check 'wins' based on updated logic (only decisive wins counted)
    assert opening1['wins'] == 3  # g1(W), g3(B), g4(W) - assuming updated logic counts these
    opening2 = next((op for op in openings if op['moves'] == "d4 d5 c4"), None)
    assert opening2 is not None
    assert opening2['count'] == 1
    assert opening2['wins'] == 0  # Draw is not counted as win in updated logic example
    assert openings[0]['count'] >= openings[1]['count']
    assert openings[0]['moves'] == "e4 e5 Nf3"
