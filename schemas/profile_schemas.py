from pydantic import BaseModel
from typing import Dict, Any, Optional

class ProfileUpdate(BaseModel):
    """Schema for profile update request."""
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class ProfileResponse(BaseModel):
    """Schema for generic profile operation response."""
    status: str
    message: Optional[str] = None

class LeaderboardParams(BaseModel):
    """Schema for leaderboard query parameters."""
    limit: int = 100

class SearchProfilesParams(BaseModel):
    """Schema for profile search parameters."""
    username_prefix: str
    limit: int = 10

class AchievementParams(BaseModel):
    """Schema for achievement parameters."""
    achievement_id: str 