# Filename: tests/integration_whitebox/test_i_friend_routes.py

# Import models/schemas used for request/response validation

# Fixtures: client, mock_friend_service, sample_friend_request, sample_friend_status,
# test_user_1_uid, test_user_2_uid from conftest.py

# --- Test Cases for /friends/requests POST ---

def test_send_friend_request_success(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test successfully sending a friend request."""
    # Arrange: Prepare payload matching FriendRequestCreate schema
    request_payload = {
        "receiver_id": test_user_2_uid,
        "message": "Integration test request!"
    }
    # Mock service success
    mock_friend_service.send_friend_request.return_value = True

    # Act: Make the POST request
    response = client.post("/friends/requests", json=request_payload)

    # Assert: Check response and service call
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Friend request sent successfully"}
    # Verify service called with correct sender (authenticated user) and payload data
    mock_friend_service.send_friend_request.assert_called_once_with(
        sender_id=test_user_1_uid,  # From authenticated user context
        receiver_id=test_user_2_uid,
        message="Integration test request!"
    )


def test_send_friend_request_service_fails(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test sending request when the service layer returns False."""
    # Arrange
    request_payload = {"receiver_id": test_user_2_uid}
    mock_friend_service.send_friend_request.return_value = False  # Simulate service failure

    # Act
    response = client.post("/friends/requests", json=request_payload)

    # Assert: Check response reflects service failure
    assert response.status_code == 409  # Route succeeded
    assert "Failed to send friend request" in response.json().get("detail", "")
    mock_friend_service.send_friend_request.assert_called_once()


def test_send_friend_request_validation_error(client, mock_friend_service):
    """Test sending request with missing required 'receiver_id'."""
    # Arrange: Invalid payload
    request_payload = {"message": "Missing receiver"}

    # Act
    response = client.post("/friends/requests", json=request_payload)

    # Assert: FastAPI validation should return 422
    assert response.status_code == 422
    mock_friend_service.send_friend_request.assert_not_called()


# --- Test Cases for /friends/requests/pending GET ---

def test_get_pending_requests_success(client, mock_friend_service, sample_friend_request, test_user_1_uid):
    """Test getting pending requests when service returns data."""
    # Arrange: Mock service to return a list containing the sample request
    mock_friend_service.get_pending_requests.return_value = [sample_friend_request]

    # Act
    response = client.get("/friends/requests/pending")

    # Assert: Check response matches serialized mock data
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    # Compare key fields (datetime will be serialized)
    assert response_data[0]["request_id"] == sample_friend_request.request_id
    assert response_data[0]["sender_id"] == sample_friend_request.sender_id
    assert response_data[0]["receiver_id"] == sample_friend_request.receiver_id
    assert response_data[0]["status"] == sample_friend_request.status.value  # Enum serialized to value

    # Assert service called with authenticated user's ID
    mock_friend_service.get_pending_requests.assert_called_once_with(test_user_1_uid)


def test_get_pending_requests_empty(client, mock_friend_service, test_user_1_uid):
    """Test getting pending requests when service returns an empty list."""
    # Arrange: Mock service returns empty list
    mock_friend_service.get_pending_requests.return_value = []

    # Act
    response = client.get("/friends/requests/pending")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    mock_friend_service.get_pending_requests.assert_called_once_with(test_user_1_uid)


# --- Test Cases for /friends/requests/{request_id}/respond POST ---

def test_respond_to_request_accept_success(client, mock_friend_service, sample_friend_request, test_user_1_uid):
    """Test accepting a pending friend request successfully."""
    # Arrange
    request_id = sample_friend_request.request_id
    # Ensure the sample request is directed TO the authenticated user
    sample_friend_request.receiver_id = test_user_1_uid
    # Mock service calls
    mock_friend_service.get_friend_request.return_value = sample_friend_request
    mock_friend_service.respond_to_request.return_value = True
    respond_payload = {"accept": True}  # Matches schema (used in route logic, not FriendRequestResponse schema)

    # Act
    response = client.post(f"/friends/requests/{request_id}/respond", json=respond_payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "accepted successfully" in response.json()["message"]
    mock_friend_service.get_friend_request.assert_called_once_with(request_id)
    mock_friend_service.respond_to_request.assert_called_once_with(request_id, True)


def test_respond_to_request_reject_success(client, mock_friend_service, sample_friend_request, test_user_1_uid):
    """Test rejecting a pending friend request successfully."""
    # Arrange
    request_id = sample_friend_request.request_id
    sample_friend_request.receiver_id = test_user_1_uid
    mock_friend_service.get_friend_request.return_value = sample_friend_request
    mock_friend_service.respond_to_request.return_value = True
    respond_payload = {"accept": False}

    # Act
    response = client.post(f"/friends/requests/{request_id}/respond", json=respond_payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "rejected successfully" in response.json()["message"]
    mock_friend_service.get_friend_request.assert_called_once_with(request_id)
    mock_friend_service.respond_to_request.assert_called_once_with(request_id, False)


def test_respond_to_request_not_found(client, mock_friend_service):
    """Test responding when the request_id doesn't exist."""
    # Arrange
    request_id = "non-existent-req"
    mock_friend_service.get_friend_request.return_value = None  # Simulate not found
    respond_payload = {"accept": True}

    # Act
    response = client.post(f"/friends/requests/{request_id}/respond", json=respond_payload)

    # Assert: Route should raise 404
    assert response.status_code == 404
    assert "Friend request not found" in response.json().get("detail", "")
    mock_friend_service.get_friend_request.assert_called_once_with(request_id)
    mock_friend_service.respond_to_request.assert_not_called()


def test_respond_to_request_forbidden(client, mock_friend_service, sample_friend_request, test_user_1_uid):
    """Test responding to a request not intended for the authenticated user."""
    # Arrange
    request_id = sample_friend_request.request_id
    # Ensure receiver is NOT the authenticated user
    sample_friend_request.receiver_id = "another_user_id"
    mock_friend_service.get_friend_request.return_value = sample_friend_request
    respond_payload = {"accept": True}

    # Act
    response = client.post(f"/friends/requests/{request_id}/respond", json=respond_payload)

    # Assert: Route should raise 403
    assert response.status_code == 403
    assert "Cannot respond to requests for other users" in response.json().get("detail", "")
    mock_friend_service.get_friend_request.assert_called_once_with(request_id)
    mock_friend_service.respond_to_request.assert_not_called()


def test_respond_to_request_service_fails(client, mock_friend_service, sample_friend_request, test_user_1_uid):
    """Test responding when the service layer fails the operation."""
    # Arrange
    request_id = sample_friend_request.request_id
    sample_friend_request.receiver_id = test_user_1_uid
    mock_friend_service.get_friend_request.return_value = sample_friend_request
    mock_friend_service.respond_to_request.return_value = False  # Simulate service failure
    respond_payload = {"accept": True}

    # Act
    response = client.post(f"/friends/requests/{request_id}/respond", json=respond_payload)

    # Assert: Check response reflects service failure
    assert response.status_code == 400
    # FIX: Assert detail format
    assert response.json() == {"detail": "Failed to respond to friend request (e.g., request not pending or db error)"}
    mock_friend_service.get_friend_request.assert_called_once_with(request_id)
    mock_friend_service.respond_to_request.assert_called_once_with(request_id, True)


# --- Test Cases for /friends/list GET ---

def test_get_friends_list_success(client, mock_friend_service, sample_friend_status, test_user_1_uid):
    """Test getting the friend list when service returns data."""
    # Arrange: Mock service returns a list containing the sample status
    mock_friend_service.get_friends.return_value = [sample_friend_status]

    # Act
    response = client.get("/friends/list")

    # Assert: Check response matches serialized mock data
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["user_id"] == sample_friend_status.user_id
    assert response_data[0]["friend_id"] == sample_friend_status.friend_id
    assert response_data[0]["games_played"] == sample_friend_status.games_played

    # Assert service called correctly
    mock_friend_service.get_friends.assert_called_once_with(test_user_1_uid)


def test_get_friends_list_empty(client, mock_friend_service, test_user_1_uid):
    """Test getting the friend list when the user has no friends."""
    # Arrange: Mock service returns empty list
    mock_friend_service.get_friends.return_value = []

    # Act
    response = client.get("/friends/list")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    mock_friend_service.get_friends.assert_called_once_with(test_user_1_uid)


# --- Test Cases for /friends/{friend_id} DELETE ---

def test_remove_friend_success(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test successfully removing a friend."""
    # Arrange
    friend_id_to_remove = test_user_2_uid
    mock_friend_service.remove_friend.return_value = True

    # Act
    response = client.delete(f"/friends/{friend_id_to_remove}")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Friend removed successfully"}
    # Verify service called with authenticated user and the friend ID from path
    mock_friend_service.remove_friend.assert_called_once_with(test_user_1_uid, friend_id_to_remove)


def test_remove_friend_service_fails(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test removing a friend when the service layer fails."""
    # Arrange
    friend_id_to_remove = test_user_2_uid
    mock_friend_service.remove_friend.return_value = False  # Simulate failure

    # Act
    response = client.delete(f"/friends/{friend_id_to_remove}")

    # Assert
    assert response.status_code == 400  # Route succeeded
    assert response.json() == {"detail": "Failed to remove friend (e.g., not friends or db error)"}
    mock_friend_service.remove_friend.assert_called_once_with(test_user_1_uid, friend_id_to_remove)


# --- Test Cases for /friends/{friend_id}/interactions POST ---

def test_update_friend_interaction_success(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test successfully updating friend interaction."""
    # Arrange
    friend_id = test_user_2_uid
    interaction_payload = {"game_id": "game_xyz_123"}  # Matches FriendInteractionUpdate
    mock_friend_service.update_last_interaction.return_value = True

    # Act
    response = client.post(f"/friends/{friend_id}/interactions", json=interaction_payload)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Interaction updated successfully"}
    # Verify service call
    mock_friend_service.update_last_interaction.assert_called_once_with(
        test_user_1_uid,
        friend_id,
        "game_xyz_123"  # game_id from payload
    )


def test_update_friend_interaction_no_game_id(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test updating interaction without a game_id (payload is optional)."""
    # Arrange
    friend_id = test_user_2_uid
    interaction_payload = {}  # Empty payload, game_id is optional in schema
    mock_friend_service.update_last_interaction.return_value = True

    # Act
    response = client.post(f"/friends/{friend_id}/interactions", json=interaction_payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Verify service call with game_id=None
    mock_friend_service.update_last_interaction.assert_called_once_with(
        test_user_1_uid,
        friend_id,
        None  # Default or None passed when game_id is missing
    )


def test_update_friend_interaction_service_fails(client, mock_friend_service, test_user_1_uid, test_user_2_uid):
    """Test updating interaction when the service layer fails."""
    # Arrange
    friend_id = test_user_2_uid
    interaction_payload = {"game_id": "game_fail"}
    mock_friend_service.update_last_interaction.return_value = False  # Simulate failure

    # Act
    response = client.post(f"/friends/{friend_id}/interactions", json=interaction_payload)

    # Assert: Route raises 400 on service failure
    assert response.status_code == 400
    assert "Failed to update interaction" in response.json().get("detail", "")
    mock_friend_service.update_last_interaction.assert_called_once()
