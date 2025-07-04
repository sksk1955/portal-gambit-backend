from datetime import datetime, timezone  # Use timezone
from typing import Optional, Dict, Any, List

from firebase_admin import firestore
from google.cloud import firestore
from models.user_profile import UserProfile
from .base_service import BaseService


class ProfileService(BaseService):
    def __init__(self, db: firestore.AsyncClient):
        super().__init__(db)
        self.collection = 'user_profiles'

    async def create_profile(self, profile: UserProfile) -> bool:
        """Create a new user profile."""
        # FIX: Use model_dump() instead of dict()
        return await self.set_document(self.collection, profile.uid, profile.model_dump())

    async def get_profile(self, uid: str) -> Optional[UserProfile]:
        """Retrieve a user profile by UID."""
        data = await self.get_document(self.collection, uid)
        return UserProfile(**data) if data else None

    async def update_profile(self, uid: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in a user profile."""
        # FIX: Use timezone.utc
        updates['last_active'] = datetime.now(timezone.utc)
        return await self.update_document(self.collection, uid, updates)

    async def update_rating(self, uid: str, new_rating: int, game_result: Dict[str, Any]) -> bool:
        """Update user's rating and game statistics."""
        updates = {
            'rating': new_rating,
            'games_played': firestore.Increment(1),
        }

        if game_result['result'] == 'win':
            updates['wins'] = firestore.Increment(1)
        elif game_result['result'] == 'loss':
            updates['losses'] = firestore.Increment(1)
        else:
            updates['draws'] = firestore.Increment(1)

        return await self.update_document(self.collection, uid, updates)

    async def search_profiles(self, username_prefix: str, limit: int = 10) -> List[UserProfile]:
        """Search for profiles by username prefix."""
        filters = [
            ('username', '>=', username_prefix),
            ('username', '<=', username_prefix + '\uf8ff')
        ]
        results = await self.query_collection(
            self.collection,
            filters=filters,
            order_by=('username', 'ASCENDING'),
            limit=limit
        )
        return [UserProfile(**data) for data in results]

    async def get_leaderboard(self, limit: int = 100) -> List[UserProfile]:
        """Get top rated players."""
        results = await self.query_collection(
            self.collection,
            order_by=('rating', 'DESCENDING'),
            limit=limit
        )
        return [UserProfile(**data) for data in results]

    async def add_achievement(self, uid: str, achievement_id: str) -> bool:
        """Add an achievement to user's profile."""
        # Use ArrayUnion from google.cloud.firestore_v1, not firebase_admin.firestore
        from google.cloud.firestore_v1 import ArrayUnion
        return await self.update_document(
            self.collection,
            uid,
            {'achievements': ArrayUnion([achievement_id])}
        )
