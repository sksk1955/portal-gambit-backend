# Filename: tests/unit_whitebox/test_u_analytics_service.py

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from models.game_history import GameResult  # Import enum for results
# Import the class to test and its dependencies/models
from services.analytics_service import AnalyticsService


# Fixtures `mock_db_client`, `test_user_1_uid`, `test_user_2_uid` from conftest.py

@pytest.fixture
def analytics_service(mock_db_client):
    """Creates an instance of the AnalyticsService with the mocked DB client."""
    return AnalyticsService(mock_db_client)


# --- Test Cases ---

@pytest.mark.asyncio
async def test_record_game_analytics_success(analytics_service, mock_db_client):
    """Test successfully recording analytics for a completed game."""
    start = datetime.now(timezone.utc) - timedelta(minutes=15)
    end = datetime.now(timezone.utc)
    duration_secs = (end - start).total_seconds()
    game_data = {
        'game_id': 'ana_game_1',
        'white_player_id': 'p_white',
        'black_player_id': 'p_black',
        'start_time': start,
        'end_time': end,
        'result': GameResult.DRAW,
        'moves': ['e4', 'e5'] * 15,  # 30 moves
        'rating_change': {'white': 1, 'black': -1},
        'game_type': 'portal_gambit',
        'time_control': {'initial': 600, 'increment': 5}
    }

    # Mock the underlying set_document call
    mock_set = AsyncMock(return_value=True)
    # Patch BaseService.set_document used by the service instance
    with patch.object(AnalyticsService, 'set_document', mock_set):
        result = await analytics_service.record_game_analytics(game_data)

    assert result is True
    # Verify the call to set_document
    mock_set.assert_called_once()
    call_args = mock_set.call_args[0]
    assert call_args[0] == 'analytics'  # collection name
    assert call_args[1] == 'game_ana_game_1'  # doc id format
    saved_data = call_args[2]  # The data dict saved
    assert saved_data['game_id'] == game_data['game_id']
    assert saved_data['duration'] == duration_secs
    assert saved_data['total_moves'] == 30
    assert saved_data['result'] == GameResult.DRAW
    assert saved_data['white_player_id'] == game_data['white_player_id']
    assert saved_data['rating_change'] == game_data['rating_change']
    assert saved_data['game_type'] == game_data['game_type']
    assert saved_data['time_control'] == game_data['time_control']
    assert 'timestamp' in saved_data  # Should be added by the service


@pytest.mark.asyncio
async def test_record_game_analytics_failure(analytics_service):
    """Test analytics recording when the database operation fails."""
    now = datetime.now(timezone.utc)
    game_data = {  # Add required fields accessed before set_document
        'game_id': 'fail_game',
        'start_time': now,
        'end_time': now,
        'moves': [],
        'result': 'draw',  # Add dummy
        'white_player_id': 'pW',  # Add dummy
        'black_player_id': 'pB',  # Add dummy
        'rating_change': {},  # Add dummy
        'game_type': 'test',  # Add dummy
        'time_control': {},  # Add dummy
    }
    with patch.object(AnalyticsService, 'set_document', AsyncMock(return_value=False)) as mock_set:
        result = await analytics_service.record_game_analytics(game_data)
    assert result is False
    mock_set.assert_called_once()


# --- Daily Stats Tests ---

@pytest.mark.asyncio
async def test_get_daily_stats_cache_hit(analytics_service):
    """Test hitting the cache for daily stats."""
    test_date = datetime(2024, 3, 10)
    cache_key = f"daily_stats_{test_date.strftime('%Y-%m-%d')}"
    cached_data = {'total_games': 5, 'mock': 'data'}

    with patch.object(AnalyticsService, 'get_document', AsyncMock(return_value=cached_data)) as mock_get, \
            patch.object(AnalyticsService, 'query_collection', new_callable=AsyncMock) as mock_query:
        stats = await analytics_service.get_daily_stats(test_date)

    assert stats == cached_data
    mock_get.assert_called_once_with('analytics_cache', cache_key)
    mock_query.assert_not_called()  # Should not query DB if cache hits


@pytest.mark.asyncio
async def test_get_daily_stats_cache_miss_no_data(analytics_service):
    """Test cache miss and no games found in the database."""
    test_date = datetime(2024, 3, 11)
    cache_key = f"daily_stats_{test_date.strftime('%Y-%m-%d')}"

    with patch.object(AnalyticsService, 'get_document', AsyncMock(return_value=None)) as mock_get, \
            patch.object(AnalyticsService, 'query_collection', AsyncMock(return_value=[])) as mock_query, \
            patch.object(AnalyticsService, 'set_document', AsyncMock(return_value=True)) as mock_set:
        stats = await analytics_service.get_daily_stats(test_date)

    mock_get.assert_called_once_with('analytics_cache', cache_key)
    mock_query.assert_called_once()  # DB query should happen
    assert stats['total_games'] == 0
    assert stats['white_wins'] == 0
    assert stats['average_duration'] == 0
    mock_set.assert_called_once_with('analytics_cache', cache_key, stats)  # Should cache empty stats


