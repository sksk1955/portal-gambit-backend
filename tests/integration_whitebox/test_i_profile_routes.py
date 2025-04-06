from datetime import datetime, timezone
from unittest.mock import patch

# Import models/schemas used for request/response validation if needed
from models.user_profile import UserProfile


# Fixtures: client, mock_profile_service, sample_user_profile, test_user_1_uid from conftest.py

# --- Test Cases for /profiles/ ---

def test_create_profile_success(client, mock_profile_service, test_user_1_uid):
    """Test successfully creating a profile for the authenticated user."""
    # ... (Arrange profile_payload) ...
    profile_payload = {
        "uid": test_user_1_uid, "username": "integration_tester",  # ... rest of payload
        "email": "integration@example.com", "rating": 1210, "games_played": 1,
        "wins": 1, "losses": 0, "draws": 0, "friends": [], "achievements": [],
        "preferences": {}, "created_at": datetime.now(timezone.utc).isoformat(),
        "last_active": datetime.now(timezone.utc).isoformat(),
        "display_name": "Integration Tester", "avatar_url": None
    }
    # Mock the service call for create_profile
    mock_profile_service.create_profile.return_value = True
    # FIX: Also mock get_profile used internally by the route to check existence
    with patch.object(mock_profile_service, 'get_profile', return_value=None) as mock_get:
        # Act: Make the request
        response = client.post("/profiles/", json=profile_payload)

    # Assert: Check response and mock calls
    assert response.status_code == 201  # Check for 201 Created
    assert response.json()["status"] == "success"
    mock_get.assert_called_once_with(test_user_1_uid)  # Verify existence check
    mock_profile_service.create_profile.assert_called_once()
    # Verify the data passed to the service matches the Pydantic model instance
    call_arg = mock_profile_service.create_profile.call_args[0][0]
    assert isinstance(call_arg, UserProfile)
    assert call_arg.uid == test_user_1_uid
    assert call_arg.username == "integration_tester"


def test_create_profile_forbidden(client, mock_profile_service, test_user_1_uid):
    """Test creating a profile for a UID other than the authenticated user."""
    # Arrange: Payload UID differs from authenticated user's UID
    profile_payload = {
        "uid": "some-other-uid",  # Different from test_user_1_uid
        "username": "forbidden_user",
        "email": "forbidden@example.com",
        "rating": 1200, "games_played": 0, "wins": 0, "losses": 0, "draws": 0,
        "friends": [], "achievements": [], "preferences": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_active": datetime.now(timezone.utc).isoformat(),
    }

    # Act
    response = client.post("/profiles/", json=profile_payload)

    # Assert
    assert response.status_code == 403
    assert "Cannot create profile for another user" in response.json().get("detail", "")
    mock_profile_service.create_profile.assert_not_called()


def test_create_profile_service_fails(client, mock_profile_service, test_user_1_uid):
    """Test profile creation when the service layer returns False."""
    # ... (Arrange profile_payload) ...
    profile_payload = {
        "uid": test_user_1_uid, "username": "fail_user", "email": "fail@example.com",
    }
    mock_profile_service.create_profile.return_value = False  # Simulate service failure
    # FIX: Also mock get_profile used internally by the route to check existence
    with patch.object(mock_profile_service, 'get_profile', return_value=None) as mock_get:
        # Act
        response = client.post("/profiles/", json=profile_payload)

    # Assert: Route should now raise 500 on service failure
    assert response.status_code == 500 # Assuming 500 is correct for DB failure
    # FIX: Assert detail format
    assert response.json() == {"detail": "Failed to create profile in database"}
    mock_get.assert_called_once_with(test_user_1_uid)  # Verify existence check
    mock_profile_service.create_profile.assert_called_once()
    # Optional deeper check: Verify the model instance passed to the service
    call_arg = mock_profile_service.create_profile.call_args[0][0]
    assert isinstance(call_arg, UserProfile)
    assert call_arg.uid == test_user_1_uid
    assert call_arg.username == "fail_user"
    assert call_arg.email == "fail@example.com"
    # Check that default values were applied by Pydantic before service call
    assert call_arg.rating == 1200
    assert call_arg.friends == []
    assert call_arg.preferences == {}


