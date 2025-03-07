from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class GameHistoryParams(BaseModel):
    """Schema for game history query parameters."""
    limit: int = 50
    days: Optional[int] = 30

class GamesBetweenPlayersParams(BaseModel):
    """Schema for querying games between players."""
    player1_id: str
    player2_id: str
    limit: int = 10

class UserStatsParams(BaseModel):
    """Schema for user stats query parameters."""
    user_id: str
    days: int = 30

class PopularOpeningsParams(BaseModel):
    """Schema for popular openings query parameters."""
    limit: int = 10

class GameHistoryResponse(BaseModel):
    """Schema for game history operation response."""
    status: str
    message: Optional[str] = None

class OpeningStats(BaseModel):
    """Schema for opening statistics."""
    moves: str
    count: int
    wins: int

class UserGameStats(BaseModel):
    """Schema for user game statistics."""
    total_games: int
    wins: int
    losses: int
    draws: int
    white_games: int
    black_games: int
    rating_change: int
    average_game_length: float
    total_moves: int 