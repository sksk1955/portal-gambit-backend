# Filename: tests/integration_whitebox/test_i_auth_routes.py
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from utils import jwt_utils


# Fixtures: client_no_auth_bypass, mock_verify_firebase_token from conftest.py

# --- Test Cases for /auth/token ---

# @patch("utils.jwt_utils.create_tokens_for_user")  # Mock our internal token creation
def test_get_token_success(
        mocker,  # Mocked jwt_utils function
        client_no_auth_bypass,  # TestClient without auth middleware bypassed
        mock_verify_firebase_token  # Mocked firebase_admin.auth.verify_id_token
):
    """Test successfully exchanging a Firebase token for backend tokens."""
    # Arrange: Configure mocks
    firebase_token_input = "valid-firebase-id-token-string"
    # mock_verify_firebase_token is already configured in conftest to return sample data
    expected_firebase_payload = mock_verify_firebase_token.return_value
    mock_create_tokens = mocker.patch(
        "routes.auth_routes.create_tokens_for_user",
        return_value={
            "access_token": jwt_utils.create_access_token(expected_firebase_payload), # Generate a real token for verification
            "token_type": "bearer",
            "expires_in": 3600
        }
    )
    # Act: Call the endpoint
    response = client_no_auth_bypass.post("/auth/token", json={"firebase_token": firebase_token_input})

    # Assert: Check status code and response body
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Decode the ACTUAL token returned to verify claims
    try:
        # Use the actual verify_token function (or jwt.decode directly)
        # Make sure your test environment has JWT_SECRET_KEY set correctly
        payload = jwt_utils.verify_token(data["access_token"])
        assert payload["uid"] == expected_firebase_payload["uid"]  # Verify claims
        assert payload["email"] == expected_firebase_payload.get("email")
    except Exception as e:
        pytest.fail(f"Failed to decode/verify the generated token: {e}")

    # Assert: Check that mocks were called correctly
    mock_verify_firebase_token.assert_called_once_with(firebase_token_input)
    mock_create_tokens.assert_called_once_with(expected_firebase_payload)  # Assert the patched function was called


def test_get_token_invalid_firebase_token(client_no_auth_bypass, mock_verify_firebase_token):
    """Test exchanging an invalid Firebase token."""
    # Arrange: Configure mock to raise exception
    firebase_token_input = "invalid-firebase-token"
    mock_verify_firebase_token.side_effect = Exception("Firebase verification failed mock")

    # Act
    response = client_no_auth_bypass.post("/auth/token", json={"firebase_token": firebase_token_input})

    # Assert
    assert response.status_code == 401
    assert "Invalid Firebase token" in response.json().get("detail", "")
    mock_verify_firebase_token.assert_called_once_with(firebase_token_input)


def test_get_token_missing_payload_field(client_no_auth_bypass):
    """Test calling /auth/token with missing 'firebase_token' field."""
    response = client_no_auth_bypass.post("/auth/token", json={"wrong_field": "some_token"})
    assert response.status_code == 422  # Validation error


def test_get_token_empty_payload(client_no_auth_bypass):
    """Test calling /auth/token with an empty JSON body."""
    response = client_no_auth_bypass.post("/auth/token", json={})
    assert response.status_code == 422  # Validation error


# --- Test Cases for /auth/verify ---

@patch(
    "utils.jwt_utils.verify_token")  # Keep mocking verify_token for this test? Maybe not needed if testing the route directly
def test_verify_token_success(mock_verify_jwt, client_no_auth_bypass):
    # Arrange
    # Generate a valid token using the utils
    valid_payload = {"uid": "verified-user-uid", "email": "verified@example.com"}
    backend_token_input = jwt_utils.create_access_token(valid_payload)  # Use the util!

    # Set up the mock to return the payload IF verify_token is still mocked
    mock_verify_jwt.return_value = valid_payload
    headers = {"Authorization": f"Bearer {backend_token_input}"}

    # Act
    response = client_no_auth_bypass.get("/auth/verify", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == "verified-user-uid"
    # Assert mock called correctly (if still mocking)
    # mock_verify_jwt.assert_called_once_with(backend_token_input)


# @patch("utils.jwt_utils.verify_token")
def test_verify_token_invalid(client_no_auth_bypass): # Remove the mock argument
    # ... rest of the test ...
    # Make sure the token is structurally invalid enough to cause jose error
    backend_token_input = "this.is.invalid"
    headers = {"Authorization": f"Bearer {backend_token_input}"}
    response = client_no_auth_bypass.get("/auth/verify", headers=headers)
    # Assert based on the HTTPException raised by the middleware when it catches JWTError
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json().get("detail", "")


def test_verify_token_missing_header(client_no_auth_bypass):
    """Test calling /auth/verify without the Authorization header."""
    response = client_no_auth_bypass.get("/auth/verify")
    # FastAPI's dependency injection for Security raises 403 if header is missing
    assert response.status_code == 403


def test_verify_token_malformed_header(client_no_auth_bypass):
    """Test calling /auth/verify with a malformed Authorization header."""
    headers = {"Authorization": "NotBearer some_token"}
    response = client_no_auth_bypass.get("/auth/verify", headers=headers)
    # FastAPI's HTTPBearer dependency raises 403 if scheme doesn't match
    assert response.status_code == 403
