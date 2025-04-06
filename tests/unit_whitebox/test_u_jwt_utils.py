# Filename: tests/unit_whitebox/test_u_jwt_utils.py
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi import HTTPException
import pytest
from jose import JWTError, ExpiredSignatureError

# Import the module to be tested
from utils import jwt_utils


# Import specific exceptions if defined in jwt_utils or rely on jose's
# For this example, we assume it might raise HTTPException directly or rely on JOSE errors

# --- Test Configuration / Mocks ---

# We need to ensure the constants used by jwt_utils are available.
# Patching os.getenv is one way if they aren't set in the test environment.
@pytest.fixture(autouse=True)
def mock_jwt_settings():
    """Mocks environment variables used by jwt_utils."""
    with patch.dict(jwt_utils.os.environ, {
        "JWT_SECRET_KEY": "test-secret-key-for-unit-tests",
        # Optionally override ALGORITHM or EXPIRE_MINUTES if needed for tests
        # "JWT_ALGORITHM": "HS256",
        # "ACCESS_TOKEN_EXPIRE_MINUTES": "1" # Example: 1 minute expiry for testing
    }):
        # Reload the module IF it reads env vars at import time.
        # If it reads them inside functions, this might not be strictly needed,
        # but it's safer.
        import importlib
        importlib.reload(jwt_utils)
        yield
        # Restore original settings if necessary (though usually not needed for tests)
        importlib.reload(jwt_utils)


# --- Test Cases ---

def test_create_access_token_default_expiry():
    """Test creating a token with the default expiration."""
    data_to_encode = {"uid": "user123", "role": "tester"}
    token = jwt_utils.create_access_token(data=data_to_encode)

    assert isinstance(token, str)
    # Decode without verification to check payload structure (using a different library if needed, or jose itself)
    # Note: Direct decoding without verification is generally discouraged outside tests
    payload = jwt_utils.jwt.decode(token, jwt_utils.SECRET_KEY, algorithms=[jwt_utils.ALGORITHM],
                                   options={"verify_signature": False, "verify_exp": False})
    assert payload["uid"] == "user123"
    assert payload["role"] == "tester"
    assert "exp" in payload
    # Check if expiry is roughly correct (within a few seconds of default)
    expected_exp = datetime.now(timezone.utc) + timedelta(minutes=jwt_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    actual_exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
    assert abs((expected_exp - actual_exp).total_seconds()) < 5  # Allow 5 seconds difference


def test_create_access_token_custom_expiry():
    """Test creating a token with a specific expiration delta."""
    data_to_encode = {"uid": "user456"}
    custom_delta = timedelta(hours=2)
    token = jwt_utils.create_access_token(data=data_to_encode, expires_delta=custom_delta)

    assert isinstance(token, str)
    payload = jwt_utils.jwt.decode(token, jwt_utils.SECRET_KEY, algorithms=[jwt_utils.ALGORITHM],
                                   options={"verify_signature": False, "verify_exp": False})
    assert payload["uid"] == "user456"
    assert "exp" in payload
    expected_exp = datetime.now(timezone.utc) + custom_delta
    actual_exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
    assert abs((expected_exp - actual_exp).total_seconds()) < 5  # Allow 5 seconds difference


def test_verify_token_valid():
    """Test verifying a valid, unexpired token."""
    data = {"uid": "verify_me", "data": "test"}
    token = jwt_utils.create_access_token(data)
    time.sleep(0.1)  # Ensure token timestamp is slightly in the past

    payload = jwt_utils.verify_token(token)

    assert payload["uid"] == "verify_me"
    assert payload["data"] == "test"
    assert "exp" in payload


def test_verify_token_invalid_signature():
    """Test verifying a token signed with a different secret."""
    data = {"uid": "bad_sig"}
    # Create token with the correct algorithm but wrong key
    wrong_secret = "a-completely-different-secret"
    invalid_token = jwt_utils.jwt.encode(data, wrong_secret, algorithm=jwt_utils.ALGORITHM)

    # verify_token should raise an exception caught by the try...except block
    # which then raises an HTTPException (check jwt_utils implementation)
    # If verify_token raises jose.JWTError directly without catching:
    with pytest.raises(HTTPException) as exc_info:
        jwt_utils.verify_token(invalid_token)
    assert exc_info.value.status_code == 401
    assert "Signature verification failed" in exc_info.value.detail # Check detail


def test_verify_token_expired():
    """Test verifying a token that has expired."""
    data = {"uid": "expired_user"}
    # Create a token that expired 1 second ago
    expiry_delta = timedelta(seconds=-1)
    expired_token = jwt_utils.create_access_token(data, expires_delta=expiry_delta)

    # If verify_token raises jose.ExpiredSignatureError directly:
    # with pytest.raises(ExpiredSignatureError):
    #     jwt_utils.verify_token(expired_token)

    # If verify_token catches JWTError and raises HTTPException(401):
    with pytest.raises(HTTPException) as exc_info:
        jwt_utils.verify_token(expired_token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail # Or specific expiry message


def test_verify_token_malformed():
    """Test verifying a token that is not a valid JWT format."""
    malformed_token = "this.is.not.a.jwt"
    # with pytest.raises(JWTError):  # Expecting jose decode error
    #     jwt_utils.verify_token(malformed_token)

    # Or check for HTTPException if caught internally
    with pytest.raises(HTTPException) as exc_info:
        jwt_utils.verify_token(malformed_token)
    assert exc_info.value.status_code == 401


def test_create_tokens_for_user():
    """Test the helper function to create tokens based on Firebase user data."""
    # Simulate the structure returned by firebase_admin.auth.verify_id_token
    firebase_user_data = {
        "uid": "fb_user_for_token",
        "email": "fb_user@example.com",
        "email_verified": True,
        "name": "Firebase User Name"  # Other claims might be present
    }

    token_response = jwt_utils.create_tokens_for_user(firebase_user_data)

    assert "access_token" in token_response
    assert isinstance(token_response["access_token"], str)
    assert token_response["token_type"] == "bearer"
    assert "expires_in" in token_response
    assert token_response["expires_in"] == jwt_utils.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Verify the claims within the generated access token
    access_token = token_response["access_token"]
    payload = jwt_utils.verify_token(access_token)
    assert payload["uid"] == "fb_user_for_token"
    assert payload["email"] == "fb_user@example.com"
    assert payload["email_verified"] is True
    assert "exp" in payload
    # Ensure extra claims from input aren't included unless explicitly added
    assert "name" not in payload


def test_create_tokens_for_user_minimal_firebase_data():
    """Test token creation with minimal required data from Firebase."""
    firebase_user_data = {
        "uid": "minimal_fb_user"
        # Email might be missing or not verified
    }

    token_response = jwt_utils.create_tokens_for_user(firebase_user_data)

    assert "access_token" in token_response
    access_token = token_response["access_token"]
    payload = jwt_utils.verify_token(access_token)
    assert payload["uid"] == "minimal_fb_user"
    assert payload.get("email") is None  # Check default handling
    assert payload.get("email_verified") is False  # Check default handling
