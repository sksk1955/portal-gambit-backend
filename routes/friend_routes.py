from typing import List

from fastapi import APIRouter, Depends, HTTPException, status  # Import status

from models.friend import FriendRequest, FriendStatus
from schemas.auth_schemas import TokenData
from schemas.friend_schemas import (
    FriendRequestCreate,
    FriendResponse,
    FriendInteractionUpdate,
    FriendRequestAction
)
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
    # FIX: Return 409 Conflict if service layer failed (e.g., duplicate/already friends)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to send friend request (already friends or pending request exists)"
        )

    return FriendResponse(
        status="success",
        message="Friend request sent successfully"
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
        # Change the body parameter to use the new schema
        action: FriendRequestAction,
        current_user: TokenData = Depends(get_current_user),
        friend_service: FriendService = Depends(get_friend_service)
):
    """Accept or reject a friend request."""
    # ... (rest of the logic remains the same, use action.accept now)
    request_obj = await friend_service.get_friend_request(request_id)  # Renamed variable
    if not request_obj:
        raise HTTPException(status_code=404, detail="Friend request not found")

    if request_obj.receiver_id != current_user.uid:
        raise HTTPException(status_code=403, detail="Cannot respond to requests for other users")

    # Use action.accept here
    success = await friend_service.respond_to_request(request_id, action.accept)
    # Return 400 if service fails (e.g., request wasn't pending)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to respond to friend request (e.g., request not pending or db error)"
        )
    return FriendResponse(
        status="success",
        message=f"Friend request {action.accept and 'accepted' or 'rejected'} successfully"
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
    # Return 400 if service fails
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove friend (e.g., not friends or db error)"
        )
    return FriendResponse(
        status="success",
        message="Friend removed successfully"
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
    # FIX: Route already raises 400 on failure, which is correct. Keep as is.
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update interaction")
    return FriendResponse(
        status="success",
        message="Interaction updated successfully"
    )
