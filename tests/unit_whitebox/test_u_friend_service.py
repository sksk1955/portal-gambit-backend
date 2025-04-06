import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch  # Import ANY

import pytest
# Import necessary Firestore types
from google.cloud.firestore_v1.async_query import AsyncQuery  # Import AsyncQuery
from google.cloud.firestore_v1.async_transaction import AsyncTransaction  # Import AsyncTransaction

# Import models and service
from models.friend import FriendRequest, FriendRequestStatus
# Import BaseService to patch its methods
from services.base_service import BaseService
from services.friend_service import FriendService


@pytest.fixture
def friend_service(mock_db_client):  # Use mock_db_client fixture
    """Creates an instance of the FriendService with the mocked DB client."""
    # FriendService __init__ takes db: AsyncClient
    return FriendService(mock_db_client)


@pytest.mark.asyncio
async def test_send_friend_request_success(friend_service, mock_db_client, test_user_1_uid, test_user_2_uid):
    # ... (Arrange sender_id, etc.) ...
    sender_id, receiver_id, message = test_user_1_uid, test_user_2_uid, "Hi!"
    test_uuid_obj = uuid.uuid4()
    request_id = f"req_{test_uuid_obj.hex}"

    # Mock BaseService.get_document
    mock_get_friendship = AsyncMock(return_value=None)

    # FIX: Correctly mock the query chain for checking existing requests
    mock_query_get_method = AsyncMock(return_value=[])  # This is what `await query.get()` returns
    mock_query_chain = MagicMock(spec=AsyncQuery)
    # Mock methods called on the query object, ensure they return the mock itself for chaining
    mock_query_chain.where.return_value = mock_query_chain
    mock_query_chain.limit.return_value = mock_query_chain
    # Assign the awaitable get method to the final link in the chain
    mock_query_chain.get = mock_query_get_method

    # Ensure the db client returns the start of the mock chain
    # db.collection(...).where(...).where(...).where(...).limit(...) -> mock_query_chain
    mock_db_client.collection.return_value.where.return_value.where.return_value.where.return_value = mock_query_chain

    # Mock BaseService.set_document
    mock_set_request = AsyncMock(return_value=True)

    with patch.object(BaseService, 'get_document', mock_get_friendship), \
            patch.object(BaseService, 'set_document', mock_set_request), \
            patch('services.friend_service.uuid.uuid4', return_value=test_uuid_obj):

        result = await friend_service.send_friend_request(sender_id, receiver_id, message)

    assert result is True
    mock_get_friendship.assert_called_once_with(friend_service.friends_collection, f"{sender_id}_{receiver_id}")
    # Assert the final .get() was awaited twice
    assert mock_query_get_method.await_count == 2
    mock_set_request.assert_called_once()
    # Check args passed to set_document
    call_args_set = mock_set_request.call_args[0]
    assert call_args_set[0] == friend_service.requests_collection
    assert call_args_set[1] == request_id  # Check ID format
    saved_data = call_args_set[2]
    assert saved_data['sender_id'] == sender_id
    assert saved_data['receiver_id'] == receiver_id
    assert saved_data['message'] == message
    assert saved_data['status'] == FriendRequestStatus.PENDING.value  # Check serialized enum
    assert 'created_at' in saved_data
    assert 'updated_at' in saved_data


@pytest.mark.asyncio
async def test_send_friend_request_failure(friend_service, mock_db_client, test_user_1_uid, test_user_2_uid):
    sender_id, receiver_id = test_user_1_uid, test_user_2_uid

    # Mock BaseService.get_document
    mock_get_friendship = AsyncMock(return_value=None)

    # FIX: Correctly mock the query chain
    mock_query_get_method = AsyncMock(return_value=[])
    mock_query_chain = MagicMock(spec=AsyncQuery)
    mock_query_chain.where.return_value = mock_query_chain
    mock_query_chain.limit.return_value = mock_query_chain
    mock_query_chain.get = mock_query_get_method
    mock_db_client.collection.return_value.where.return_value.where.return_value.where.return_value = mock_query_chain

    # Mock BaseService.set_document to fail
    mock_set_request = AsyncMock(return_value=False)

    with patch.object(BaseService, 'get_document', mock_get_friendship), \
            patch.object(BaseService, 'set_document', mock_set_request), \
            patch('services.friend_service.uuid.uuid4'):

        result = await friend_service.send_friend_request(sender_id, receiver_id)

    assert result is False
    # Assert the final .get() was awaited twice (check happens before set attempt)
    assert mock_query_get_method.await_count == 2
    mock_set_request.assert_called_once()  # Ensure it was attempted


