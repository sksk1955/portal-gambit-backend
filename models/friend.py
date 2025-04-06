from datetime import datetime, timezone  # Import timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FriendRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class FriendRequest(BaseModel):
    request_id: str = Field(..., description="Unique request identifier")
    sender_id: str = Field(..., description="UID of the request sender")
    receiver_id: str = Field(..., description="UID of the request receiver")
    status: FriendRequestStatus = Field(default=FriendRequestStatus.PENDING)
    # FIX: Use datetime.now(timezone.utc) for default factory
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req123",
                "sender_id": "user1",
                "receiver_id": "user2",
                "status": "pending",
                "message": "Let's play some chess!"
            }
        }


class FriendStatus(BaseModel):
    user_id: str
    friend_id: str
    # FIX: Use datetime.now(timezone.utc) for default factory
    became_friends: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    games_played: int = Field(default=0)
    last_game: Optional[str] = None  # Reference to last game_id
    # FIX: Use datetime.now(timezone.utc) for default factory
    last_interaction: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
