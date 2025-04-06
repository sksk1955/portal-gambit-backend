# Filename: tests/conftest.py
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.auth_middleware import FirebaseAuthMiddleware  # Import middleware
# Import models/schemas...
from models.friend import FriendRequest, FriendStatus, FriendRequestStatus
from models.game_history import GameHistory, GameResult
from models.user_profile import UserProfile
# Import the original app instance AND the routers separately
from routes import profile_routes, friend_routes, history_routes, analytics_routes, auth_routes
from schemas.analytics_schemas import DailyStats, PlayerPerformance, GlobalStats
from schemas.auth_schemas import TokenData
from schemas.history_schemas import OpeningStats, UserGameStats
from services.analytics_service import AnalyticsService
from services.friend_service import FriendService
from services.history_service import HistoryService
from services.profile_service import ProfileService
from utils import dependencies

load_dotenv()


# --- Test Data Fixtures --- (Keep these as they are) ---
@pytest.fixture(scope="session")
def test_user_1_uid() -> str:
    return os.getenv("TEST_USER1_UID_FIXTURE", "fixture-user-1-uid")

@pytest.fixture(scope="session")
def test_user_2_uid() -> str:
    return os.getenv("TEST_USER2_UID_FIXTURE", "fixture-user-2-uid")

@pytest.fixture
def test_user_1_token_data(test_user_1_uid) -> TokenData:
    return TokenData(
        uid=test_user_1_uid,
        email="test1@example.com",
        email_verified=True
    )


# ... (keep sample_user_profile, sample_game_history, etc.) ...
@pytest.fixture
def sample_user_profile(test_user_1_uid, test_user_2_uid) -> UserProfile:
    """Provides a sample UserProfile object."""
    return UserProfile(
        uid=test_user_1_uid,
        username=f"testuser_{uuid.uuid4().hex[:6]}",
        email="test1@example.com",
        display_name="Test User One",
        avatar_url="http://example.com/avatar.png",
        rating=1250,
        games_played=10,
        wins=5,
        losses=3,
        draws=2,
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
        last_active=datetime.now(timezone.utc) - timedelta(hours=1),
        friends=[test_user_2_uid],  # Reference the other test user
        achievements=["first_win", "portal_master"],
        preferences={"theme": "dark", "sound": True}
    )


@pytest.fixture
def sample_game_history(test_user_1_uid, test_user_2_uid) -> GameHistory:
    """Provides a sample GameHistory object."""
    now = datetime.now(timezone.utc)
    return GameHistory(
        game_id=f"game_{uuid.uuid4().hex}",
        white_player_id=test_user_1_uid,
        black_player_id=test_user_2_uid,
        start_time=now - timedelta(minutes=15),
        end_time=now - timedelta(minutes=2),
        result=GameResult.WHITE_WIN,
        winner_id=test_user_1_uid,
        moves=["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Bxc6", "dxc6", "O-O"],  # Example
        initial_position="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        white_rating=1250,
        black_rating=1230,
        rating_change={"white": 8, "black": -8},
        game_type="portal_gambit",
        time_control={"initial": 600, "increment": 5}
    )


@pytest.fixture
def sample_friend_request(test_user_1_uid, test_user_2_uid) -> FriendRequest:
    """Provides a sample pending FriendRequest object."""
    return FriendRequest(
        request_id=f"req_{uuid.uuid4().hex}",
        sender_id=test_user_2_uid,  # User 2 sent to User 1
        receiver_id=test_user_1_uid,
        status=FriendRequestStatus.PENDING,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        updated_at=datetime.now(timezone.utc) - timedelta(days=1),
        message="Wanna be friends and test portals?"
    )


@pytest.fixture
def sample_friend_status(test_user_1_uid, test_user_2_uid, sample_game_history) -> FriendStatus:
    """Provides a sample FriendStatus object."""
    return FriendStatus(
        user_id=test_user_1_uid,
        friend_id=test_user_2_uid,
        became_friends=datetime.now(timezone.utc) - timedelta(days=2),
        games_played=1,
        last_game=sample_game_history.game_id,
        last_interaction=sample_game_history.end_time
    )


# --- Mocking Fixtures (Firebase init, token verify - keep as is) ---
@pytest.fixture(scope="session", autouse=True)
def mock_firebase_admin_init():
    try:
        import firebase_admin
        if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            print("Firebase Admin already initialized, skipping init mock patch.")
            yield None
            return
    except ImportError:
        pass
    with patch("firebase_admin.initialize_app") as mock_init:
        print("Firebase Admin Initialized (Mocked via Patch)")
        yield mock_init

