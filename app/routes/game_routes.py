from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.controllers.game_controller import GameController

router = APIRouter(tags=["Game"])

class GameCreate(BaseModel):
    player1: str
    player2: str

@router.post("/create_game")
async def create_game(game: GameCreate):
    try:
        return await GameController.create_game(game.player1, game.player2)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def index():
    return {"message": "Welcome to Portal Gambit!"} 