# --- Tests for get_friend_request ---
# ... (get_friend_request tests remain the same) ...
@pytest.mark.asyncio
async def test_get_friend_request_found(friend_service, sample_friend_request):
    request_id = sample_friend_request.request_id
    # Use mode='json' to simulate Firestore data serialization (enums to values)
    mock_data = sample_friend_request.model_dump(mode='json')
    with patch.object(BaseService, 'get_document', AsyncMock(return_value=mock_data)) as mock_get:
        request = await friend_service.get_friend_request(request_id)

    assert request is not None
    assert isinstance(request, FriendRequest)
    assert request.request_id == request_id
    assert request.sender_id == sample_friend_request.sender_id
    mock_get.assert_called_once_with(friend_service.requests_collection, request_id)


@pytest.mark.asyncio
async def test_get_friend_request_not_found(friend_service):
    request_id = "non_existent_req"
    with patch.object(BaseService, 'get_document', AsyncMock(return_value=None)) as mock_get:
        request = await friend_service.get_friend_request(request_id)

    assert request is None
    mock_get.assert_called_once_with(friend_service.requests_collection, request_id)


# --- Tests for get_pending_requests ---
# ... (get_pending_requests tests remain the same) ...
@pytest.mark.asyncio
async def test_get_pending_requests(friend_service, mock_db_client, sample_friend_request, test_user_1_uid):
    # ... (Arrange user_id, mock_return_data_dict) ...
    user_id = test_user_1_uid
    sample_friend_request.receiver_id = user_id
    sample_friend_request.status = FriendRequestStatus.PENDING
    mock_return_data_dict = sample_friend_request.model_dump(mode='json')

    # Mock the final query result snapshot
    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = mock_return_data_dict
    # Mock the awaitable .get() method
    mock_query_get_method = AsyncMock(return_value=[mock_snapshot])

    # Mock the query chain, including the two where calls
    mock_query_chain = MagicMock(spec=AsyncQuery)
    # FIX: Make the first .where() return the chain so the second .where() can be called
    mock_query_chain.where.return_value = mock_query_chain
    # Assign the awaitable get method to the end of the chain
    mock_query_chain.get = mock_query_get_method

    # Mock the db client call chain to return the start of the mock chain
    # db.collection(...).where(...).where(...) -> mock_query_chain
    mock_db_client.collection.return_value.where.return_value = mock_query_chain

    # Act
    results = await friend_service.get_pending_requests(user_id)

    # Assert results
    assert len(results) == 1
    assert results[0].receiver_id == user_id

    # Verify query chain calls
    mock_db_client.collection.assert_called_with(friend_service.requests_collection)
    # Get the mock object representing the collection reference
    collection_mock = mock_db_client.collection.return_value
    # Assert the first where call on the collection mock
    first_where_call = collection_mock.where.call_args_list[0]
    filter1_args = first_where_call[1]['filter']
    assert filter1_args.field_path == 'receiver_id'  # Use public attribute
    assert filter1_args.op_string == '=='
    assert filter1_args.value == user_id

    # Assert the second where call on the result of the first where (which is mock_query_chain)
    second_where_call = mock_query_chain.where.call_args_list[0]  # Called once on mock_query_chain
    filter2_args = second_where_call[1]['filter']
    assert filter2_args.field_path == 'status'  # Use public attribute
    assert filter2_args.op_string == '=='
    assert filter2_args.value == FriendRequestStatus.PENDING.value

    # Check get was awaited
    mock_query_get_method.assert_awaited_once()


# --- Tests for respond_to_request ---
# ... (respond_to_request tests remain the same) ...
@pytest.mark.asyncio
async def test_respond_to_request_accept(friend_service, sample_friend_request):
    request_id = sample_friend_request.request_id
    sender_id = sample_friend_request.sender_id
    receiver_id = sample_friend_request.receiver_id
    status_key1 = f"{sender_id}_{receiver_id}"
    status_key2 = f"{receiver_id}_{sender_id}"
    # Use mode='json' to simulate Firestore data
    mock_request_data = sample_friend_request.model_dump(mode='json')

    # Mock BaseService methods used by respond_to_request
    with patch.object(BaseService, 'get_document', AsyncMock(return_value=mock_request_data)) as mock_get_req, \
            patch.object(BaseService, 'update_document', AsyncMock(return_value=True)) as mock_update_req, \
            patch.object(BaseService, 'set_document', AsyncMock(return_value=True)) as mock_set_status:
        result = await friend_service.respond_to_request(request_id, accept=True)

    assert result is True
    # Verify get_document was called for the request
    mock_get_req.assert_called_once_with(friend_service.requests_collection, request_id)
    # Verify update_document call for the request status
    mock_update_req.assert_called_once()
    update_call_args = mock_update_req.call_args[0]  # Positional args
    assert update_call_args[0] == friend_service.requests_collection
    assert update_call_args[1] == request_id
    assert update_call_args[2]['status'] == FriendRequestStatus.ACCEPTED.value  # Check enum value
    assert 'updated_at' in update_call_args[2]
    # Verify set_document calls for friend status
    assert mock_set_status.call_count == 2
    set_calls = mock_set_status.call_args_list
    # Check that both keys were used for setting friend status
    keys_called = {call[0][1] for call in set_calls}  # Get the doc_id from each call
    assert keys_called == {status_key1, status_key2}
    # Optionally check the data structure passed to set_document
    assert set_calls[0][0][2]['user_id'] in [sender_id, receiver_id]
    assert set_calls[0][0][2]['friend_id'] in [sender_id, receiver_id]


