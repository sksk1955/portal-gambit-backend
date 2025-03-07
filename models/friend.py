from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class FriendRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class FriendRequest(BaseModel):
    request_id: str = Field(..., description="Unique request identifier")
    sender_id: str = Field(..., description="UID of the request sender")
    receiver_id: str = Field(..., description="UID of the request receiver")
    status: FriendRequestStatus = Field(default=FriendRequestStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
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
    became_friends: datetime = Field(default_factory=datetime.utcnow)
    games_played: int = Field(default=0)
    last_game: Optional[str] = None  # Reference to last game_id
    last_interaction: datetime = Field(default_factory=datetime.utcnow) 