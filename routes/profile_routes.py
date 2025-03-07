from fastapi import APIRouter, Depends, HTTPException
from typing import List
from models.user_profile import UserProfile
from schemas.profile_schemas import (
    ProfileUpdate,
    ProfileResponse,
    LeaderboardParams,
    SearchProfilesParams,
    AchievementParams
)
from schemas.auth_schemas import TokenData
from services.profile_service import ProfileService
from utils.dependencies import get_current_user, get_profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.post("/", response_model=ProfileResponse)
async def create_profile(
    profile: UserProfile,
    current_user: TokenData = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Create a new user profile."""
    if profile.uid != current_user.uid:
        raise HTTPException(status_code=403, detail="Cannot create profile for another user")
    success = await profile_service.create_profile(profile)
    return ProfileResponse(
        status="success" if success else "error",
        message="Profile created successfully" if success else "Failed to create profile"
    )

@router.get("/{uid}", response_model=UserProfile)
async def get_profile(
    uid: str,
    current_user: TokenData = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get a user profile by UID."""
    profile = await profile_service.get_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
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
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")
    
    success = await profile_service.update_profile(uid, updates.dict(exclude_unset=True))
    return ProfileResponse(
        status="success" if success else "error",
        message="Profile updated successfully" if success else "Failed to update profile"
    )

@router.get("/search/{username_prefix}", response_model=List[UserProfile])
async def search_profiles(
    username_prefix: str,
    params: SearchProfilesParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Search for profiles by username prefix."""
    return await profile_service.search_profiles(username_prefix, params.limit)

@router.get("/leaderboard/top", response_model=List[UserProfile])
async def get_leaderboard(
    params: LeaderboardParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Get the top rated players."""
    return await profile_service.get_leaderboard(params.limit)

@router.post("/{uid}/achievements/{achievement_id}", response_model=ProfileResponse)
async def add_achievement(
    uid: str,
    params: AchievementParams,
    current_user: TokenData = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service)
):
    """Add an achievement to a user's profile."""
    if uid != current_user.uid:
        raise HTTPException(status_code=403, detail="Cannot modify another user's achievements")
    
    success = await profile_service.add_achievement(uid, params.achievement_id)
    return ProfileResponse(
        status="success" if success else "error",
        message="Achievement added successfully" if success else "Failed to add achievement"
    ) 