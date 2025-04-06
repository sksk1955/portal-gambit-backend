import os
import time
import uuid

import pytest
import requests

# --- Test Configuration ---
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080").rstrip('/')
# Increased delay slightly to potentially help with consistency issues
API_DELAY = float(os.getenv("TEST_API_DELAY", "1.5"))

USER1_TOKEN = os.getenv("TEST_USER1_BACKEND_TOKEN")
USER1_UID = os.getenv("TEST_USER1_UID")
USER2_TOKEN = os.getenv("TEST_USER2_BACKEND_TOKEN")
USER2_UID = os.getenv("TEST_USER2_UID")

config_present = USER1_TOKEN and USER1_UID and USER2_TOKEN and USER2_UID
if not config_present:
    print(
        "\nWARNING: Missing environment variables for friend flow tests (TEST_USER1/2_BACKEND_TOKEN, "
        "TEST_USER1/2_UID). Tests will be skipped.")


def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


pending_request_id = None  # Keep track of request ID across tests


def poll_for_condition(check_function, expected_value, max_attempts=5, delay=1.0):
    """
    Polls a check_function until it returns the expected_value or times out.

    Args:
        check_function: A callable that performs the check and returns a value.
        expected_value: The value we expect check_function to return.
        max_attempts: Maximum number of times to try.
        delay: Seconds to wait between attempts.

    Returns:
        True if the condition was met within max_attempts, False otherwise.
    """
    for attempt in range(max_attempts):
        try:
            result = check_function()
            if result == expected_value:
                print(f"Polling successful on attempt {attempt + 1}.")
                return True
        except Exception as e:
            print(f"Polling check function raised an exception: {e}")
            # Decide if you want to retry on exceptions or fail immediately
            # For now, we'll just print and continue polling

        # Avoid printing the last "waiting" message if it's the final attempt
        if attempt < max_attempts - 1:
            print(f"Polling attempt {attempt + 1}/{max_attempts} failed, waiting {delay}s...")
            time.sleep(delay)
        else:
            print(f"Polling failed on final attempt {attempt + 1}/{max_attempts}.")

    return False


# Fixture to clean up *after* tests run
@pytest.fixture(scope="module", autouse=True)
def cleanup_friendship():
    yield  # Run tests first
    if not config_present:
        return
    print("\n--- Post-module Cleanup: Removing Friend State ---")
    headers1 = get_auth_headers(USER1_TOKEN)
    headers2 = get_auth_headers(USER2_TOKEN)

    # Attempt to reject any pending requests from User1 to User2 first
    try:
        pending_resp = requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers2)
        if pending_resp.status_code == 200:
            pending_reqs = pending_resp.json()
            for req in pending_reqs:
                if req.get("sender_id") == USER1_UID:
                    req_id = req["request_id"]
                    print(f"Cleanup: User2 rejecting pending request {req_id} from User1...")
                    reject_resp = requests.post(f"{BASE_URL}/friends/requests/{req_id}/respond", headers=headers2,
                                                json={"accept": False})
                    print(f"  Reject response status: {reject_resp.status_code}")
                    time.sleep(0.2)  # Small delay between actions
    except Exception as e:
        print(f"Cleanup Warning: Error checking/rejecting pending requests: {e}")

    # Remove friendship status
    remove_resp1 = requests.delete(f"{BASE_URL}/friends/{USER2_UID}", headers=headers1)
    print(f"Cleanup: User1 remove User2 -> Status {remove_resp1.status_code}")
    time.sleep(0.2)
    remove_resp2 = requests.delete(f"{BASE_URL}/friends/{USER1_UID}", headers=headers2)
    print(f"Cleanup: User2 remove User1 -> Status {remove_resp2.status_code}")
    print("--- Cleanup Complete ---")


