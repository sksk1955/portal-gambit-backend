from pydantic import BaseModel
from typing import Optional

class FriendRequestCreate(BaseModel):
    """Schema for creating a friend request."""
    receiver_id: str
    message: Optional[str] = None

class FriendRequestResponse(BaseModel):
    """Schema for friend request response."""
    request_id: str
    accept: bool

class FriendResponse(BaseModel):
    """Schema for generic friend operation response."""
    status: str
    message: Optional[str] = None

class FriendInteractionUpdate(BaseModel):
    """Schema for updating friend interaction."""
    game_id: Optional[str] = None 