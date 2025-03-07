from fastapi import APIRouter, Depends, HTTPException
from typing import List
from models.game_history import GameHistory
from schemas.history_schemas import (
    GameHistoryParams,
    GamesBetweenPlayersParams,
    UserStatsParams,
    PopularOpeningsParams,
    GameHistoryResponse,
    UserGameStats,
    OpeningStats
)
from schemas.auth_schemas import TokenData
from services.history_service import HistoryService
from utils.dependencies import get_current_user, get_history_service

router = APIRouter(prefix="/history", tags=["history"])

@router.post("/games", response_model=GameHistoryResponse)
async def archive_game(
    game: GameHistory,
    current_user: TokenData = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service)
):
    """Archive a completed game."""
    # Verify that the current user was a participant in the game
    if current_user.uid not in [game.white_player_id, game.black_player_id]:
        raise HTTPException(status_code=403, detail="Can only archive games you participated in")
    success = await history_service.archive_game(game)
    return GameHistoryResponse(
        status="success" if success else "error",
        message="Game archived successfully" if success else "Failed to archive game"
    )

@router.get("/games/{game_id}", response_model=GameHistory)
async def get_game(
    game_id: str,
    current_user: TokenData = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service)
):
    """Get a specific game by ID."""
    game = await history_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@router.get("/users/{user_id}/games", response_model=List[GameHistory])
async def get_user_games(
    user_id: str,
    params: GameHistoryParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service)
):
    """Get recent games for a user."""
    return await history_service.get_user_games(user_id, params.limit)

@router.get("/games/between/{player1_id}/{player2_id}", response_model=List[GameHistory])
async def get_games_between_players(
    player1_id: str,
    player2_id: str,
    params: GamesBetweenPlayersParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service)
):
    """Get recent games between two specific players."""
    return await history_service.get_games_between_players(player1_id, player2_id, params.limit)

@router.get("/users/{user_id}/stats", response_model=UserGameStats)
async def get_user_stats(
    user_id: str,
    params: UserStatsParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service)
):
    """Get user's game statistics for a specific time period."""
    return await history_service.get_user_stats(user_id, params.days)

@router.get("/openings/popular", response_model=List[OpeningStats])
async def get_popular_openings(
    params: PopularOpeningsParams = Depends(),
    current_user: TokenData = Depends(get_current_user),
    history_service: HistoryService = Depends(get_history_service)
):
    """Get most popular opening moves from recent games."""
    return await history_service.get_popular_openings(params.limit) 