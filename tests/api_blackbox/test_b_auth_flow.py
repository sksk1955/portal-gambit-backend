# Filename: tests/api_blackbox/test_b_auth_flow.py

import os

import pytest
import requests

# --- Test Configuration ---
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080").rstrip('/')
# Seconds to wait for potential eventual consistency if needed
API_DELAY = float(os.getenv("TEST_API_DELAY", "0.5"))

# !!! IMPORTANT: Obtain REAL tokens for these environment variables !!!
# 1. Get a Firebase ID Token for a test user (e.g., via Firebase Auth client SDK)
VALID_FIREBASE_ID_TOKEN = os.getenv("TEST_FIREBASE_ID_TOKEN")
# 2. Set the expected UID for the user associated with the Firebase token
EXPECTED_UID_FROM_FIREBASE_TOKEN = os.getenv("TEST_FIREBASE_UID")

# Store the backend token obtained during the test
backend_access_token = None


# --- Helper Functions ---
def get_auth_headers(token):
    """Creates authorization headers if a token is provided."""
    return {"Authorization": f"Bearer {token}"} if token else {}


# --- Test Cases ---

def test_api_ping_root():
    """Tests the root endpoint, which should be public."""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Portal Gambit Backend API"
    assert data["status"] == "running"


def test_api_access_protected_route_no_token():
    """Tests accessing a protected route without any token."""
    # Using /profiles/some-uid as an example protected route
    response = requests.get(f"{BASE_URL}/profiles/some-uid")
    # Expect 401 (Unauthorized) or 403 (Forbidden) depending on FastAPI/middleware setup
    # FastAPI's default for missing HTTPBearer is 403, but our middleware might raise 401
    assert response.status_code in [401, 403]


def test_api_access_protected_route_invalid_token():
    """Tests accessing a protected route with an invalid/malformed token."""
    headers = get_auth_headers("invalid.jwt.token")
    response = requests.get(f"{BASE_URL}/profiles/some-uid", headers=headers)
    assert response.status_code == 401  # Expect 401 due to JWT validation failure
    assert "WWW-Authenticate" in response.headers  # Should indicate Bearer scheme


# --- /auth/token Endpoint Tests ---

@pytest.mark.skipif(not VALID_FIREBASE_ID_TOKEN, reason="Requires TEST_FIREBASE_ID_TOKEN environment variable")
def test_api_get_token_valid_firebase():
    """
    Tests exchanging a valid Firebase ID token for backend access token.
    This is the crucial step to get the token for other tests.
    """
    global backend_access_token
    payload = {"firebase_token": VALID_FIREBASE_ID_TOKEN}
    response = requests.post(f"{BASE_URL}/auth/token", json=payload)

    assert response.status_code == 200, f"Request failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 50  # Basic sanity check
    assert data["token_type"].lower() == "bearer"
    assert "expires_in" in data
    assert isinstance(data["expires_in"], int)
    assert data["expires_in"] > 0

    # Store the obtained token for subsequent verification test
    backend_access_token = data["access_token"]
    print(f"\nSuccessfully obtained backend token: {backend_access_token[:10]}...")  # Log snippet


def test_api_get_token_invalid_firebase_token():
    """Tests using an invalid Firebase token."""
    payload = {"firebase_token": "this-is-not-a-valid-firebase-token"}
    response = requests.post(f"{BASE_URL}/auth/token", json=payload)
    assert response.status_code == 401
    assert "Invalid Firebase token" in response.json().get("detail", "")


def test_api_get_token_missing_firebase_token():
    """Tests calling the endpoint without the firebase_token field."""
    payload = {}  # Missing required field
    response = requests.post(f"{BASE_URL}/auth/token", json=payload)
    assert response.status_code == 422  # Unprocessable Entity (Validation Error)


def test_api_get_token_wrong_field_name():
    """Tests calling the endpoint with a misspelled field."""
    payload = {"firebaseToken": VALID_FIREBASE_ID_TOKEN or "placeholder"}
    response = requests.post(f"{BASE_URL}/auth/token", json=payload)
    assert response.status_code == 422  # Unprocessable Entity


# --- /auth/verify Endpoint Tests ---

@pytest.mark.skipif(not backend_access_token or not EXPECTED_UID_FROM_FIREBASE_TOKEN,
                    reason="Requires backend token from test_api_get_token_valid_firebase and TEST_FIREBASE_UID")
def test_api_verify_valid_backend_token():
    """
    Tests verifying the backend token obtained from /auth/token.
    Relies on test_api_get_token_valid_firebase having run successfully.
    """
    assert backend_access_token is not None, "Backend token was not obtained in previous step"
    headers = get_auth_headers(backend_access_token)
    response = requests.get(f"{BASE_URL}/auth/verify", headers=headers)

    assert response.status_code == 200, f"Verification failed: {response.text}"
    data = response.json()
    assert "uid" in data
    assert data["uid"] == EXPECTED_UID_FROM_FIREBASE_TOKEN  # Verify UID matches expectation
    assert "email" in data  # Based on TokenData schema
    assert "email_verified" in data


def test_api_verify_invalid_backend_token():
    """Tests verifying an invalid/malformed backend token."""
    headers = get_auth_headers("clearly-invalid-backend-token")
    response = requests.get(f"{BASE_URL}/auth/verify", headers=headers)
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json().get("detail", "")
    assert "WWW-Authenticate" in response.headers


def test_api_verify_missing_token():
    """Tests calling /auth/verify without an Authorization header."""
    response = requests.get(f"{BASE_URL}/auth/verify")
    # As noted before, expect 403 from FastAPI default or 401 from middleware
    assert response.status_code in [401, 403]

# --- Optional: Test with expired token (Harder in Black Box) ---
# def test_api_verify_expired_backend_token():
#    # 1. Obtain a token using test_api_get_token_valid_firebase
#    # 2. Wait for longer than the token's expiry time (e.g., ACCESS_TOKEN_EXPIRE_MINUTES)
#    # 3. Call /auth/verify with the expired token
#    # 4. Assert status code is 401 and detail indicates expiration
#    pass # This test takes a long time, often skipped or handled in white-box
