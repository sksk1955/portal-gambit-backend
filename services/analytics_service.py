from firebase_admin import firestore
from typing import Dict, Any, List, Optional
from .base_service import BaseService
from datetime import datetime, timedelta
from models.game_history import GameResult

class AnalyticsService(BaseService):
    def __init__(self, db: firestore.Client):
        super().__init__(db)
        self.collection = 'analytics'
        self.cache_collection = 'analytics_cache'

    async def record_game_analytics(self, game_data: Dict[str, Any]) -> bool:
        """Record analytics data for a completed game."""
        analytics_id = f"game_{game_data['game_id']}"
        analytics = {
            'timestamp': datetime.utcnow(),
            'game_id': game_data['game_id'],
            'duration': (game_data['end_time'] - game_data['start_time']).total_seconds(),
            'total_moves': len(game_data['moves']),
            'result': game_data['result'],
            'white_player_id': game_data['white_player_id'],
            'black_player_id': game_data['black_player_id'],
            'rating_change': game_data['rating_change'],
            'game_type': game_data['game_type'],
            'time_control': game_data['time_control']
        }
        return await self.set_document(self.collection, analytics_id, analytics)

    async def get_daily_stats(self, date: datetime) -> Dict[str, Any]:
        """Get aggregated statistics for a specific day."""
        cache_key = f"daily_stats_{date.strftime('%Y-%m-%d')}"
        
        # Try to get from cache first
        cached_stats = await self.get_document(self.cache_collection, cache_key)
        if cached_stats:
            return cached_stats

        start_time = datetime.combine(date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        filters = [
            ('timestamp', '>=', start_time),
            ('timestamp', '<', end_time)
        ]
        
        games = await self.query_collection(self.collection, filters=filters)
        
        stats = {
            'total_games': len(games),
            'average_duration': 0,
            'average_moves': 0,
            'white_wins': 0,
            'black_wins': 0,
            'draws': 0,
            'abandoned': 0,
            'game_types': {},
            'time_controls': {}
        }
        
        total_duration = 0
        total_moves = 0
        
        for game in games:
            total_duration += game['duration']
            total_moves += game['total_moves']
            
            if game['result'] == GameResult.WHITE_WIN:
                stats['white_wins'] += 1
            elif game['result'] == GameResult.BLACK_WIN:
                stats['black_wins'] += 1
            elif game['result'] == GameResult.DRAW:
                stats['draws'] += 1
            else:
                stats['abandoned'] += 1
            
            # Count game types
            game_type = game['game_type']
            stats['game_types'][game_type] = stats['game_types'].get(game_type, 0) + 1
            
            # Count time controls
            time_control = f"{game['time_control']['initial']}/{game['time_control']['increment']}"
            stats['time_controls'][time_control] = stats['time_controls'].get(time_control, 0) + 1
        
        if stats['total_games'] > 0:
            stats['average_duration'] = total_duration / stats['total_games']
            stats['average_moves'] = total_moves / stats['total_games']
        
        # Cache the results
        await self.set_document(self.cache_collection, cache_key, stats)
        
        return stats

    async def get_player_performance(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed performance analytics for a player."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        filters = [
            [('white_player_id', '==', user_id), ('timestamp', '>=', start_date)],
            [('black_player_id', '==', user_id), ('timestamp', '>=', start_date)]
        ]
        
        performance = {
            'rating_progression': [],
            'average_game_duration': 0,
            'preferred_time_control': None,
            'preferred_game_type': None,
            'win_rate': 0,
            'performance_by_color': {
                'white': {'games': 0, 'wins': 0},
                'black': {'games': 0, 'wins': 0}
            },
            'average_moves_per_game': 0
        }
        
        games = []
        for filter_set in filters:
            results = await self.query_collection(self.collection, filters=filter_set)
            games.extend(results)
        
        if not games:
            return performance
        
        # Sort games by timestamp
        games.sort(key=lambda x: x['timestamp'])
        
        total_duration = 0
        total_moves = 0
        time_controls = {}
        game_types = {}
        
        for game in games:
            # Track rating progression
            is_white = game['white_player_id'] == user_id
            rating_change = game['rating_change']['white' if is_white else 'black']
            performance['rating_progression'].append({
                'timestamp': game['timestamp'],
                'rating_change': rating_change
            })
            
            # Track color performance
            color = 'white' if is_white else 'black'
            performance['performance_by_color'][color]['games'] += 1
            if (is_white and game['result'] == GameResult.WHITE_WIN) or \
               (not is_white and game['result'] == GameResult.BLACK_WIN):
                performance['performance_by_color'][color]['wins'] += 1
            
            # Track time controls and game types
            time_control = f"{game['time_control']['initial']}/{game['time_control']['increment']}"
            time_controls[time_control] = time_controls.get(time_control, 0) + 1
            game_types[game['game_type']] = game_types.get(game['game_type'], 0) + 1
            
            total_duration += game['duration']
            total_moves += game['total_moves']
        
        # Calculate averages and preferences
        total_games = len(games)
        performance['average_game_duration'] = total_duration / total_games
        performance['average_moves_per_game'] = total_moves / total_games
        
        # Find preferred time control and game type
        performance['preferred_time_control'] = max(time_controls.items(), key=lambda x: x[1])[0]
        performance['preferred_game_type'] = max(game_types.items(), key=lambda x: x[1])[0]
        
        # Calculate overall win rate
        total_wins = sum(color['wins'] for color in performance['performance_by_color'].values())
        performance['win_rate'] = total_wins / total_games
        
        return performance

    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global game statistics."""
        cache_key = 'global_stats'
        cached_stats = await self.get_document(self.cache_collection, cache_key)
        
        # Return cached stats if less than 1 hour old
        if cached_stats and \
           (datetime.utcnow() - cached_stats['last_updated']).total_seconds() < 3600:
            return cached_stats
        
        # Calculate new stats
        results = await self.query_collection(
            self.collection,
            order_by=('timestamp', 'DESCENDING'),
            limit=10000  # Get a good sample size
        )
        
        stats = {
            'total_games': len(results),
            'white_win_rate': 0,
            'average_game_duration': 0,
            'average_moves_per_game': 0,
            'popular_time_controls': {},
            'popular_game_types': {},
            'last_updated': datetime.utcnow()
        }
        
        if not results:
            return stats
        
        white_wins = 0
        total_duration = 0
        total_moves = 0
        
        for game in results:
            if game['result'] == GameResult.WHITE_WIN:
                white_wins += 1
            
            total_duration += game['duration']
            total_moves += game['total_moves']
            
            time_control = f"{game['time_control']['initial']}/{game['time_control']['increment']}"
            stats['popular_time_controls'][time_control] = \
                stats['popular_time_controls'].get(time_control, 0) + 1
            
            stats['popular_game_types'][game['game_type']] = \
                stats['popular_game_types'].get(game['game_type'], 0) + 1
        
        stats['white_win_rate'] = white_wins / stats['total_games']
        stats['average_game_duration'] = total_duration / stats['total_games']
        stats['average_moves_per_game'] = total_moves / stats['total_games']
        
        # Sort and limit popular lists
        stats['popular_time_controls'] = dict(
            sorted(stats['popular_time_controls'].items(), key=lambda x: x[1], reverse=True)[:5]
        )
        stats['popular_game_types'] = dict(
            sorted(stats['popular_game_types'].items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        # Cache the results
        await self.set_document(self.cache_collection, cache_key, stats)
        
        return stats 