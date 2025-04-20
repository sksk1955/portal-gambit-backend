from datetime import datetime, timedelta, timezone  # Use timezone
from typing import Optional, List, Dict, Any

from google.cloud import firestore

from models.game_history import GameHistory, GameResult
from .base_service import BaseService
from services.profile_service import ProfileService  # Import at class level

class HistoryService(BaseService):
    def __init__(self, db: firestore.AsyncClient):
        super().__init__(db)
        self.collection = 'game_history'

    async def archive_game(self, game: GameHistory) -> bool:
        """Archive a completed game."""
        # FIX: Use model_dump() instead of dict()
        success = await self.set_document(self.collection, game.game_id, game.model_dump())
        
        # If game was successfully archived, update player profiles
        if success:
            # Create profile service
            profile_service = ProfileService(self.db)
            
            # Fetch current player profiles to get accurate ratings
            white_profile = await profile_service.get_profile(game.white_player_id)
            black_profile = await profile_service.get_profile(game.black_player_id)
            
            # Use current ratings from profiles if available, otherwise use game data
            white_current_rating = white_profile.rating if white_profile else game.white_rating
            black_current_rating = black_profile.rating if black_profile else game.black_rating
            
            # Calculate new ratings with rating changes
            white_new_rating = white_current_rating + game.rating_change.get('white', 0)
            black_new_rating = black_current_rating + game.rating_change.get('black', 0)
            
            # Update white player profile
            white_result = {'result': 'win' if game.result == GameResult.WHITE_WIN else 
                                     'loss' if game.result == GameResult.BLACK_WIN else 'draw'}
            await profile_service.update_rating(
                game.white_player_id, 
                white_new_rating, 
                white_result
            )
            
            # Update black player profile
            black_result = {'result': 'win' if game.result == GameResult.BLACK_WIN else 
                                     'loss' if game.result == GameResult.WHITE_WIN else 'draw'}
            await profile_service.update_rating(
                game.black_player_id, 
                black_new_rating, 
                black_result
            )
        
        return success

    async def get_game(self, game_id: str) -> Optional[GameHistory]:
        """Retrieve a specific game by ID."""
        data = await self.get_document(self.collection, game_id)
        return GameHistory(**data) if data else None

    async def get_user_games(self, user_id: str, limit: int = 50) -> List[GameHistory]:
        """Get recent games for a user."""
        # BaseService query needs adjustment for OR logic simulation or use two queries
        # Assuming BaseService query is adapted or this method runs two queries
        # If using BaseService's current implementation, it might only query one field.
        # Let's assume the service logic ORs the results from two queries if necessary.

        # Query for games where user is white
        filters_white = [('white_player_id', '==', user_id)]
        white_games_data = await self.query_collection(
            self.collection,
            filters=filters_white,
            order_by=('end_time', 'DESCENDING'),
            limit=limit  # Apply limit here too, although final sort/limit is better
        )

        # Query for games where user is black
        filters_black = [('black_player_id', '==', user_id)]
        black_games_data = await self.query_collection(
            self.collection,
            filters=filters_black,
            order_by=('end_time', 'DESCENDING'),
            limit=limit
        )

        # Combine, remove duplicates (if any, though unlikely with unique IDs), sort, and limit
        all_games_data = {game['game_id']: game for game in white_games_data + black_games_data}
        sorted_games = sorted(all_games_data.values(), key=lambda x: x['end_time'], reverse=True)

        return [GameHistory(**data) for data in sorted_games[:limit]]

    async def get_games_between_players(self, player1_id: str, player2_id: str, limit: int = 10) -> List[GameHistory]:
        """Get recent games between two specific players."""
        # Query for player1 as white, player2 as black
        filters1 = [('white_player_id', '==', player1_id), ('black_player_id', '==', player2_id)]
        games1_data = await self.query_collection(
            self.collection,
            filters=filters1,
            order_by=('end_time', 'DESCENDING'),
            limit=limit
        )

        # Query for player2 as white, player1 as black
        filters2 = [('white_player_id', '==', player2_id), ('black_player_id', '==', player1_id)]
        games2_data = await self.query_collection(
            self.collection,
            filters=filters2,
            order_by=('end_time', 'DESCENDING'),
            limit=limit
        )

        # Combine, sort by end_time descending, and take the top 'limit' results
        all_games_data = {game['game_id']: game for game in games1_data + games2_data}
        sorted_games = sorted(all_games_data.values(), key=lambda x: x['end_time'], reverse=True)

        return [GameHistory(**data) for data in sorted_games[:limit]]

    async def get_user_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user's game statistics for a specific time period."""
        # FIX: Use timezone.utc
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Combine filters for BaseService or run two queries as above
        # Running two queries for clarity:
        filters_white = [('white_player_id', '==', user_id), ('end_time', '>=', start_date)]
        white_games = await self.query_collection(self.collection, filters=filters_white)

        filters_black = [('black_player_id', '==', user_id), ('end_time', '>=', start_date)]
        black_games = await self.query_collection(self.collection, filters=filters_black)

        all_user_games_data = {game['game_id']: game for game in white_games + black_games}

        stats = {
            'total_games': 0, 'wins': 0, 'losses': 0, 'draws': 0,
            'white_games': 0, 'black_games': 0, 'rating_change': 0,
            'average_game_length': 0, 'total_moves': 0
        }
        total_duration = 0

        for game_data in all_user_games_data.values():
            try:
                game = GameHistory(**game_data)
                stats['total_games'] += 1

                is_white = game.white_player_id == user_id
                if is_white:
                    stats['white_games'] += 1
                    stats['rating_change'] += game.rating_change.get('white', 0)  # Use .get for safety
                else:
                    stats['black_games'] += 1
                    stats['rating_change'] += game.rating_change.get('black', 0)  # Use .get for safety

                if game.result == GameResult.WHITE_WIN:
                    if is_white:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1
                elif game.result == GameResult.BLACK_WIN:
                    if not is_white:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1
                elif game.result == GameResult.DRAW:
                    stats['draws'] += 1

                stats['total_moves'] += len(game.moves)
                # Ensure end_time and start_time are datetime objects
                end_time = game.end_time if isinstance(game.end_time, datetime) else datetime.fromisoformat(
                    str(game.end_time))
                start_time = game.start_time if isinstance(game.start_time, datetime) else datetime.fromisoformat(
                    str(game.start_time))
                total_duration += (end_time - start_time).total_seconds()
            except Exception as e:
                print(f"Warning: Skipping game data due to parsing error: {game_data.get('game_id')}, Error: {e}")
                continue  # Skip problematic game data

        if stats['total_games'] > 0:
            stats['average_game_length'] = total_duration / stats['total_games']

        return stats

    async def get_popular_openings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular opening moves from recent games."""
        # Consider adding a date filter here for performance (e.g., last 30 days)
        results = await self.query_collection(
            self.collection,
            order_by=('end_time', 'DESCENDING'),
            limit=1000  # Sample size limit
        )

        openings = {}
        for game_data in results:
            try:
                # Ensure data is parsed into the model
                game = GameHistory(**game_data)
                if len(game.moves) >= 3:  # Consider first 3 moves as opening
                    opening_key = ' '.join(game.moves[:3])
                    if opening_key not in openings:
                        openings[opening_key] = {'count': 0, 'wins': 0}  # Initialize wins
                    openings[opening_key]['count'] += 1

                    # FIX: Correctly count wins based on result, regardless of winner_id presence
                    # Count decisive wins (not draws or abandoned)
                    if game.result == GameResult.WHITE_WIN or game.result == GameResult.BLACK_WIN:
                        openings[opening_key]['wins'] += 1

            except Exception as e:
                print(
                    f"Warning: Skipping game data in opening stats due to parsing error: "
                    f"{game_data.get('game_id')}, Error: {e}")
                continue

        # Sort by popularity
        popular_openings = sorted(
            [{'moves': k, **v} for k, v in openings.items()],
            key=lambda x: x['count'],
            reverse=True
        )

        return popular_openings[:limit]
