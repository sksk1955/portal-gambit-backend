from config.firebase_config import db

class GameService:
    @staticmethod
    async def create_game(player1: str, player2: str):
        game_data = {
            'player1': player1,
            'player2': player2,
            'status': 'waiting',
            'moves': []
        }
        game_ref = db.collection('games').add(game_data)
        return game_ref[1].id 