@pytest.mark.asyncio
async def test_get_daily_stats_calculation(analytics_service):
    """Test correct calculation of daily stats from fetched game data."""
    test_date = datetime(2024, 3, 12)
    cache_key = f"daily_stats_{test_date.strftime('%Y-%m-%d')}"
    start_time = datetime.combine(test_date, datetime.min.time())
    end_time = start_time + timedelta(days=1)

    # Mock game data returned by query
    mock_games = [
        {'duration': 300, 'total_moves': 40, 'result': GameResult.WHITE_WIN, 'game_type': 'standard',
         'time_control': {'initial': 300, 'increment': 0}},
        {'duration': 600, 'total_moves': 60, 'result': GameResult.BLACK_WIN, 'game_type': 'portal_gambit',
         'time_control': {'initial': 600, 'increment': 5}},
        {'duration': 450, 'total_moves': 50, 'result': GameResult.DRAW, 'game_type': 'portal_gambit',
         'time_control': {'initial': 600, 'increment': 5}},
        {'duration': 150, 'total_moves': 10, 'result': GameResult.ABANDONED, 'game_type': 'standard',
         'time_control': {'initial': 180, 'increment': 0}},
    ]

    with patch.object(AnalyticsService, 'get_document', AsyncMock(return_value=None)) as mock_get, \
            patch.object(AnalyticsService, 'query_collection', AsyncMock(return_value=mock_games)) as mock_query, \
            patch.object(AnalyticsService, 'set_document', AsyncMock(return_value=True)) as mock_set:
        stats = await analytics_service.get_daily_stats(test_date)

    assert stats['total_games'] == 4
    assert stats['white_wins'] == 1
    assert stats['black_wins'] == 1
    assert stats['draws'] == 1
    assert stats['abandoned'] == 1
    assert stats['average_duration'] == pytest.approx((300 + 600 + 450 + 150) / 4)
    assert stats['average_moves'] == pytest.approx((40 + 60 + 50 + 10) / 4)
    assert stats['game_types'] == {'standard': 2, 'portal_gambit': 2}
    # Time control key format depends on the service implementation
    expected_tc_key1 = f"{mock_games[0]['time_control']['initial']}/{mock_games[0]['time_control']['increment']}"
    expected_tc_key2 = f"{mock_games[1]['time_control']['initial']}/{mock_games[1]['time_control']['increment']}"
    expected_tc_key3 = f"{mock_games[3]['time_control']['initial']}/{mock_games[3]['time_control']['increment']}"
    assert stats['time_controls'] == {expected_tc_key1: 1, expected_tc_key2: 2, expected_tc_key3: 1}
    mock_set.assert_called_once_with('analytics_cache', cache_key, stats)  # Verify caching


# --- Player Performance Tests ---

@pytest.mark.asyncio
async def test_get_player_performance_no_games(analytics_service, test_user_1_uid):
    """Test player performance when the player has no games in the period."""
    user_id = test_user_1_uid
    days = 30
    with patch.object(AnalyticsService, 'query_collection', AsyncMock(return_value=[])) as mock_query:
        perf = await analytics_service.get_player_performance(user_id, days)

    assert mock_query.call_count == 2  # Called for white and black games
    assert perf['rating_progression'] == []
    assert perf['win_rate'] == 0
    assert perf['average_game_duration'] == 0


@pytest.mark.asyncio
async def test_get_player_performance_calculation(analytics_service, test_user_1_uid):
    """Test correct calculation of player performance stats."""
    user_id = test_user_1_uid
    days = 30
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Mock games involving the user
    game1 = {'timestamp': start_date + timedelta(days=1), 'white_player_id': user_id, 'black_player_id': 'p2',
             'result': GameResult.WHITE_WIN, 'rating_change': {'white': 8, 'black': -8}, 'duration': 400,
             'total_moves': 50, 'game_type': 'portal_gambit', 'time_control': {'initial': 600, 'increment': 5}}
    game2 = {'timestamp': start_date + timedelta(days=2), 'white_player_id': 'p3', 'black_player_id': user_id,
             'result': GameResult.BLACK_WIN, 'rating_change': {'white': -7, 'black': 7}, 'duration': 500,
             'total_moves': 60, 'game_type': 'portal_gambit', 'time_control': {'initial': 600, 'increment': 5}}
    game3 = {'timestamp': start_date + timedelta(days=3), 'white_player_id': user_id, 'black_player_id': 'p4',
             'result': GameResult.DRAW, 'rating_change': {'white': 0, 'black': 0}, 'duration': 300, 'total_moves': 40,
             'game_type': 'standard', 'time_control': {'initial': 300, 'increment': 0}}

    with patch.object(AnalyticsService, 'query_collection', new_callable=AsyncMock) as mock_query:
        # Simulate query results: user as white -> g1, g3; user as black -> g2
        mock_query.side_effect = [
            [game1, game3],  # Games where user_id is white
            [game2]  # Games where user_id is black
        ]
        perf = await analytics_service.get_player_performance(user_id, days)

    assert mock_query.call_count == 2
    assert len(perf['rating_progression']) == 3
    # Index 0: Game 1 (Correct)
    assert perf['rating_progression'][0] == {'timestamp': game1['timestamp'], 'rating_change': 8}
    assert perf['rating_progression'][1] == {'timestamp': game2['timestamp'], 'rating_change': 7} # Game 2 comes second
    assert perf['rating_progression'][2] == {'timestamp': game3['timestamp'], 'rating_change': 0}
    assert perf['average_game_duration'] == pytest.approx((400 + 500 + 300) / 3)
    assert perf['average_moves_per_game'] == pytest.approx((50 + 60 + 40) / 3)
    # Preferred TC/GT based on counts
    assert perf['preferred_time_control'] == '600/5'  # Appeared twice
    assert perf['preferred_game_type'] == 'portal_gambit'  # Appeared twice
    # Wins: g1 (as white), g2 (as black) -> 2 wins out of 3 games
    assert perf['win_rate'] == pytest.approx(2 / 3)
    # Performance by color
    assert perf['performance_by_color']['white']['games'] == 2
    assert perf['performance_by_color']['white']['wins'] == 1  # Only g1
    assert perf['performance_by_color']['black']['games'] == 1
    assert perf['performance_by_color']['black']['wins'] == 1  # Only g2