@pytest.fixture
def mock_verify_firebase_token():
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.return_value = {
            "uid": "mock_firebase_uid_from_token", "email": "firebase_user@example.com", "email_verified": True,
            "name": "Firebase Mock User", "picture": "http://example.com/firebase_pic.jpg",
            "iss": "https://securetoken.google.com/your-project-id", "aud": "your-project-id",
            "auth_time": int(time.time()) - 300, "user_id": "mock_firebase_uid_from_token",
            "sub": "mock_firebase_uid_from_token", "iat": int(time.time()) - 300, "exp": int(time.time()) + 3600,
            "firebase": {"identities": {"email": ["firebase_user@example.com"]}, "sign_in_provider": "password"}
        }
        yield mock_verify


# --- Mock Services (Keep as is) ---
@pytest.fixture
def mock_analytics_service(test_user_1_uid, test_user_2_uid):
    service = MagicMock(spec=AnalyticsService)
    service.record_game_analytics = AsyncMock(return_value=True)
    service.get_daily_stats = AsyncMock(
        return_value=DailyStats(total_games=7, average_duration=410.2, average_moves=51.8, white_wins=3, black_wins=3,
                                draws=1, abandoned=0, game_types={"portal_gambit": 7},
                                time_controls={"600/5": 4, "300/3": 3}))
    service.get_player_performance = AsyncMock(return_value=PlayerPerformance(
        rating_progression=[{"timestamp": datetime.now(timezone.utc) - timedelta(days=2), "rating_change": 8},
                            {"timestamp": datetime.now(timezone.utc) - timedelta(days=1), "rating_change": -6}],
        average_game_duration=450.0, preferred_time_control="600/5", preferred_game_type="portal_gambit", win_rate=0.5,
        performance_by_color={"white": {"games": 4, "wins": 2}, "black": {"games": 3, "wins": 1}},
        average_moves_per_game=55.0))
    service.get_global_stats = AsyncMock(
        return_value=GlobalStats(total_games=1500, white_win_rate=0.475, average_game_duration=430.0,
                                 average_moves_per_game=53.5, popular_time_controls={"600/5": 700, "900/10": 300},
                                 popular_game_types={"portal_gambit": 1450, "standard": 50},
                                 last_updated=datetime.now(timezone.utc) - timedelta(minutes=30)))
    return service

@pytest.fixture
def mock_friend_service(sample_friend_request, sample_friend_status, test_user_1_uid, test_user_2_uid):
    service = MagicMock(spec=FriendService)
    service.send_friend_request = AsyncMock(return_value=True)
    service.get_pending_requests = AsyncMock(return_value=[sample_friend_request])
    service.get_friend_request = AsyncMock(return_value=sample_friend_request)
    service.respond_to_request = AsyncMock(return_value=True)
    service.get_friends = AsyncMock(return_value=[sample_friend_status])
    service.remove_friend = AsyncMock(return_value=True)
    service.update_last_interaction = AsyncMock(return_value=True)
    return service

@pytest.fixture
def mock_history_service(sample_game_history, test_user_1_uid, test_user_2_uid):
    service = MagicMock(spec=HistoryService)
    service.archive_game = AsyncMock(return_value=True)
    service.get_game = AsyncMock(return_value=sample_game_history)
    service.get_user_games = AsyncMock(return_value=[sample_game_history])
    service.get_games_between_players = AsyncMock(return_value=[sample_game_history])
    service.get_user_stats = AsyncMock(
        return_value=UserGameStats(total_games=12, wins=6, losses=4, draws=2, white_games=6, black_games=6,
                                   rating_change=15, average_game_length=510.0, total_moves=612))
    service.get_popular_openings = AsyncMock(return_value=[OpeningStats(moves="e4 c5 Nf3", count=120, wins=65)])
    return service

@pytest.fixture
def mock_profile_service(sample_user_profile, test_user_1_uid):
    service = MagicMock(spec=ProfileService)
    service.create_profile = AsyncMock(return_value=True)
    service.get_profile = AsyncMock(return_value=sample_user_profile)
    service.update_profile = AsyncMock(return_value=True)
    service.search_profiles = AsyncMock(return_value=[sample_user_profile])
    service.get_leaderboard = AsyncMock(return_value=[sample_user_profile])
    service.add_achievement = AsyncMock(return_value=True)
    service.update_rating = AsyncMock(return_value=True)
    return service


# --- Mock Firestore Client (Keep revised version without specs for Firestore types) ---
@pytest.fixture
def mock_firestore_increment():
    with patch('firebase_admin.firestore.Increment', spec=True) as MockIncrement:
        yield MockIncrement

