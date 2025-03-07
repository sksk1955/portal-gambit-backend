from firebase_admin import firestore
from typing import Optional, List, Dict, Any
from .base_service import BaseService
from models.friend import FriendRequest, FriendStatus, FriendRequestStatus
from datetime import datetime
import uuid

class FriendService(BaseService):
    def __init__(self, db: firestore.Client):
        super().__init__(db)
        self.requests_collection = 'friend_requests'
        self.friends_collection = 'friend_status'

    async def send_friend_request(self, sender_id: str, receiver_id: str, message: Optional[str] = None) -> bool:
        """Send a friend request."""
        request = FriendRequest(
            request_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message
        )
        return await self.set_document(self.requests_collection, request.request_id, request.dict())

    async def get_friend_request(self, request_id: str) -> Optional[FriendRequest]:
        """Get a specific friend request."""
        data = await self.get_document(self.requests_collection, request_id)
        return FriendRequest(**data) if data else None

    async def get_pending_requests(self, user_id: str) -> List[FriendRequest]:
        """Get all pending friend requests for a user."""
        filters = [
            ('receiver_id', '==', user_id),
            ('status', '==', FriendRequestStatus.PENDING)
        ]
        results = await self.query_collection(self.requests_collection, filters=filters)
        return [FriendRequest(**data) for data in results]

    async def respond_to_request(self, request_id: str, accept: bool) -> bool:
        """Accept or reject a friend request."""
        request = await self.get_friend_request(request_id)
        if not request:
            return False

        status = FriendRequestStatus.ACCEPTED if accept else FriendRequestStatus.REJECTED
        await self.update_document(
            self.requests_collection,
            request_id,
            {'status': status, 'updated_at': datetime.utcnow()}
        )

        if accept:
            # Create mutual friend status entries
            friend_status1 = FriendStatus(
                user_id=request.sender_id,
                friend_id=request.receiver_id
            )
            friend_status2 = FriendStatus(
                user_id=request.receiver_id,
                friend_id=request.sender_id
            )
            
            status_key1 = f"{request.sender_id}_{request.receiver_id}"
            status_key2 = f"{request.receiver_id}_{request.sender_id}"
            
            await self.set_document(self.friends_collection, status_key1, friend_status1.dict())
            await self.set_document(self.friends_collection, status_key2, friend_status2.dict())

        return True

    async def get_friends(self, user_id: str) -> List[FriendStatus]:
        """Get all friends of a user."""
        filters = [('user_id', '==', user_id)]
        results = await self.query_collection(self.friends_collection, filters=filters)
        return [FriendStatus(**data) for data in results]

    async def remove_friend(self, user_id: str, friend_id: str) -> bool:
        """Remove a friend relationship."""
        status_key1 = f"{user_id}_{friend_id}"
        status_key2 = f"{friend_id}_{user_id}"
        
        success1 = await self.delete_document(self.friends_collection, status_key1)
        success2 = await self.delete_document(self.friends_collection, status_key2)
        
        return success1 and success2

    async def update_last_interaction(self, user_id: str, friend_id: str, game_id: Optional[str] = None) -> bool:
        """Update the last interaction between friends."""
        status_key = f"{user_id}_{friend_id}"
        updates = {
            'last_interaction': datetime.utcnow(),
            'games_played': firestore.Increment(1)
        }
        if game_id:
            updates['last_game'] = game_id
        
        return await self.update_document(self.friends_collection, status_key, updates) 