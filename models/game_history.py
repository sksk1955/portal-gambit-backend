from datetime import datetime, timezone  # Import timezone
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class GameResult(str, Enum):
    WHITE_WIN = "white_win"
    BLACK_WIN = "black_win"
    DRAW = "draw"
    ABANDONED = "abandoned"


class GameHistory(BaseModel):
    game_id: str = Field(..., description="Unique game identifier")
    white_player_id: str = Field(..., description="UID of white player")
    black_player_id: str = Field(..., description="UID of black player")
    # FIX: Use datetime.now(timezone.utc) for default factory
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime  # Should be set when game ends
    result: GameResult
    winner_id: Optional[str] = None
    moves: List[str] = Field(..., description="List of moves in algebraic notation")
    initial_position: str = Field(default="standard", description="Starting position FEN")
    white_rating: int
    black_rating: int
    rating_change: dict = Field(..., description="Rating changes for both players")
    game_type: str = Field(default="portal_gambit", description="Variant type")
    time_control: dict = Field(..., description="Time control settings")

    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "game123",
                "white_player_id": "user1",
                "black_player_id": "user2",
                "result": "white_win",
                "winner_id": "user1",
                "moves": ["e4", "e5", "Nf3"],
                "white_rating": 1200,
                "black_rating": 1150,
                "rating_change": {"white": 8, "black": -8},
                "time_control": {"initial": 600, "increment": 5}
            }
        }
