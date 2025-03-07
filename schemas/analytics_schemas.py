from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

class GameAnalyticsCreate(BaseModel):
    """Schema for creating game analytics."""
    game_id: str
    white_player_id: str
    black_player_id: str
    start_time: datetime
    end_time: datetime
    result: str
    moves: List[str]
    rating_change: Dict[str, int]
    game_type: str
    time_control: Dict[str, int]

class DailyStats(BaseModel):
    """Schema for daily statistics."""
    total_games: int
    average_duration: float
    average_moves: float
    white_wins: int
    black_wins: int
    draws: int
    abandoned: int
    game_types: Dict[str, int]
    time_controls: Dict[str, int]

class PlayerPerformance(BaseModel):
    """Schema for player performance statistics."""
    rating_progression: List[Dict[str, Any]]
    average_game_duration: float
    preferred_time_control: Optional[str]
    preferred_game_type: Optional[str]
    win_rate: float
    performance_by_color: Dict[str, Dict[str, int]]
    average_moves_per_game: float

class GlobalStats(BaseModel):
    """Schema for global game statistics."""
    total_games: int
    white_win_rate: float
    average_game_duration: float
    average_moves_per_game: float
    popular_time_controls: Dict[str, int]
    popular_game_types: Dict[str, int]
    last_updated: datetime

class AnalyticsResponse(BaseModel):
    """Schema for generic analytics operation response."""
    status: str
    message: Optional[str] = None 