# Helper to ensure clean state *before* a specific test
def ensure_not_friends_or_pending(headers1, headers2, user1_uid, user2_uid):
    print(f"\nPre-test Check: Ensuring {user1_uid} and {user2_uid} are not friends/pending...")
    # Check if friends and remove
    resp1_list = requests.get(f"{BASE_URL}/friends/list", headers=headers1)
    if resp1_list.status_code == 200 and any(f["friend_id"] == user2_uid for f in resp1_list.json()):
        print(f"  Pre-check: Found friendship (U1->U2), removing...")
        requests.delete(f"{BASE_URL}/friends/{user2_uid}", headers=headers1)
        time.sleep(API_DELAY / 2)  # Allow time for removal
    resp2_list = requests.get(f"{BASE_URL}/friends/list", headers=headers2)
    if resp2_list.status_code == 200 and any(f["friend_id"] == user1_uid for f in resp2_list.json()):
        print(f"  Pre-check: Found friendship (U2->U1), removing...")
        requests.delete(f"{BASE_URL}/friends/{user1_uid}", headers=headers2)
        time.sleep(API_DELAY / 2)

    # Check pending requests and reject
    pending_resp = requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers2)
    if pending_resp.status_code == 200:
        req_to_reject = next((r for r in pending_resp.json() if r.get("sender_id") == user1_uid), None)
        if req_to_reject:
            req_id = req_to_reject['request_id']
            print(f"  Pre-check: Found pending request {req_id}, rejecting...")
            requests.post(f"{BASE_URL}/friends/requests/{req_id}/respond", headers=headers2, json={"accept": False})
            time.sleep(API_DELAY / 2)
    print("Pre-test Check: State should be clean.")


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_initial_friend_list_empty():
    headers1 = get_auth_headers(USER1_TOKEN)
    headers2 = get_auth_headers(USER2_TOKEN)
    ensure_not_friends_or_pending(headers1, headers2, USER1_UID, USER2_UID)
    time.sleep(API_DELAY)
    resp1 = requests.get(f"{BASE_URL}/friends/list", headers=headers1)
    assert resp1.status_code == 200, f"Failed to get User1 friends: {resp1.text}"
    friends1 = resp1.json()
    assert not any(
        f["friend_id"] == USER2_UID for f in friends1), f"User2 found in User1's list unexpectedly: {friends1}"

    resp2 = requests.get(f"{BASE_URL}/friends/list", headers=headers2)
    assert resp2.status_code == 200
    friends2 = resp2.json()
    assert not any(
        f["friend_id"] == USER1_UID for f in friends2), f"User1 found in User2's list unexpectedly: {friends2}"


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_send_friend_request():
    global pending_request_id
    headers1 = get_auth_headers(USER1_TOKEN)
    headers2 = get_auth_headers(USER2_TOKEN)

    # Ensure clean state before sending
    ensure_not_friends_or_pending(headers1, headers2, USER1_UID, USER2_UID)
    time.sleep(API_DELAY)  # Wait after potential cleanup

    payload = {
        "receiver_id": USER2_UID,
        "message": f"Hello from blackbox test! {uuid.uuid4().hex[:6]}"
    }
    response = requests.post(f"{BASE_URL}/friends/requests", headers=headers1, json=payload)

    # Assert the request *itself* succeeded, regardless of business logic outcome initially
    assert response.status_code == 200, f"POST /friends/requests failed (expected 200): {response.status_code} - {response.text}"
    data = response.json()
    assert data.get("status") == "success", f"Expected status 'success', got: {data}"

    # Assert business logic success *specifically*
    data = response.json()
    assert data.get(
        "status") == "success", f"Expected status 'success', got: {data}"  # FIX: This is the core assertion that failed

    print(f"Send request response: {response.status_code} -> {data}")

    time.sleep(API_DELAY)
    pending_resp = requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers2)
    assert pending_resp.status_code == 200
    pending_reqs = pending_resp.json()
    assert isinstance(pending_reqs, list)
    found_req = next((req for req in pending_resp.json() if req.get("sender_id") == USER1_UID), None)
    assert found_req is not None
    pending_request_id = found_req["request_id"]
    print(f"\nStored pending request ID: {pending_request_id}")


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs")
def test_api_accept_and_interact():
    """User2 accepts the friend request, then User1 updates interaction."""
    global pending_request_id
    # FIX: Attempt to send request if ID is missing
    if pending_request_id is None:
        print("pending_request_id not set in test_api_accept_and_interact, attempting to send request...")
        # Ensure clean state before attempting to send
        headers1_fix = get_auth_headers(USER1_TOKEN)
        headers2_fix = get_auth_headers(USER2_TOKEN)
        ensure_not_friends_or_pending(headers1_fix, headers2_fix, USER1_UID, USER2_UID)
        time.sleep(API_DELAY)
        test_api_send_friend_request()  # Call the send function to set the ID
        assert pending_request_id is not None, "Failed to get pending_request_id even after retry in accept test."
        print(f"Obtained pending_request_id: {pending_request_id}")
        time.sleep(API_DELAY)  # Allow time for request to be processed

    # --- Step 1: User2 Accepts Request ---
    print(f"\nAccepting request ID: {pending_request_id}")
    headers2 = get_auth_headers(USER2_TOKEN)
    headers1 = get_auth_headers(USER1_TOKEN)
    response_accept = requests.post(f"{BASE_URL}/friends/requests/{pending_request_id}/respond", headers=headers2,
                                    json={"accept": True})
    # Rest of the test remains the same...
    assert response_accept.status_code == 200, f"Accept request failed: {response_accept.text}"
    data_accept = response_accept.json()
    assert data_accept.get("status") == "success"
    assert "accepted successfully" in data_accept.get("message", "")

    # Allow time for friend status creation
    print("Waiting for friendship creation...")
    time.sleep(API_DELAY * 2)  # Increase delay slightly just in case

    # --- Step 2: Verify Friendship ---
    print("Polling for friendship confirmation...")
    # FIX: Increase polling time/attempts
    poll_delay = API_DELAY * 1.5  # Slightly longer delay between checks
    max_attempts = 8  # More attempts

    # Poll U1 list
    poll_u1 = poll_for_condition(
        lambda: any(
            f["friend_id"] == USER2_UID for f in requests.get(f"{BASE_URL}/friends/list", headers=headers1).json()),
        expected_value=True, delay=poll_delay, max_attempts=max_attempts
    )
    assert poll_u1, "User2 never appeared in User1's friend list after polling."

    # Poll U2 list
    poll_u2 = poll_for_condition(
        lambda: any(
            f["friend_id"] == USER1_UID for f in requests.get(f"{BASE_URL}/friends/list", headers=headers2).json()),
        expected_value=True, delay=poll_delay, max_attempts=max_attempts
    )
    assert poll_u2, "User1 never appeared in User2's friend list after polling."
    print("Friendship confirmed via polling.")

    # --- Step 3: User1 Updates Interaction ---
    print(f"Updating interaction for friend: {USER2_UID}")
    headers1_interact = get_auth_headers(USER1_TOKEN)
    game_id = f"bb_game_{uuid.uuid4().hex[:8]}"
    payload_interact = {
        "game_id": game_id
    }
    response_interact = requests.post(f"{BASE_URL}/friends/{USER2_UID}/interactions", headers=headers1_interact,
                                      json=payload_interact)

    assert response_interact.status_code == 200, f"Update interaction failed: {response_interact.text}"
    data_interact = response_interact.json()
    assert data_interact.get("status") == "success"
    print("Interaction update successful.")

    # --- Step 4: Verify Interaction Update (Optional) ---
    time.sleep(API_DELAY)
    resp1_list_final = requests.get(f"{BASE_URL}/friends/list", headers=headers1_interact)
    assert resp1_list_final.status_code == 200
    friends1_final = resp1_list_final.json()
    friend_status_final = next((f for f in friends1_final if f.get("friend_id") == USER2_UID), None)

    assert friend_status_final is not None, f"Friend status for {USER2_UID} not found in final check."
    assert friend_status_final.get("last_game") == game_id


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_remove_friend():
    """User1 removes User2 as a friend."""
    # This assumes they might be friends from the accept_and_interact test
    headers1 = get_auth_headers(USER1_TOKEN)
    headers2 = get_auth_headers(USER2_TOKEN)

    # Ensure they are friends first (maybe redundant if accept test runs before)
    resp1_list_pre = requests.get(f"{BASE_URL}/friends/list", headers=headers1)
    if resp1_list_pre.status_code != 200 or not any(f["friend_id"] == USER2_UID for f in resp1_list_pre.json()):
        print("Pre-remove check: Users not friends, attempting to accept request first (if any)...")
        test_api_accept_and_interact()  # Try to ensure they are friends
        time.sleep(API_DELAY)

    # Proceed with removal
    response = requests.delete(f"{BASE_URL}/friends/{USER2_UID}", headers=headers1)
    assert response.status_code == 200, f"Remove friend failed: {response.text}"
    data = response.json()
    assert data.get("status") == "success"

    time.sleep(API_DELAY)

    resp1_list = requests.get(f"{BASE_URL}/friends/list", headers=headers1)
    assert resp1_list.status_code == 200
    friends1 = resp1_list.json()
    assert not any(f["friend_id"] == USER2_UID for f in friends1), "User2 still in User1's list after remove"

    resp2_list = requests.get(f"{BASE_URL}/friends/list", headers=headers2)
    assert resp2_list.status_code == 200
    friends2 = resp2_list.json()
    assert not any(f["friend_id"] == USER1_UID for f in friends2), "User1 still in User2's list after remove"


