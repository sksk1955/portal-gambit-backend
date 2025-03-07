from fastapi import Header, HTTPException, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials, firestore
from typing import Optional
from config.firebase_config import initialize_firebase
from services.profile_service import ProfileService
from services.friend_service import FriendService
from services.history_service import HistoryService
from services.analytics_service import AnalyticsService
from utils.jwt_utils import verify_token
from schemas.auth_schemas import TokenData

# Initialize Firebase and get Firestore client
db_client = initialize_firebase()

# Initialize services
profile_service = ProfileService(db_client)
friend_service = FriendService(db_client)
history_service = HistoryService(db_client)
analytics_service = AnalyticsService(db_client)

# Security scheme
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenData:
    """Verify JWT token and return user data."""
    try:
        payload = verify_token(credentials.credentials)
        return TokenData(
            uid=payload["uid"],
            email=payload.get("email"),
            email_verified=payload.get("email_verified", False)
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

def get_profile_service() -> ProfileService:
    """Dependency for profile service."""
    return profile_service

def get_friend_service() -> FriendService:
    """Dependency for friend service."""
    return friend_service

def get_history_service() -> HistoryService:
    """Dependency for history service."""
    return history_service

def get_analytics_service() -> AnalyticsService:
    """Dependency for analytics service."""
    return analytics_service 