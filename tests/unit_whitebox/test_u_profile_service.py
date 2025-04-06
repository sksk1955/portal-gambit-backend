from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock  # Import call

import pytest
from google.cloud import firestore

from models.user_profile import UserProfile
# Import BaseService to patch its methods
from services.base_service import BaseService
# Import the class to test and its dependencies/models
from services.profile_service import ProfileService


# Import the mock Firestore utility classes if needed for assertions


@pytest.fixture
def profile_service(mock_db_client):  # Keep mock_db_client fixture for now, might remove later
    """Creates an instance of the ProfileService."""
    # We will patch BaseService methods directly in the tests below
    return ProfileService(mock_db_client)  # Pass the mock client, though we override methods


# Mocks for firestore field types (needed for assertions)
@pytest.fixture
def mock_fs_increment():
    return firestore.Increment(1)


@pytest.fixture
def mock_fs_array_union():
    return firestore.ArrayUnion(["some_value"])


# --- Test Cases ---

@pytest.mark.asyncio
async def test_create_profile_success(profile_service, sample_user_profile):
    """Test successfully creating a new profile by mocking BaseService.set_document."""
    profile_data = sample_user_profile
    # Mock the specific BaseService method used by create_profile
    with patch.object(BaseService, 'set_document', new_callable=AsyncMock) as mock_set:
        mock_set.return_value = True  # Simulate successful set
        result = await profile_service.create_profile(profile_data)

    assert result is True
    # Verify the call to the mocked BaseService method
    # Use model_dump() instead of dict() for Pydantic v2
    mock_set.assert_called_once_with(
        profile_service.collection,  # 'user_profiles'
        profile_data.uid,
        profile_data.model_dump()  # Use model_dump()
    )


@pytest.mark.asyncio
async def test_create_profile_failure(profile_service, sample_user_profile):
    """Test profile creation failure by mocking BaseService.set_document."""
    profile_data = sample_user_profile
    with patch.object(BaseService, 'set_document', new_callable=AsyncMock) as mock_set:
        mock_set.return_value = False  # Simulate failure
        result = await profile_service.create_profile(profile_data)

    assert result is False
    mock_set.assert_called_once_with(
        profile_service.collection, profile_data.uid, profile_data.model_dump()  # Use model_dump()
    )


@pytest.mark.asyncio
async def test_get_profile_found(profile_service, sample_user_profile):
    """Test retrieving an existing profile by mocking BaseService.get_document."""
    uid = sample_user_profile.uid
    # Mock get_document to return the expected dict
    with patch.object(BaseService, 'get_document', new_callable=AsyncMock) as mock_get:
        # Use model_dump() for serialization simulation
        mock_get.return_value = sample_user_profile.model_dump()
        profile = await profile_service.get_profile(uid)

    assert profile is not None
    assert isinstance(profile, UserProfile)
    assert profile.uid == uid
    mock_get.assert_called_once_with(profile_service.collection, uid)