def test_create_profile_validation_error(client, mock_profile_service, test_user_1_uid):
    """Test profile creation with invalid data (e.g., missing required field)."""
    # Arrange: Missing 'email', 'username' which are likely required by UserProfile model
    profile_payload = {
        "uid": test_user_1_uid,
        "rating": 1100,
    }

    # Act
    response = client.post("/profiles/", json=profile_payload)

    # Assert: FastAPI should return 422
    assert response.status_code == 422
    mock_profile_service.create_profile.assert_not_called()


# --- Test Cases for /profiles/{uid} GET ---

def test_get_profile_found(client, mock_profile_service, sample_user_profile):
    """Test retrieving an existing profile by UID."""
    # Arrange: Mock service to return the sample profile
    uid_to_get = sample_user_profile.uid
    mock_profile_service.get_profile.return_value = sample_user_profile

    # Act
    response = client.get(f"/profiles/{uid_to_get}")

    # Assert: Check response matches the sample profile data (serialized)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["uid"] == uid_to_get
    assert response_data["username"] == sample_user_profile.username
    assert response_data["rating"] == sample_user_profile.rating
    # Compare a datetime field (requires careful parsing or string comparison)
    # FastAPI serializes datetime to ISO string by default
    assert response_data["created_at"] == sample_user_profile.created_at.isoformat().replace('+00:00', 'Z')

    # Assert service was called correctly
    mock_profile_service.get_profile.assert_called_once_with(uid_to_get)


def test_get_profile_not_found(client, mock_profile_service):
    """Test retrieving a profile that the service indicates is not found."""
    # Arrange: Mock service to return None
    uid_to_get = "non-existent-user"
    mock_profile_service.get_profile.return_value = None

    # Act
    response = client.get(f"/profiles/{uid_to_get}")

    # Assert: Route should return 404
    assert response.status_code == 404
    assert "Profile not found" in response.json().get("detail", "")
    mock_profile_service.get_profile.assert_called_once_with(uid_to_get)


# --- Test Cases for /profiles/{uid} PATCH ---

def test_update_profile_success(client, mock_profile_service, test_user_1_uid):
    """Test successfully updating the authenticated user's profile."""
    # Arrange: Prepare update payload matching ProfileUpdate schema
    uid_to_update = test_user_1_uid  # Matches authenticated user
    update_payload = {
        "display_name": "Updated Int Name",
        "avatar_url": "http://example.com/updated.png",
        "preferences": {"sound": False}
    }
    # Mock service success
    mock_profile_service.update_profile.return_value = True

    # Act
    response = client.patch(f"/profiles/{uid_to_update}", json=update_payload)

    # Assert: Check response and service call
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Profile updated successfully"}
    # Service should be called with a dict containing only the fields present in the payload
    # (due to exclude_unset=True in the route)
    mock_profile_service.update_profile.assert_called_once_with(
        uid_to_update,
        update_payload  # exclude_unset means only these fields are passed
    )


