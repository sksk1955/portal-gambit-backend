from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status  # import status

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Can only record analytics for games you participated in")

    # FIX: Use model_dump() instead of dict()
    game_dict = game_data.model_dump()
    # Add game_id from path parameter, as it might not be in the body schema required by FastAPI
    game_dict['game_id'] = game_id

    success = await analytics_service.record_game_analytics(game_dict)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record game analytics")

    return AnalyticsResponse(
        status="success",
        message="Game analytics recorded successfully"
    )


@router.get("/daily/{date}", response_model=DailyStats)
async def get_daily_stats(
        date: datetime,  # FastAPI handles path param conversion
        current_user: TokenData = Depends(get_current_user),
        analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get aggregated statistics for a specific day."""
    # Add try-except block if service method can raise specific errors
    try:
        stats = await analytics_service.get_daily_stats(date)
        return stats
    except Exception as e:
        # Log the error e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching daily statistics")


@router.get("/players/{user_id}/performance", response_model=PlayerPerformance)
async def get_player_performance(
        user_id: str,
        days: int = 30,
        current_user: TokenData = Depends(get_current_user),  # Auth needed to view performance?
        analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get detailed performance analytics for a player."""
    # Add try-except block
    try:
        performance = await analytics_service.get_player_performance(user_id, days)
        return performance
    except Exception as e:
        # Log the error e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error fetching player performance")


@router.get("/global", response_model=GlobalStats)
async def get_global_stats(
        current_user: TokenData = Depends(get_current_user),  # Auth needed?
        analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get global game statistics."""
    # Add try-except block
    try:
        global_stats = await analytics_service.get_global_stats()
        return global_stats
    except Exception as e:
        # Log the error e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error fetching global statistics")