@pytest.mark.asyncio
async def test_respond_to_request_reject(friend_service, sample_friend_request):
    request_id = sample_friend_request.request_id
    mock_request_data = sample_friend_request.model_dump(mode='json')

    with patch.object(BaseService, 'get_document', AsyncMock(return_value=mock_request_data)) as mock_get_req, \
            patch.object(BaseService, 'update_document', AsyncMock(return_value=True)) as mock_update_req, \
            patch.object(BaseService, 'set_document', AsyncMock()) as mock_set_status:  # Mock set just in case

        result = await friend_service.respond_to_request(request_id, accept=False)

    assert result is True
    mock_get_req.assert_called_once_with(friend_service.requests_collection, request_id)
    # Verify request status update to REJECTED
    mock_update_req.assert_called_once()
    update_args = mock_update_req.call_args[0][2]  # Data dict
    assert update_args['status'] == FriendRequestStatus.REJECTED.value
    # Verify friend status was NOT created
    mock_set_status.assert_not_called()


@pytest.mark.asyncio
async def test_respond_to_request_not_found(friend_service):
    """Test responding to a request that doesn't exist."""
    request_id = "fake_req"
    with patch.object(BaseService, 'get_document', AsyncMock(return_value=None)):
        result = await friend_service.respond_to_request(request_id, accept=True)
    assert result is False


@pytest.mark.asyncio
async def test_respond_to_request_parsing_error(friend_service, sample_friend_request):
    """Test responding when the fetched data is invalid."""
    request_id = sample_friend_request.request_id
    invalid_data = {"wrong_field": "some_value"}  # Missing required fields
    with patch.object(BaseService, 'get_document', AsyncMock(return_value=invalid_data)):
        result = await friend_service.respond_to_request(request_id, accept=True)
    assert result is False  # Service should handle parsing error and return False


# --- Tests for get_friends ---
# ... (get_friends tests remain the same) ...
@pytest.mark.asyncio
async def test_get_friends(friend_service, mock_db_client, sample_friend_status, test_user_1_uid):
    # ... (Arrange user_id, mock_return_data_dict) ...
    user_id = test_user_1_uid
    sample_friend_status.user_id = user_id
    mock_return_data_dict = sample_friend_status.model_dump(mode='json')

    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = mock_return_data_dict
    mock_query_get_method = AsyncMock(return_value=[mock_snapshot])

    # Mock the query chain
    mock_query_chain = MagicMock(spec=AsyncQuery)
    mock_query_chain.get = mock_query_get_method
    mock_db_client.collection.return_value.where.return_value = mock_query_chain

    # Act
    friends = await friend_service.get_friends(user_id)

    # Assert results
    assert len(friends) == 1
    assert friends[0].user_id == user_id

    # Verify query
    mock_db_client.collection.assert_called_with(friend_service.friends_collection)
    where_call = mock_db_client.collection.return_value.where.call_args
    filter_args = where_call[1]['filter']
    # FIX: Use public attribute field_path
    assert filter_args.field_path == 'user_id'
    assert filter_args.op_string == '=='
    assert filter_args.value == user_id
    mock_query_get_method.assert_awaited_once()


