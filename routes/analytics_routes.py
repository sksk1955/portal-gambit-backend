from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from schemas.analytics_schemas import (
    GameAnalyticsCreate,
    DailyStats,
    PlayerPerformance,
    GlobalStats,
    AnalyticsResponse
)
from schemas.auth_schemas import TokenData
from services.analytics_service import AnalyticsService
from utils.dependencies import get_current_user, get_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/games/{game_id}", response_model=AnalyticsResponse)
async def record_game_analytics(
    game_id: str,
    game_data: GameAnalyticsCreate,
    current_user: TokenData = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Record analytics data for a completed game."""
    # Verify that the current user was a participant in the game
    if current_user.uid not in [game_data.white_player_id, game_data.black_player_id]:
        raise HTTPException(status_code=403, detail="Can only record analytics for games you participated in")
    
    game_dict = game_data.dict()
    game_dict['game_id'] = game_id
    success = await analytics_service.record_game_analytics(game_dict)
    return AnalyticsResponse(
        status="success" if success else "error",
        message="Game analytics recorded successfully" if success else "Failed to record game analytics"
    )

@router.get("/daily/{date}", response_model=DailyStats)
async def get_daily_stats(
    date: datetime,
    current_user: TokenData = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get aggregated statistics for a specific day."""
    return await analytics_service.get_daily_stats(date)

@router.get("/players/{user_id}/performance", response_model=PlayerPerformance)
async def get_player_performance(
    user_id: str,
    days: int = 30,
    current_user: TokenData = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get detailed performance analytics for a player."""
    return await analytics_service.get_player_performance(user_id, days)

@router.get("/global", response_model=GlobalStats)
async def get_global_stats(
    current_user: TokenData = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get global game statistics."""
    return await analytics_service.get_global_stats() 