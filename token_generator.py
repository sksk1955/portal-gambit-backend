import json
import os  # Import os to use getenv for backend URL

import requests
from dotenv import load_dotenv

# Load optional .env if needed for API key (or hardcode it temporarily)
load_dotenv()

# --- Configuration ---
# GET THIS FROM YOUR FIREBASE PROJECT SETTINGS! (Project Settings -> General -> Web API Key)
# !! IMPORTANT: Replace "YOUR_FIREBASE_WEB_API_KEY" with your actual key !!
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "YOUR_FIREBASE_WEB_API_KEY")
if FIREBASE_WEB_API_KEY == "YOUR_FIREBASE_WEB_API_KEY":
    print("WARNING: FIREBASE_WEB_API_KEY is not set. Please set it in your .env file or directly in the script.")

# Backend URL (use environment variable like in tests)
BACKEND_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080").rstrip('/')

# Credentials for your test users (replace with actuals you created in Firebase Auth)
USER1_EMAIL = os.getenv("TEST_USER1_EMAIL", "testuser1@example.com")
USER1_PASSWORD = os.getenv("TEST_USER1_PASSWORD", "testP4ssw0rd1")
USER2_EMAIL = os.getenv("TEST_USER2_EMAIL", "testuser2@example.com")
USER2_PASSWORD = os.getenv("TEST_USER2_PASSWORD", "testP4ssw0rd2")

# Firebase REST API endpoint for email/password sign-in
rest_api_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"


# --- Function to Get Firebase Token ---
def get_firebase_id_token(email, password):
    """Authenticates a user via Firebase REST API and returns their Firebase ID token."""
    print(f"Attempting Firebase authentication for {email}...")
    payload = json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True
    })
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(rest_api_url, headers=headers, data=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        token_data = response.json()
        print(f"Successfully authenticated {email} with Firebase.")
        # print(f"Full Firebase Response: {token_data}") # Uncomment for debugging
        return token_data.get("idToken")
    except requests.exceptions.RequestException as e:
        print(f"Error authenticating {email} with Firebase: {e}")
        if e.response is not None:
            print(f"Firebase Error details: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding Firebase response for {email}.")
        return None


# --- Function to Get Backend Token ---
def get_backend_token(base_url, firebase_id_token):
    """Exchanges a Firebase ID token for a backend access token."""
    if not firebase_id_token:
        return None

    backend_token_url = f"{base_url}/auth/token"
    print(f"Attempting backend token exchange at {backend_token_url}...")
    payload = json.dumps({"firebase_token": firebase_id_token})
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(backend_token_url, headers=headers, data=payload)
        response.raise_for_status()
        token_data = response.json()
        print("Successfully exchanged Firebase token for backend token.")
        # print(f"Full Backend Response: {token_data}") # Uncomment for debugging
        return token_data.get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Error exchanging token with backend: {e}")
        if e.response is not None:
            print(f"Backend Error details: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print("Error decoding backend response.")
        return None


# --- Main Execution ---

# --- Step 1: Get Firebase ID Tokens ---
print("\n--- Step 1: Obtaining Firebase ID Tokens ---")
user1_firebase_token = get_firebase_id_token(USER1_EMAIL, USER1_PASSWORD)
user2_firebase_token = get_firebase_id_token(USER2_EMAIL, USER2_PASSWORD)

# --- Step 2: Exchange for Backend Tokens ---
print("\n--- Step 2: Exchanging for Backend Access Tokens ---")
user1_backend_token = None
user2_backend_token = None

if user1_firebase_token:
    user1_backend_token = get_backend_token(BACKEND_BASE_URL, user1_firebase_token)
else:
    print("Skipping backend token exchange for User 1 (Firebase token missing).")

if user2_firebase_token:
    user2_backend_token = get_backend_token(BACKEND_BASE_URL, user2_firebase_token)
else:
    print("Skipping backend token exchange for User 2 (Firebase token missing).")

# --- Step 3: Print Results for Environment Variables ---
print("\n--- Step 3: Tokens for Environment Variables ---")

if user1_firebase_token:
    print("Set this Firebase token for TEST_FIREBASE_ID_TOKEN:")
    print(f"{user1_firebase_token}\n")
else:
    print("Failed to get Firebase ID Token for User 1.\n")

if user1_backend_token:
    print("Set this backend token for TEST_USER1_BACKEND_TOKEN:")
    print(f"{user1_backend_token}\n")
else:
    print("Failed to get Backend Access Token for User 1.\n")

if user2_backend_token:
    print("Set this backend token for TEST_USER2_BACKEND_TOKEN:")
    print(f"{user2_backend_token}\n")
else:
    print("Failed to get Backend Access Token for User 2.\n")

print("Remember to also set TEST_USER1_UID and TEST_USER2_UID (obtainable from Firebase console or decoded tokens).")