# --- Negative and Edge Case Tests ---

@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_send_friend_request_to_self():
    headers1 = get_auth_headers(USER1_TOKEN)
    payload = {"receiver_id": USER1_UID}
    response = requests.post(f"{BASE_URL}/friends/requests", headers=headers1, json=payload)
    # Expect 400 or 409 if route logic is fixed, otherwise check status field
    # assert response.status_code in [400, 409]
    assert response.status_code == 409
    assert "Failed to send friend request" in response.json().get("detail", "")


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_send_duplicate_friend_request():
    headers1 = get_auth_headers(USER1_TOKEN)
    headers2 = get_auth_headers(USER2_TOKEN)
    ensure_not_friends_or_pending(headers1, headers2, USER1_UID, USER2_UID)

    # FIX: Add extra polling here to ensure the state allows sending
    print("Polling to confirm state allows sending friend request...")
    poll_delay = API_DELAY / 2  # Use smaller delay for this check

    # Check U2 has no pending from U1
    poll_p2_clear = poll_for_condition(
        lambda: not any(r.get("sender_id") == USER1_UID for r in
                        requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers2).json()),
        expected_value=True, delay=poll_delay, max_attempts=6
    )
    # Check U1 has no pending from U2 (less likely to interfere, but good practice)
    poll_p1_clear = poll_for_condition(
        lambda: not any(r.get("sender_id") == USER2_UID for r in
                        requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers1).json()),
        expected_value=True, delay=poll_delay, max_attempts=6
    )

    if not (poll_p1_clear and poll_p2_clear):
        pytest.fail("Polling failed to confirm clear pending request state before sending first request.")
    print("Confirmed state is clear via polling.")

    time.sleep(API_DELAY / 2)  # Short extra delay

    payload = {"receiver_id": USER2_UID, "message": "Duplicate request test"}
    print("Sending first request...")
    resp1 = requests.post(f"{BASE_URL}/friends/requests", headers=headers1, json=payload)
    assert resp1.status_code == 200, f"First request failed (expected 200): {resp1.status_code} - {resp1.text}"
    assert resp1.json().get("status") == "success"
    print("First request sent successfully.")

    # ... (rest of the test: poll for request ID, send duplicate, assert 409, cleanup) ...
    # (Polling for ID is already added in the previous fix for test_api_send_friend_request logic)
    first_req_id = None

    def check_pending_dup():
        pending_resp_check = requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers2)
        if pending_resp_check.status_code == 200:
            return next((r.get("request_id") for r in pending_resp_check.json() if r.get("sender_id") == USER1_UID),
                        None)
        return None

    if not poll_for_condition(lambda: check_pending_dup() is not None, expected_value=True):
        print("Warning: Could not confirm first request appeared via polling for cleanup ID.")
    else:
        first_req_id = check_pending_dup()
        print(f"Obtained ID of first request for potential cleanup: {first_req_id}")

    # Send duplicate
    print("Sending duplicate request...")
    resp2 = requests.post(f"{BASE_URL}/friends/requests", headers=headers1, json=payload)
    assert resp2.status_code == 409, f"Duplicate request did not fail with 409: {resp2.status_code} - {resp2.text}"
    assert "Failed to send friend request" in resp2.json().get("detail", "")
    print("Duplicate request correctly failed with 409.")

    # Cleanup the first pending request if its ID was found
    if first_req_id:
        print(f"Cleaning up first request: {first_req_id}")
        reject_resp = requests.post(f"{BASE_URL}/friends/requests/{first_req_id}/respond",
                                    headers=headers2, json={"accept": False})
        print(f"  Cleanup reject status: {reject_resp.status_code}")
        assert reject_resp.status_code == 200  # Ensure cleanup worked
    else:
        print("Skipping cleanup as first request ID was not found.")


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_respond_to_non_existent_request():
    headers2 = get_auth_headers(USER2_TOKEN)
    non_existent_req_id = f"req_fake_{uuid.uuid4().hex}"
    response = requests.post(f"{BASE_URL}/friends/requests/{non_existent_req_id}/respond", headers=headers2,
                             json={"accept": True})
    assert response.status_code == 404


