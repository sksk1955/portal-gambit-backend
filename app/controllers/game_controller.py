from flask import jsonify
from app.services.game_service import GameService

class GameController:
    @staticmethod
    async def create_game(player1: str, player2: str):
        try:
            game_id = await GameService.create_game(player1, player2)
            return {"message": "Game created successfully", "game_id": game_id}
        except Exception as e:
            raise Exception(str(e)) 