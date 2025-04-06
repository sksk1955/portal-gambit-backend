import os
import time
import uuid

import pytest
import requests

# --- Test Configuration ---
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080").rstrip('/')
# Increased default delay, can be overridden by environment variable
API_DELAY = float(os.getenv("TEST_API_DELAY", "1.5"))

USER1_TOKEN = os.getenv("TEST_USER1_BACKEND_TOKEN")
USER1_UID = os.getenv("TEST_USER1_UID")

config_present = USER1_TOKEN and USER1_UID
if not config_present:
    print(
        "\nWARNING: Missing environment variables for profile flow tests (TEST_USER1_BACKEND_TOKEN, "
        "TEST_USER1_UID). Tests will be skipped.")


def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


# --- Combined Test Case ---

@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_profile_crud_search_achievement():
    """Tests profile creation/get, update, search, and adding achievements sequentially."""
    headers = get_auth_headers(USER1_TOKEN)
    test_run_username = f"bb_user_{uuid.uuid4().hex[:8]}"  # Use local variable
    profile_data = None  # Use local variable

    # --- Step 1: Create or Get Profile ---
    print(f"\n--- Profile Step 1: Ensuring profile exists for {USER1_UID} ---")
    get_response = requests.get(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers)

    profile_created_or_updated = False  # Flag to indicate if we should wait

    if get_response.status_code == 404:
        print(f"Profile for {USER1_UID} not found (404). Attempting creation with username {test_run_username}...")
        create_payload = {
            "uid": USER1_UID,
            "username": test_run_username,
            "email": f"{test_run_username}@example.com",
            "rating": 1200, "games_played": 0, "wins": 0, "losses": 0, "draws": 0,
            "friends": [], "achievements": [], "preferences": {},
            "display_name": "BB Test User", "avatar_url": None
        }
        create_response = requests.post(f"{BASE_URL}/profiles/", headers=headers, json=create_payload)

        if create_response.status_code == 409:  # Conflict (profile likely created between GET and POST)
            print(f"Profile creation returned 409 Conflict. Getting existing profile...")
            get_response = requests.get(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers)
            assert get_response.status_code == 200, "Failed to get profile after 409 on create."
            profile_data = get_response.json()
            # If it existed, it might have a different username, try to update
            if profile_data["username"] != test_run_username:
                print(
                    f"Profile existed with username {profile_data['username']}, "
                    f"attempting update to {test_run_username}")
                update_resp = requests.patch(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers,
                                             json={"username": test_run_username})
                if update_resp.status_code == 200:
                    print("Username updated successfully for search test.")
                    profile_data["username"] = test_run_username
                    profile_created_or_updated = True
                else:
                    print(
                        f"Warning: Failed to update username for existing profile after 409 ({update_resp.status_code})"
            
                        f". Search test might use old username.")
                    test_run_username = profile_data["username"]  # Use existing name for search
            else:
                test_run_username = profile_data["username"]  # Ensure local var matches DB

        elif create_response.status_code == 200:
            assert create_response.json().get("status") == "success", f"Create request failed: {create_response.text}"
            print(f"Profile for {USER1_UID} created successfully.")
            profile_created_or_updated = True
            # Get profile data after creation
            get_response = requests.get(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers)
            assert get_response.status_code == 200, "Failed to get profile immediately after creation."
            profile_data = get_response.json()
        else:
            pytest.fail(
                f"Unexpected status code {create_response.status_code} during profile creation: {create_response.text}")

    elif get_response.status_code == 200:
        print(f"\nProfile for {USER1_UID} already exists.")
        profile_data = get_response.json()
        # If it existed, it might have a different username, try to update
        if profile_data["username"] != test_run_username:
            print(f"Profile existed with username {profile_data['username']}, attempting update to {test_run_username}")
            update_resp = requests.patch(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers,
                                         json={"username": test_run_username})
            if update_resp.status_code == 200:
                print("Username updated successfully for search test.")
                profile_data["username"] = test_run_username
                profile_created_or_updated = True
            else:
                print(
                    f"Warning: Failed to update username for existing profile ({update_resp.status_code})."
                    f" Search test might use old username.")
                test_run_username = profile_data["username"]  # Use existing name for search
        else:
            test_run_username = profile_data["username"]  # Ensure local var matches DB

    else:  # Handle unexpected status codes from initial GET
        pytest.fail(
            f"Unexpected status code {get_response.status_code} when checking profile existence: {get_response.text}")

    assert profile_data is not None, "Failed to get or create profile data"
    assert profile_data["uid"] == USER1_UID
    original_rating = profile_data["rating"]

    # FIX: Add delay if profile was just created or username updated
    if profile_created_or_updated:
        print(f"Waiting {API_DELAY}s after profile creation/update for consistency...")
        time.sleep(API_DELAY)

    # --- Step 2: Update Profile (other fields) ---
    print("\n--- Profile Step 2: Updating profile ---")
    new_display_name = f"Updated BB {int(time.time())}"
    new_avatar_url = f"http://example.com/new_avatar_{uuid.uuid4().hex[:4]}.png"
    new_preferences = {"theme": "chesscom", "sound_volume": 8}
    update_payload = {
        "display_name": new_display_name,
        "avatar_url": new_avatar_url,
        "preferences": new_preferences
    }
    response_update = requests.patch(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers, json=update_payload)
    assert response_update.status_code == 200, f"Update failed: {response_update.text}"
    assert response_update.json().get("status") == "success"
    print("Profile update successful.")

    # --- Step 3: Verify Update ---
    # FIX: Add delay before verifying the update
    print(f"Waiting {API_DELAY}s after update before verification...")
    time.sleep(API_DELAY)
    get_response_updated = requests.get(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers)
    assert get_response_updated.status_code == 200
    updated_data = get_response_updated.json()
    assert updated_data["display_name"] == new_display_name
    assert updated_data["avatar_url"] == new_avatar_url
    assert updated_data["preferences"] == new_preferences
    assert updated_data["rating"] == original_rating  # Check rating didn't change

    # --- Step 4: Search Profile ---
    # FIX: Add significant delay before search, especially if username was updated
    search_delay = API_DELAY * 2  # Double delay before search
    print(f"\n--- Profile Step 4: Waiting {search_delay}s before searching for profile '{test_run_username}' ---")
    time.sleep(search_delay)
    search_prefix = test_run_username[:5]  # Use potentially updated username
    response_search = requests.get(f"{BASE_URL}/profiles/search/{search_prefix}?limit=5", headers=headers)
    assert response_search.status_code == 200
    search_results = response_search.json()
    print(f"Search results for prefix '{search_prefix}': {search_results}")  # Log search results
    assert isinstance(search_results, list)
    found = any(profile["uid"] == USER1_UID and profile["username"] == test_run_username for profile in search_results)
    assert found, f"Profile with username {test_run_username} not found in search results for prefix '{search_prefix}'"
    print("Profile search successful.")

    # --- Step 5: Add Achievement ---
    print("\n--- Profile Step 5: Adding achievement ---")
    achievement_id = f"bb_achieve_{uuid.uuid4().hex[:6]}"
    response_achieve = requests.post(f"{BASE_URL}/profiles/{USER1_UID}/achievements/{achievement_id}", headers=headers)
    assert response_achieve.status_code == 200, f"Add achievement failed: {response_achieve.text}"
    assert response_achieve.json().get("status") == "success"
    print("Add achievement successful.")

    # --- Step 6: Verify Achievement ---
    # FIX: Add delay before verifying achievement
    print(f"Waiting {API_DELAY}s after adding achievement...")
    time.sleep(API_DELAY)
    get_response_final = requests.get(f"{BASE_URL}/profiles/{USER1_UID}", headers=headers)
    assert get_response_final.status_code == 200
    final_data = get_response_final.json()
    assert achievement_id in final_data.get("achievements", [])
    print("Achievement verification successful.")