@pytest.mark.skipif(not config_present, reason="Requires tokens/UIDs for two users")
def test_api_respond_to_request_not_for_user():
    headers1 = get_auth_headers(USER1_TOKEN)
    headers2 = get_auth_headers(USER2_TOKEN)
    # Ensure clean state
    ensure_not_friends_or_pending(headers1, headers2, USER1_UID, USER2_UID)
    time.sleep(API_DELAY)

    payload1 = {"receiver_id": USER2_UID, "message": "Request for User2"}
    resp_send = requests.post(f"{BASE_URL}/friends/requests", headers=headers1, json=payload1)
    assert resp_send.status_code == 200, f"Send request failed (expected 200): {resp_send.status_code} - {resp_send.text}"
    assert resp_send.json().get("status") == "success"

    time.sleep(API_DELAY)

    pending_resp = requests.get(f"{BASE_URL}/friends/requests/pending", headers=headers2)
    assert pending_resp.status_code == 200
    req_for_u2 = next((r for r in pending_resp.json() if r.get("sender_id") == USER1_UID), None)
    assert req_for_u2 is not None, "Failed to find request for User2"
    req_id = req_for_u2["request_id"]

    # User1 (sender) tries to respond - should fail
    response = requests.post(f"{BASE_URL}/friends/requests/{req_id}/respond", headers=headers1,
                             json={"accept": True})
    assert response.status_code == 403

    # Cleanup: User2 rejects the request
    reject_resp = requests.post(f"{BASE_URL}/friends/requests/{req_id}/respond", headers=headers2,
                                json={"accept": False})
    print(f"\nCleanup: User2 rejected request {req_id} -> Status {reject_resp.status_code}")