@pytest.fixture
def mock_firestore_array_union():
    with patch('firebase_admin.firestore.ArrayUnion', spec=True) as MockArrayUnion:
        yield MockArrayUnion

@pytest.fixture
def mock_db_client(mock_firestore_increment, mock_firestore_array_union):
    # Mocks without specs for Firestore types, AsyncMock for methods
    doc_snapshot_mock = MagicMock()
    doc_snapshot_mock.exists = True
    doc_snapshot_mock.to_dict.return_value = {"mock_field": "mock_value_from_db"}
    doc_snapshot_mock.id = "mock_doc_id"
    doc_ref_mock = MagicMock()
    doc_ref_mock.get = AsyncMock(return_value=doc_snapshot_mock)
    doc_ref_mock.set = AsyncMock(return_value=None)
    doc_ref_mock.update = AsyncMock(return_value=None)
    doc_ref_mock.delete = AsyncMock(return_value=None)
    query_mock = MagicMock()
    query_mock.where.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.limit.return_value = query_mock

    async def mock_stream_gen(*args, **kwargs):
        snap = MagicMock()
        snap.exists = True
        snap.to_dict.return_value = {"mock_query_field": "mock_query_value"}
        snap.id = "mock_query_doc_id"
        yield snap

    query_mock.stream = mock_stream_gen
    collection_ref_mock = MagicMock()
    collection_ref_mock.document = MagicMock(return_value=doc_ref_mock)
    collection_ref_mock.where.return_value = query_mock
    collection_ref_mock.order_by.return_value = query_mock
    collection_ref_mock.limit.return_value = query_mock
    collection_ref_mock.stream = mock_stream_gen
    db_mock = MagicMock()
    db_mock.collection = MagicMock(return_value=collection_ref_mock)
    yield db_mock


# --- Test Client Fixtures ---

@pytest.fixture(scope="function")  # Use function scope to ensure clean app state per test
def app_instance_for_test():
    """Creates a fresh FastAPI app instance for testing."""
    app = FastAPI()
    # Include routers
    app.include_router(profile_routes.router)
    app.include_router(friend_routes.router)
    app.include_router(history_routes.router)
    app.include_router(analytics_routes.router)
    app.include_router(auth_routes.router)
    return app


@pytest.fixture
def client(
        app_instance_for_test,  # Use the fresh app instance
        test_user_1_token_data,
        mock_analytics_service,
        mock_friend_service,
        mock_history_service,
        mock_profile_service,
):
    """
    Provides a TestClient using a temporary app instance WHERE:
    - Auth middleware is NOT added.
    - get_current_user dependency IS overridden.
    - Service dependencies ARE overridden.
    """
    app = app_instance_for_test  # Get the fresh app

    # Apply overrides directly to the app instance
    app.dependency_overrides[dependencies.get_analytics_service] = lambda: mock_analytics_service
    app.dependency_overrides[dependencies.get_friend_service] = lambda: mock_friend_service
    app.dependency_overrides[dependencies.get_history_service] = lambda: mock_history_service
    app.dependency_overrides[dependencies.get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[dependencies.get_current_user] = lambda: test_user_1_token_data

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides (important with function-scoped app)
    app.dependency_overrides = {}


@pytest.fixture
def client_no_auth_bypass(
        app_instance_for_test,  # Use the fresh app instance
        mock_analytics_service,
        mock_friend_service,
        mock_history_service,
        mock_profile_service,
):
    """
    Provides a TestClient using a temporary app instance WHERE:
    - Auth middleware IS added.
    - get_current_user dependency is NOT overridden.
    - Service dependencies ARE overridden.
    """
    app = app_instance_for_test  # Get the fresh app

    # Apply service overrides
    app.dependency_overrides[dependencies.get_analytics_service] = lambda: mock_analytics_service
    app.dependency_overrides[dependencies.get_friend_service] = lambda: mock_friend_service
    app.dependency_overrides[dependencies.get_history_service] = lambda: mock_history_service
    app.dependency_overrides[dependencies.get_profile_service] = lambda: mock_profile_service

    # Add the *real* middleware to this test app instance
    excluded_paths = [r"^/$", r"^/docs$", r"^/openapi.json$", r"^/redoc$"]
    app.add_middleware(FirebaseAuthMiddleware, exclude_paths=excluded_paths)

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides = {}

# Remove the autouse=True override fixture if it still exists
# @pytest.fixture(autouse=True) def override_dependencies_in_app(...): pass
