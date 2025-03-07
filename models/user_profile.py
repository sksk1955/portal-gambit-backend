from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UserProfile(BaseModel):
    uid: str = Field(..., description="Firebase User ID")
    username: str = Field(..., min_length=3, max_length=30)
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    rating: int = Field(default=1200, description="Chess rating")
    games_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    draws: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    friends: List[str] = Field(default_factory=list, description="List of friend UIDs")
    achievements: List[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "uid": "abc123",
                "username": "chessMaster",
                "email": "user@example.com",
                "display_name": "Chess Master",
                "rating": 1200,
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0
            }
        } 