# --- Global Stats Tests ---

@pytest.mark.asyncio
async def test_get_global_stats_cache_hit_recent(analytics_service):
    """Test global stats cache hit when data is recent."""
    cache_key = 'global_stats'
    # Simulate cached data less than 1 hour old
    cached_data = {'total_games': 100, 'last_updated': datetime.now(timezone.utc) - timedelta(minutes=30)}

    with patch.object(AnalyticsService, 'get_document', AsyncMock(return_value=cached_data)) as mock_get, \
            patch.object(AnalyticsService, 'query_collection', new_callable=AsyncMock) as mock_query:
        stats = await analytics_service.get_global_stats()

    assert stats == cached_data
    mock_get.assert_called_once_with('analytics_cache', cache_key)
    mock_query.assert_not_called()


@pytest.mark.asyncio
async def test_get_global_stats_cache_hit_stale(analytics_service):
    """Test global stats cache hit when data is stale (needs recalculation)."""
    cache_key = 'global_stats'
    stale_cached_data = {'total_games': 50,
                         'last_updated': datetime.now(timezone.utc) - timedelta(hours=2)}  # Over 1 hour old
    # Mock new data from DB query
    mock_games_for_recalc = [
        {'duration': 300, 'total_moves': 40, 'result': GameResult.WHITE_WIN, 'game_type': 'standard',
         'time_control': {'initial': 300, 'increment': 0}},
        {'duration': 600, 'total_moves': 60, 'result': GameResult.BLACK_WIN, 'game_type': 'portal_gambit',
         'time_control': {'initial': 600, 'increment': 5}},
    ]

    with patch.object(AnalyticsService, 'get_document', AsyncMock(return_value=stale_cached_data)) as mock_get, \
            patch.object(AnalyticsService, 'query_collection',
                         AsyncMock(return_value=mock_games_for_recalc)) as mock_query, \
            patch.object(AnalyticsService, 'set_document', AsyncMock(return_value=True)) as mock_set:
        stats = await analytics_service.get_global_stats()

    mock_get.assert_called_once_with('analytics_cache', cache_key)
    mock_query.assert_called_once()  # Query should run due to stale cache
    assert stats['total_games'] == 2  # Recalculated total
    assert stats['white_win_rate'] == 0.5  # 1 white win out of 2 games
    assert stats['average_game_duration'] == pytest.approx((300 + 600) / 2)
    assert 'last_updated' in stats
    assert stats['last_updated'] > stale_cached_data['last_updated']  # Should be newer
    mock_set.assert_called_once()  # Should save recalculated stats to cache
    assert mock_set.call_args[0][0] == 'analytics_cache'
    assert mock_set.call_args[0][1] == cache_key


@pytest.mark.asyncio
async def test_get_global_stats_cache_miss(analytics_service):
    """Test global stats cache miss (needs calculation)."""
    cache_key = 'global_stats'
    # Similar to stale test, but get_document returns None
    mock_games_for_calc = [
        {'duration': 400, 'total_moves': 50, 'result': GameResult.WHITE_WIN, 'game_type': 'portal_gambit',
         'time_control': {'initial': 600, 'increment': 5}},
    ]
    with patch.object(AnalyticsService, 'get_document', AsyncMock(return_value=None)) as mock_get, \
            patch.object(AnalyticsService, 'query_collection',
                         AsyncMock(return_value=mock_games_for_calc)) as mock_query, \
            patch.object(AnalyticsService, 'set_document', AsyncMock(return_value=True)) as mock_set:
        stats = await analytics_service.get_global_stats()

    mock_get.assert_called_once_with('analytics_cache', cache_key)
    mock_query.assert_called_once()
    assert stats['total_games'] == 1
    assert stats['white_win_rate'] == 1.0
    mock_set.assert_called_once_with('analytics_cache', cache_key, stats)
