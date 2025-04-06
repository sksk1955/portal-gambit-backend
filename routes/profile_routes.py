from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status  # Import status

from models.user_profile import UserProfile
from schemas.auth_schemas import TokenData
from schemas.profile_schemas import (
    ProfileUpdate,
    ProfileResponse,
    LeaderboardParams,
    SearchProfilesParams
)
from services.profile_service import ProfileService
from utils.dependencies import get_current_user, get_profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("/", response_model=ProfileResponse,
             status_code=status.HTTP_201_CREATED)  # Use 201 for successful creation
async def create_profile(
        profile: UserProfile,
        current_user: TokenData = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
):
    """Create a new user profile."""
    if profile.uid != current_user.uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create profile for another user")

    # Check if profile already exists? BaseService.set will overwrite, maybe check first?
    existing_profile = await profile_service.get_profile(profile.uid)
    if existing_profile:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists for this user")

    success = await profile_service.create_profile(profile)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create profile in database")

    return ProfileResponse(
        status="success",
        message="Profile created successfully"
    )


@router.get("/{uid}", response_model=UserProfile)
async def get_profile(
        uid: str,
        current_user: TokenData = Depends(get_current_user),  # Keep auth for now, maybe public later?
        profile_service: ProfileService = Depends(get_profile_service)
):
    """Get a user profile by UID."""
    profile = await profile_service.get_profile(uid)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.patch("/{uid}", response_model=ProfileResponse)
async def update_profile(
        uid: str,
        updates: ProfileUpdate,
        current_user: TokenData = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
):
    """Update a user profile."""
    if uid != current_user.uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another user's profile")

    # FIX: Use model_dump() instead of dict()
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:  # Prevent empty updates if needed
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    success = await profile_service.update_profile(uid, update_data)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to update profile in database")

    return ProfileResponse(
        status="success",
        message="Profile updated successfully"
    )


@router.get("/search/{username_prefix}", response_model=List[UserProfile])
async def search_profiles(
        username_prefix: str,
        params: SearchProfilesParams = Depends(),
        current_user: TokenData = Depends(get_current_user),  # Auth needed?
        profile_service: ProfileService = Depends(get_profile_service)
):
    """Search for profiles by username prefix."""
    if not username_prefix or len(username_prefix) < 1:  # Add basic validation
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username prefix must be at least 1 character")
    return await profile_service.search_profiles(username_prefix, params.limit)


@router.get("/leaderboard/top", response_model=List[UserProfile])
async def get_leaderboard(
        params: LeaderboardParams = Depends(),
        current_user: TokenData = Depends(get_current_user),  # Auth needed?
        profile_service: ProfileService = Depends(get_profile_service)
):
    """Get the top rated players."""
    return await profile_service.get_leaderboard(params.limit)


@router.post("/{uid}/achievements/{achievement_id}", response_model=ProfileResponse)
async def add_achievement(
        uid: str = Path(..., description="User ID"),
        achievement_id: str = Path(..., description="Achievement ID to add"),
        current_user: TokenData = Depends(get_current_user),
        profile_service: ProfileService = Depends(get_profile_service)
):
    """Add an achievement to a user's profile."""
    if uid != current_user.uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another user's achievements")

    # Consider validating achievement_id format or against a predefined list
    if not achievement_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Achievement ID cannot be empty")

    success = await profile_service.add_achievement(uid, achievement_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add achievement")

    return ProfileResponse(
        status="success",
        message="Achievement added successfully"
    )
