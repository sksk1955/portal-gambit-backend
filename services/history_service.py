from firebase_admin import firestore
from typing import Optional, List, Dict, Any
from .base_service import BaseService
from models.game_history import GameHistory, GameResult
from datetime import datetime, timedelta

class HistoryService(BaseService):
    def __init__(self, db: firestore.Client):
        super().__init__(db)
        self.collection = 'game_history'

    async def archive_game(self, game: GameHistory) -> bool:
        """Archive a completed game."""
        return await self.set_document(self.collection, game.game_id, game.dict())

    async def get_game(self, game_id: str) -> Optional[GameHistory]:
        """Retrieve a specific game by ID."""
        data = await self.get_document(self.collection, game_id)
        return GameHistory(**data) if data else None

    async def get_user_games(self, user_id: str, limit: int = 50) -> List[GameHistory]:
        """Get recent games for a user."""
        filters = [
            ('white_player_id', '==', user_id),
            ('black_player_id', '==', user_id)
        ]
        results = await self.query_collection(
            self.collection,
            filters=filters,
            order_by=('end_time', 'DESCENDING'),
            limit=limit
        )
        return [GameHistory(**data) for data in results]

    async def get_games_between_players(self, player1_id: str, player2_id: str, limit: int = 10) -> List[GameHistory]:
        """Get recent games between two specific players."""
        filters = [
            [('white_player_id', '==', player1_id), ('black_player_id', '==', player2_id)],
            [('white_player_id', '==', player2_id), ('black_player_id', '==', player1_id)]
        ]
        
        results = []
        for filter_set in filters:
            games = await self.query_collection(
                self.collection,
                filters=filter_set,
                order_by=('end_time', 'DESCENDING'),
                limit=limit
            )
            results.extend(games)
            
        # Sort combined results by end_time
        results.sort(key=lambda x: x['end_time'], reverse=True)
        return [GameHistory(**data) for data in results[:limit]]

    async def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user's game statistics for a specific time period."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        filters = [
            [('white_player_id', '==', user_id), ('end_time', '>=', start_date)],
            [('black_player_id', '==', user_id), ('end_time', '>=', start_date)]
        ]
        
        stats = {
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'white_games': 0,
            'black_games': 0,
            'rating_change': 0,
            'average_game_length': 0,
            'total_moves': 0
        }
        
        total_duration = 0
        
        for filter_set in filters:
            games = await self.query_collection(self.collection, filters=filter_set)
            for game_data in games:
                game = GameHistory(**game_data)
                stats['total_games'] += 1
                
                is_white = game.white_player_id == user_id
                stats['white_games'] += 1 if is_white else 0
                stats['black_games'] += 0 if is_white else 1
                
                if game.result == GameResult.WHITE_WIN:
                    stats['wins'] += 1 if is_white else 0
                    stats['losses'] += 0 if is_white else 1
                elif game.result == GameResult.BLACK_WIN:
                    stats['wins'] += 0 if is_white else 1
                    stats['losses'] += 1 if is_white else 0
                elif game.result == GameResult.DRAW:
                    stats['draws'] += 1
                
                stats['rating_change'] += game.rating_change['white' if is_white else 'black']
                stats['total_moves'] += len(game.moves)
                total_duration += (game.end_time - game.start_time).total_seconds()
        
        if stats['total_games'] > 0:
            stats['average_game_length'] = total_duration / stats['total_games']
        
        return stats

    async def get_popular_openings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular opening moves from recent games."""
        results = await self.query_collection(
            self.collection,
            order_by=('end_time', 'DESCENDING'),
            limit=1000  # Get a good sample size
        )
        
        openings = {}
        for game_data in results:
            game = GameHistory(**game_data)
            if len(game.moves) >= 3:  # Consider first 3 moves as opening
                opening_key = ' '.join(game.moves[:3])
                if opening_key not in openings:
                    openings[opening_key] = {'count': 0, 'wins': 0}
                openings[opening_key]['count'] += 1
                if game.result != GameResult.ABANDONED:
                    openings[opening_key]['wins'] += 1
        
        # Sort by popularity
        popular_openings = sorted(
            [{'moves': k, **v} for k, v in openings.items()],
            key=lambda x: x['count'],
            reverse=True
        )
        
        return popular_openings[:limit] 