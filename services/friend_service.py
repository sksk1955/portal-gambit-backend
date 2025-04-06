import uuid
from datetime import datetime, timezone
from typing import Optional, List

# Import necessary types for async Firestore
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.async_query import AsyncQuery
from google.cloud.firestore_v1.transaction import Transaction # Correct import
from google.cloud.firestore_v1 import FieldFilter, Increment, ArrayUnion, async_transactional
# Keep models
from models.friend import FriendRequest, FriendStatus, FriendRequestStatus
from .base_service import BaseService


class FriendService(BaseService):
    def __init__(self, db: AsyncClient): # Use AsyncClient
        super().__init__(db)
        self.requests_collection = 'friend_requests'
        self.friends_collection = 'friend_status'

    async def send_friend_request(self, sender_id: str, receiver_id: str, message: Optional[str] = None) -> bool:
        if sender_id == receiver_id:
            print(f"Attempt to send friend request to self blocked: {sender_id}")
            return False

        status_key = f"{sender_id}_{receiver_id}"
        # Ensure get_document is awaited (fixed in BaseService)
        existing_friendship = await self.get_document(self.friends_collection, status_key)
        if existing_friendship:
            print(f"Users {sender_id} and {receiver_id} are already friends.")
            return False

        query1: AsyncQuery = self.db.collection(self.requests_collection).where(
            filter=FieldFilter('sender_id', '==', sender_id)
        ).where(
            filter=FieldFilter('receiver_id', '==', receiver_id)
        ).where(
            filter=FieldFilter('status', '==', FriendRequestStatus.PENDING.value)
        ).limit(1)

        query2: AsyncQuery = self.db.collection(self.requests_collection).where(
            filter=FieldFilter('sender_id', '==', receiver_id)
        ).where(
            filter=FieldFilter('receiver_id', '==', sender_id)
        ).where(
            filter=FieldFilter('status', '==', FriendRequestStatus.PENDING.value)
        ).limit(1)

        # Await query.get()
        existing_sent_docs = await query1.get()
        existing_received_docs = await query2.get()

        if existing_sent_docs or existing_received_docs:
            print(f"Pending friend request already exists between {sender_id} and {receiver_id}.")
            return False

        request = FriendRequest(
            request_id=f"req_{uuid.uuid4().hex}", # Add prefix for clarity
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message,
        )
        # Ensure set_document is awaited (fixed in BaseService)
        return await self.set_document(self.requests_collection, request.request_id,
                                       request.model_dump(mode='json'))

    async def get_friend_request(self, request_id: str) -> Optional[FriendRequest]:
        # Uses get_document (fixed in BaseService)
        data = await self.get_document(self.requests_collection, request_id)
        return FriendRequest(**data) if data else None

    async def get_pending_requests(self, user_id: str) -> List[FriendRequest]:
        query: AsyncQuery = self.db.collection(self.requests_collection).where(
            filter=FieldFilter('receiver_id', '==', user_id)
        ).where(
            filter=FieldFilter('status', '==', FriendRequestStatus.PENDING.value)
        )
        # Await query.get()
        results_docs = await query.get()
        return [FriendRequest(**doc.to_dict()) for doc in results_docs if doc.exists]

    async def respond_to_request(self, request_id: str, accept: bool) -> bool:
        # Await get_document (fixed in BaseService)
        request_data = await self.get_document(self.requests_collection, request_id)
        if not request_data:
            return False
        try:
            request = FriendRequest(**request_data)
        except Exception as e:
             print(f"Error parsing friend request data {request_id}: {e}")
             return False

        if request.status != FriendRequestStatus.PENDING:
            print(f"Request {request_id} is not pending, cannot respond.")
            return False

        status = FriendRequestStatus.ACCEPTED if accept else FriendRequestStatus.REJECTED
        # Await update_document (fixed in BaseService)
        update_success = await self.update_document(
            self.requests_collection,
            request_id,
            {'status': status.value, 'updated_at': datetime.now(timezone.utc)}
        )
        if not update_success:
             print(f"Failed to update request status for {request_id}")
             return False # Return early if update failed

        if accept:
            friend_status1 = FriendStatus(user_id=request.sender_id, friend_id=request.receiver_id)
            friend_status2 = FriendStatus(user_id=request.receiver_id, friend_id=request.sender_id)
            status_key1 = f"{request.sender_id}_{request.receiver_id}"
            status_key2 = f"{request.receiver_id}_{request.sender_id}"

            # Await set_document (fixed in BaseService)
            set1_success = await self.set_document(self.friends_collection, status_key1, friend_status1.model_dump(mode='json'))
            set2_success = await self.set_document(self.friends_collection, status_key2, friend_status2.model_dump(mode='json'))

            if not (set1_success and set2_success):
                print(f"Warning: Failed to create one or both friend status entries for request {request_id}")
                # Consider cleanup logic here (e.g., delete the one that succeeded)
                return False # Return False if setting friend status fails

        return True # Return True only if all steps succeeded

    async def get_friends(self, user_id: str) -> List[FriendStatus]:
        query: AsyncQuery = self.db.collection(self.friends_collection).where(
            filter=FieldFilter('user_id', '==', user_id)
        )
        # Await query.get()
        results_docs = await query.get()
        return [FriendStatus(**doc.to_dict()) for doc in results_docs if doc.exists]

    async def remove_friend(self, user_id: str, friend_id: str) -> bool:
        status_key1 = f"{user_id}_{friend_id}"
        status_key2 = f"{friend_id}_{user_id}"

        # Get Async Transaction object
        transaction: Transaction = self.db.transaction()
        doc_ref1 = self.db.collection(self.friends_collection).document(status_key1)
        doc_ref2 = self.db.collection(self.friends_collection).document(status_key2)

        @async_transactional
        async def delete_in_transaction(transaction: Transaction, ref1, ref2):
            # Transaction operations are sync within the decorated func
            transaction.delete(ref1)
            transaction.delete(ref2)

        try:
            # Await the execution of the transactional function
            await delete_in_transaction(transaction, doc_ref1, doc_ref2)
            print(f"Successfully removed friend in transaction: {user_id} <-> {friend_id}")
            return True
        except Exception as e:
            print(f"Error removing friend in transaction for {user_id}-{friend_id}: {e}")
            return False

    async def update_last_interaction(self, user_id: str, friend_id: str, game_id: Optional[str] = None) -> bool:
        status_key = f"{user_id}_{friend_id}"
        updates = {
            'last_interaction': datetime.now(timezone.utc),
            'games_played': Increment(1)
        }
        if game_id:
            updates['last_game'] = game_id

        # Await update_document (fixed in BaseService)
        return await self.update_document(self.friends_collection, status_key, updates)