def test_update_profile_partial(client, mock_profile_service, test_user_1_uid):
    """Test updating only one field in the profile."""
    # Arrange
    uid_to_update = test_user_1_uid
    update_payload = {"display_name": "Just Display Name"}  # Only one field
    mock_profile_service.update_profile.return_value = True

    # Act
    response = client.patch(f"/profiles/{uid_to_update}", json=update_payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Verify only the provided field was passed to the service
    mock_profile_service.update_profile.assert_called_once_with(
        uid_to_update,
        {"display_name": "Just Display Name"}
    )


def test_update_profile_forbidden(client, mock_profile_service, test_user_1_uid):
    """Test attempting to update another user's profile."""
    # Arrange
    uid_to_update = "another-users-profile-id"  # Different UID
    update_payload = {"display_name": "Hacking Attempt"}

    # Act
    response = client.patch(f"/profiles/{uid_to_update}", json=update_payload)

    # Assert
    assert response.status_code == 403
    assert "Cannot update another user's profile" in response.json().get("detail", "")
    mock_profile_service.update_profile.assert_not_called()


def test_update_profile_service_fails(client, mock_profile_service, test_user_1_uid):
    """Test profile update when the service layer returns False."""
    # Arrange
    uid_to_update = test_user_1_uid
    update_payload = {"display_name": "Update Me Fail"}
    mock_profile_service.update_profile.return_value = False  # Simulate service failure

    # Act
    response = client.patch(f"/profiles/{uid_to_update}", json=update_payload)

    # Assert
    assert response.status_code == 500
    # FIX: Assert detail format
    assert response.json() == {"detail": "Failed to update profile in database"}
    mock_profile_service.update_profile.assert_called_once()


# --- Test Cases for /profiles/search/{username_prefix} ---

def test_search_profiles_found(client, mock_profile_service, sample_user_profile):
    """Test searching for profiles when the service finds results."""
    # Arrange
    prefix = "integ"
    mock_results = [sample_user_profile]  # Service returns a list containing the sample
    mock_profile_service.search_profiles.return_value = mock_results
    limit = 5

    # Act
    response = client.get(f"/profiles/search/{prefix}?limit={limit}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["uid"] == sample_user_profile.uid  # Compare response to mock data

    # Assert service call
    mock_profile_service.search_profiles.assert_called_once_with(prefix, limit)


def test_search_profiles_not_found(client, mock_profile_service):
    """Test searching for profiles when the service finds no results."""
    # Arrange
    prefix = "nonexistentprefix"
    mock_profile_service.search_profiles.return_value = []  # Service returns empty list
    limit = 10

    # Act
    response = client.get(f"/profiles/search/{prefix}?limit={limit}")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    mock_profile_service.search_profiles.assert_called_once_with(prefix, limit)


# --- Test Cases for /profiles/leaderboard/top ---

def test_get_leaderboard_success(client, mock_profile_service, sample_user_profile):
    """Test fetching the leaderboard when the service returns data."""
    # Arrange
    mock_leaderboard_data = [sample_user_profile]  # Simulate service returning leaderboard
    mock_profile_service.get_leaderboard.return_value = mock_leaderboard_data
    limit = 10

    # Act
    response = client.get(f"/profiles/leaderboard/top?limit={limit}")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]["uid"] == sample_user_profile.uid  # Compare response to mock

    # Assert service call
    mock_profile_service.get_leaderboard.assert_called_once_with(limit)


# --- Test Cases for /profiles/{uid}/achievements/{achievement_id} ---

def test_add_achievement_success(client, mock_profile_service, test_user_1_uid):
    """Test adding an achievement to the authenticated user's profile."""
    # Arrange
    uid = test_user_1_uid  # Matches authenticated user
    achievement_id = "integration_complete"
    # Mock service success
    mock_profile_service.add_achievement.return_value = True

    # Act: Route uses path params based on definition
    response = client.post(f"/profiles/{uid}/achievements/{achievement_id}")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Achievement added successfully"}
    mock_profile_service.add_achievement.assert_called_once_with(uid, achievement_id)


def test_add_achievement_forbidden(client, mock_profile_service, test_user_1_uid):
    """Test attempting to add an achievement to another user's profile."""
    # Arrange
    uid = "another-user-achieve"  # Different UID
    achievement_id = "forbidden_achieve"

    # Act
    response = client.post(f"/profiles/{uid}/achievements/{achievement_id}")

    # Assert
    assert response.status_code == 403
    assert "Cannot modify another user's achievements" in response.json().get("detail", "")
    mock_profile_service.add_achievement.assert_not_called()


def test_add_achievement_service_fails(client, mock_profile_service, test_user_1_uid):
    """Test adding achievement when the service layer returns False."""
    # Arrange
    uid = test_user_1_uid
    achievement_id = "fail_achieve"
    mock_profile_service.add_achievement.return_value = False  # Simulate service failure

    # Act
    response = client.post(f"/profiles/{uid}/achievements/{achievement_id}")

    # Assert
    assert response.status_code == 500  # Route succeeded
    assert response.json() == {"detail": "Failed to add achievement"}
    mock_profile_service.add_achievement.assert_called_once_with(uid, achievement_id)