# --- Tests for remove_friend ---
@pytest.mark.asyncio
async def test_remove_friend_success(friend_service, mock_db_client, test_user_1_uid, test_user_2_uid):
    user_id, friend_id = test_user_1_uid, test_user_2_uid
    status_key1 = f"{user_id}_{friend_id}"
    status_key2 = f"{friend_id}_{user_id}"

    # Mock document references needed before transaction starts
    mock_doc_ref1 = MagicMock()
    mock_doc_ref2 = MagicMock()

    def doc_side_effect(key):
        if key == status_key1: return mock_doc_ref1
        if key == status_key2: return mock_doc_ref2
        return MagicMock()

    mock_db_client.collection.return_value.document.side_effect = doc_side_effect

    # --- FIX: Mock db.transaction() AND the delete method ---
    # 1. Mock the transaction object that will be passed to the inner function
    mock_transaction_obj = AsyncMock(spec=AsyncTransaction)

    # 2. Mock db.transaction() to return a simple context manager that yields the mock transaction object
    #    This avoids errors like '_read_only' attribute missing.
    @pytest.mark.asyncio
    async def mock_transaction_context_manager(*args, **kwargs):
        yield mock_transaction_obj  # Yield the mock transaction

    mock_db_client.transaction.return_value = AsyncMock()  # Mock the initial call
    mock_db_client.transaction.return_value.__aenter__.return_value = mock_transaction_obj  # Make context yield mock
    mock_db_client.transaction.return_value.__aexit__ = AsyncMock(return_value=None)  # Mock exit

    # Act: Call the service method. The @async_transactional decorator will use the mocked transaction.
    result = await friend_service.remove_friend(user_id, friend_id)

    # Assert
    assert result is True
    # Verify the transaction was initiated
    mock_db_client.transaction.assert_called_once()
    # Verify delete was called on the mock transaction object for both refs
    assert mock_transaction_obj.delete.call_count == 2
    mock_transaction_obj.delete.assert_any_call(mock_doc_ref1)
    mock_transaction_obj.delete.assert_any_call(mock_doc_ref2)


@pytest.mark.asyncio
async def test_remove_friend_failure(friend_service, mock_db_client, test_user_1_uid, test_user_2_uid):
    user_id, friend_id = test_user_1_uid, test_user_2_uid
    status_key1 = f"{user_id}_{friend_id}"
    status_key2 = f"{friend_id}_{user_id}"

    # Mock document references
    mock_doc_ref1 = MagicMock()
    mock_doc_ref2 = MagicMock()

    def doc_side_effect(key):
        if key == status_key1: return mock_doc_ref1
        if key == status_key2: return mock_doc_ref2
        return MagicMock()

    mock_db_client.collection.return_value.document.side_effect = doc_side_effect

    # --- FIX: Mock db.transaction() AND make delete raise error ---
    mock_transaction_obj = AsyncMock(spec=AsyncTransaction)
    # Make the delete method raise an exception when called
    mock_transaction_obj.delete.side_effect = Exception("Simulated DB error during delete")

    @pytest.mark.asyncio
    async def mock_transaction_context_manager(*args, **kwargs):
        yield mock_transaction_obj

    mock_db_client.transaction.return_value = AsyncMock()
    mock_db_client.transaction.return_value.__aenter__.return_value = mock_transaction_obj
    mock_db_client.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    # Act
    result = await friend_service.remove_friend(user_id, friend_id)

    # Assert
    assert result is False
    # Verify the transaction was initiated
    mock_db_client.transaction.assert_called_once()
    # Verify delete was attempted
    mock_transaction_obj.delete.assert_called()  # Should be called at least once before raising


# --- Tests for update_last_interaction ---
# ... (update_last_interaction tests remain the same) ...
@pytest.mark.asyncio
async def test_update_last_interaction(friend_service, test_user_1_uid, test_user_2_uid):
    user_id, friend_id, game_id = test_user_1_uid, test_user_2_uid, "game1"
    status_key = f"{user_id}_{friend_id}"

    # Patch the BaseService method
    with patch.object(BaseService, 'update_document', AsyncMock(return_value=True)) as mock_update, \
            patch('services.friend_service.Increment') as MockIncrement:  # Mock Increment used inside the method
        MockIncrement.return_value = "INCREMENT_OBJECT"  # Return a placeholder
        result = await friend_service.update_last_interaction(user_id, friend_id, game_id)

    assert result is True
    mock_update.assert_called_once()
    # Check arguments passed to update_document
    call_args = mock_update.call_args[0]
    assert call_args[0] == friend_service.friends_collection
    assert call_args[1] == status_key
    update_data = call_args[2]
    assert 'last_interaction' in update_data
    assert isinstance(update_data['last_interaction'], datetime)
    assert update_data['games_played'] == "INCREMENT_OBJECT"  # Check the placeholder
    assert update_data['last_game'] == game_id


@pytest.mark.asyncio
async def test_update_last_interaction_no_game_id(friend_service, test_user_1_uid, test_user_2_uid):
    user_id, friend_id = test_user_1_uid, test_user_2_uid
    status_key = f"{user_id}_{friend_id}"

    with patch.object(BaseService, 'update_document', AsyncMock(return_value=True)) as mock_update, \
            patch('services.friend_service.Increment') as MockIncrement:
        MockIncrement.return_value = "INCREMENT_OBJECT"
        result = await friend_service.update_last_interaction(user_id, friend_id, game_id=None)

    assert result is True
    mock_update.assert_called_once()
    update_data = mock_update.call_args[0][2]
    assert 'last_interaction' in update_data
    assert update_data['games_played'] == "INCREMENT_OBJECT"
    assert 'last_game' not in update_data