# Keep other tests like leaderboard, negative cases etc. as they were

@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_get_leaderboard():
    """Tests fetching the leaderboard."""
    headers = get_auth_headers(USER1_TOKEN)
    limit = 10
    response = requests.get(f"{BASE_URL}/profiles/leaderboard/top?limit={limit}", headers=headers)
    assert response.status_code == 200
    leaderboard = response.json()
    assert isinstance(leaderboard, list)
    assert len(leaderboard) <= limit
    if len(leaderboard) > 1:
        for i in range(len(leaderboard) - 1):
            assert leaderboard[i].get("rating", 0) >= leaderboard[i + 1].get("rating", 0)


@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_create_profile_missing_data():
    """Tests creating a profile with missing required fields."""
    headers = get_auth_headers(USER1_TOKEN)
    payload = {"uid": USER1_UID}  # Missing username, email
    response = requests.post(f"{BASE_URL}/profiles/", headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_create_profile_forbidden():
    """Tests creating a profile for a different UID than the authenticated user."""
    headers = get_auth_headers(USER1_TOKEN)
    different_uid = f"other-uid-{uuid.uuid4().hex}"
    payload = {
        "uid": different_uid, "username": f"forbidden_{uuid.uuid4().hex[:6]}", "email": "forbidden@example.com",
        "rating": 1200, "games_played": 0, "wins": 0, "losses": 0, "draws": 0,
        "friends": [], "achievements": [], "preferences": {}
    }
    response = requests.post(f"{BASE_URL}/profiles/", headers=headers, json=payload)
    assert response.status_code == 403


@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_update_other_user_profile_forbidden():
    """Tests attempting to update another user's profile."""
    headers = get_auth_headers(USER1_TOKEN)
    other_user_uid = f"other-profile-uid-{uuid.uuid4().hex}"
    update_payload = {"display_name": "Hacker"}
    response = requests.patch(f"{BASE_URL}/profiles/{other_user_uid}", headers=headers, json=update_payload)
    assert response.status_code == 403


@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_add_achievement_other_user_forbidden():
    """Tests attempting to add an achievement to another user's profile."""
    headers = get_auth_headers(USER1_TOKEN)
    other_user_uid = f"other-achieve-uid-{uuid.uuid4().hex}"
    achievement_id = "hack_achievement"
    response = requests.post(f"{BASE_URL}/profiles/{other_user_uid}/achievements/{achievement_id}", headers=headers)
    # This route doesn't expect a body, so 403 is the correct expectation
    assert response.status_code == 403


@pytest.mark.skipif(not config_present, reason="Requires TEST_USER1_BACKEND_TOKEN and TEST_USER1_UID")
def test_api_get_non_existent_profile():
    """Tests getting a profile that definitely does not exist."""
    headers = get_auth_headers(USER1_TOKEN)
    non_existent_uid = f"non-existent-uid-{uuid.uuid4().hex}"
    response = requests.get(f"{BASE_URL}/profiles/{non_existent_uid}", headers=headers)
    assert response.status_code == 404