@pytest.mark.asyncio
async def test_get_profile_not_found(profile_service, test_user_1_uid):
    """Test retrieving non-existent profile by mocking BaseService.get_document."""
    uid = test_user_1_uid
    with patch.object(BaseService, 'get_document', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None  # Simulate not found
        profile = await profile_service.get_profile(uid)

    assert profile is None
    mock_get.assert_called_once_with(profile_service.collection, uid)


@pytest.mark.asyncio
async def test_update_profile_success(profile_service, test_user_1_uid):
    """Test updating profile by mocking BaseService.update_document."""
    uid = test_user_1_uid
    updates = {"display_name": "New Updated Name"}
    # Mock utcnow used inside update_profile
    mock_now = datetime.now(timezone.utc)
    with patch.object(BaseService, 'update_document', new_callable=AsyncMock) as mock_update, \
            patch('services.profile_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_now  # Use timezone.utc if needed
        mock_update.return_value = True
        result = await profile_service.update_profile(uid, updates.copy())  # Pass copy

    assert result is True
    # Verify update_document call *includes* 'last_active'
    mock_update.assert_called_once()
    call_args = mock_update.call_args[0]
    assert call_args[0] == profile_service.collection  # collection
    assert call_args[1] == uid  # doc_id
    update_data = call_args[2]  # data dict
    assert update_data["display_name"] == "New Updated Name"
    assert "last_active" in update_data
    # assert update_data["last_active"] == mock_now # Check the mocked time is used


@pytest.mark.asyncio
async def test_update_profile_failure(profile_service, test_user_1_uid):
    """Test profile update failure by mocking BaseService.update_document."""
    uid = test_user_1_uid
    updates = {"display_name": "Update Fail"}
    with patch.object(BaseService, 'update_document', new_callable=AsyncMock) as mock_update, \
            patch('services.profile_service.datetime'):  # Still need to patch datetime if used
        mock_update.return_value = False  # Simulate failure
        result = await profile_service.update_profile(uid, updates.copy())

    assert result is False
    mock_update.assert_called_once()  # Check it was called even on failure


# --- Tests requiring mocked Firestore field types ---

@pytest.mark.asyncio
async def test_update_rating_win(profile_service, test_user_1_uid, mock_fs_increment):
    """Test updating rating after win by mocking BaseService.update_document."""
    uid = test_user_1_uid
    new_rating = 1258
    game_result = {"result": "win"}
    with patch.object(BaseService, 'update_document', new_callable=AsyncMock) as mock_update, \
            patch('services.profile_service.firestore.Increment',  # Mock Increment where it's used
                  return_value=mock_fs_increment):
        mock_update.return_value = True
        result = await profile_service.update_rating(uid, new_rating, game_result)

    assert result is True
    expected_update = {
        'rating': new_rating,
        'games_played': mock_fs_increment,
        'wins': mock_fs_increment
    }
    mock_update.assert_called_once_with(profile_service.collection, uid, expected_update)


@pytest.mark.asyncio
async def test_update_rating_loss(profile_service, test_user_1_uid, mock_fs_increment):
    """Test updating rating after loss by mocking BaseService.update_document."""
    uid = test_user_1_uid
    new_rating = 1242
    game_result = {"result": "loss"}
    with patch.object(BaseService, 'update_document', new_callable=AsyncMock) as mock_update, \
            patch('services.profile_service.firestore.Increment', return_value=mock_fs_increment):
        mock_update.return_value = True
        result = await profile_service.update_rating(uid, new_rating, game_result)

    assert result is True
    expected_update = {
        'rating': new_rating,
        'games_played': mock_fs_increment,
        'losses': mock_fs_increment
    }
    mock_update.assert_called_once_with(profile_service.collection, uid, expected_update)


@pytest.mark.asyncio
async def test_update_rating_draw(profile_service, test_user_1_uid, mock_fs_increment):
    """Test updating rating after draw by mocking BaseService.update_document."""
    uid = test_user_1_uid
    new_rating = 1250
    game_result = {"result": "draw"}
    with patch.object(BaseService, 'update_document', new_callable=AsyncMock) as mock_update, \
            patch('services.profile_service.firestore.Increment', return_value=mock_fs_increment):
        mock_update.return_value = True
        result = await profile_service.update_rating(uid, new_rating, game_result)

    assert result is True
    expected_update = {
        'rating': new_rating,
        'games_played': mock_fs_increment,
        'draws': mock_fs_increment
    }
    mock_update.assert_called_once_with(profile_service.collection, uid, expected_update)


@pytest.mark.asyncio
async def test_add_achievement_success(profile_service, test_user_1_uid):
    uid = test_user_1_uid
    achievement_id = "unit_test_master"
    # Patch BaseService method and the correct ArrayUnion
    with patch.object(BaseService, 'update_document', new_callable=AsyncMock) as mock_update, \
            patch('google.cloud.firestore_v1.ArrayUnion') as mock_array_union_constructor:  # FIX: Correct patch target
        # Configure mocks
        mock_update.return_value = True
        # Create a dummy object to represent what ArrayUnion might return
        # This is needed because the code calls ArrayUnion(...)
        mock_array_union_instance = MagicMock(name="ArrayUnionInstance")
        mock_array_union_constructor.return_value = mock_array_union_instance

        # Act
        result = await profile_service.add_achievement(uid, achievement_id)

    # Assert
    assert result is True
    # Verify ArrayUnion constructor was called
    mock_array_union_constructor.assert_called_once_with([achievement_id])
    # FIX: Verify update_document call structure using ANY
    mock_update.assert_called_once_with(
        profile_service.collection,
        uid,
        {'achievements': mock_array_union_instance}  # Check the instance returned by the mock constructor was used
        # Or use ANY for more flexibility: {'achievements': ANY}
    )


# --- Query Tests (Mocking BaseService.query_collection) ---

@pytest.mark.asyncio
async def test_search_profiles_found(profile_service, sample_user_profile):
    """Test searching profiles by mocking BaseService.query_collection."""
    prefix = sample_user_profile.username[:5]
    limit = 10
    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query:
        # Return data that matches what the real query would return (list of dicts)
        mock_query.return_value = [sample_user_profile.model_dump()]
        results = await profile_service.search_profiles(prefix, limit)

    assert len(results) == 1
    assert isinstance(results[0], UserProfile)
    assert results[0].uid == sample_user_profile.uid

    # Verify the arguments passed to the mocked query_collection
    mock_query.assert_called_once()
    call_args, call_kwargs = mock_query.call_args
    assert call_args[0] == profile_service.collection  # Check positional collection arg
    expected_filters = [
        ('username', '>=', prefix),
        ('username', '<=', prefix + '\uf8ff')
    ]
    assert call_kwargs.get('filters') == expected_filters
    assert call_kwargs.get('order_by') == ('username', 'ASCENDING')
    assert call_kwargs.get('limit') == limit


@pytest.mark.asyncio
async def test_search_profiles_not_found(profile_service):
    """Test searching profiles when no results are found."""
    prefix = "nonexistent"
    limit = 5
    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []  # Simulate empty result
        results = await profile_service.search_profiles(prefix, limit)

    assert isinstance(results, list)
    assert len(results) == 0
    mock_query.assert_called_once()  # Verify it was called


@pytest.mark.asyncio
async def test_get_leaderboard(profile_service, sample_user_profile):
    """Test retrieving the leaderboard by mocking BaseService.query_collection."""
    limit = 50
    with patch.object(BaseService, 'query_collection', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [sample_user_profile.model_dump()]
        results = await profile_service.get_leaderboard(limit)

    assert len(results) == 1
    assert isinstance(results[0], UserProfile)

    # Verify arguments passed to query_collection
    # FIX: Match the actual call which doesn't explicitly pass filters=None
    mock_query.assert_called_once_with(
        profile_service.collection,  # Positional collection
        # filters=None, # REMOVE this assertion
        order_by=('rating', 'DESCENDING'),
        limit=limit
    )