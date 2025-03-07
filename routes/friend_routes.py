from fastapi import APIRouter, Depends, HTTPException
from typing import List
from models.friend import FriendRequest, FriendStatus
from schemas.friend_schemas import (
    FriendRequestCreate,
    FriendRequestResponse,
    FriendResponse,
    FriendInteractionUpdate
)
from schemas.auth_schemas import TokenData
from services.friend_service import FriendService
from utils.dependencies import get_current_user, get_friend_service

router = APIRouter(prefix="/friends", tags=["friends"])

@router.post("/requests", response_model=FriendResponse)
async def send_friend_request(
    request: FriendRequestCreate,
    current_user: TokenData = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Send a friend request to another user."""
    success = await friend_service.send_friend_request(
        sender_id=current_user.uid,
        receiver_id=request.receiver_id,
        message=request.message
    )
    return FriendResponse(
        status="success" if success else "error",
        message="Friend request sent successfully" if success else "Failed to send friend request"
    )

@router.get("/requests/pending", response_model=List[FriendRequest])
async def get_pending_requests(
    current_user: TokenData = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Get all pending friend requests for the current user."""
    return await friend_service.get_pending_requests(current_user.uid)

@router.post("/requests/{request_id}/respond", response_model=FriendResponse)
async def respond_to_request(
    request_id: str,
    response: FriendRequestResponse,
    current_user: TokenData = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Accept or reject a friend request."""
    request = await friend_service.get_friend_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    if request.receiver_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Cannot respond to requests for other users")
    
    success = await friend_service.respond_to_request(request_id, response.accept)
    return FriendResponse(
        status="success" if success else "error",
        message=f"Friend request {response.accept and 'accepted' or 'rejected'} successfully" if success else "Failed to respond to friend request"
    )

@router.get("/list", response_model=List[FriendStatus])
async def get_friends(
    current_user: TokenData = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Get all friends of the current user."""
    return await friend_service.get_friends(current_user.uid)

@router.delete("/{friend_id}", response_model=FriendResponse)
async def remove_friend(
    friend_id: str,
    current_user: TokenData = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Remove a friend."""
    success = await friend_service.remove_friend(current_user.uid, friend_id)
    return FriendResponse(
        status="success" if success else "error",
        message="Friend removed successfully" if success else "Failed to remove friend"
    )

@router.post("/{friend_id}/interactions", response_model=FriendResponse)
async def update_friend_interaction(
    friend_id: str,
    interaction: FriendInteractionUpdate,
    current_user: TokenData = Depends(get_current_user),
    friend_service: FriendService = Depends(get_friend_service)
):
    """Update the last interaction with a friend."""
    success = await friend_service.update_last_interaction(
        current_user.uid,
        friend_id,
        interaction.game_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update interaction")
    return FriendResponse(
        status="success",
        message="Interaction updated successfully"
    )