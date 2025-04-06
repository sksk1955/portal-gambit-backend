from typing import Optional, Any, Dict, List

from firebase_admin import auth
from google.cloud.firestore_v1 import FieldFilter, Query  # Keep for constants if needed
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.async_query import AsyncQuery
from google.cloud.firestore_v1.base_document import BaseDocumentReference  # For type hint
from google.cloud.firestore_v1.types import WriteResult


class BaseService:
    def __init__(self, db: AsyncClient):  # Correct type hint
        self.db = db
        self._auth = auth  # auth is sync, okay here

    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document from Firestore."""
        try:
            doc_ref: BaseDocumentReference = self.db.collection(collection).document(doc_id)
            # await the get() call
            doc = await doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting document {collection}/{doc_id}: {e}")
            return None  # Return None on error

    async def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """Create or update a document in Firestore."""
        try:
            doc_ref: BaseDocumentReference = self.db.collection(collection).document(doc_id)
            # await the set() call
            _: WriteResult = await doc_ref.set(data)  # Result is not usually awaited
            return True
        except Exception as e:
            print(f"Error setting document {collection}/{doc_id}: {e}")
            return False  # Return False on error

    async def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update fields in a document."""
        try:
            doc_ref: BaseDocumentReference = self.db.collection(collection).document(doc_id)
            # await the update() call
            _: WriteResult = await doc_ref.update(data)  # Result is not usually awaited
            return True
        except Exception as e:
            print(f"Error updating document {collection}/{doc_id}: {e}")
            return False  # Return False on error

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from Firestore."""
        try:
            doc_ref: BaseDocumentReference = self.db.collection(collection).document(doc_id)
            # await the delete() call
            _: WriteResult = await doc_ref.delete()  # Result is not usually awaited
            return True
        except Exception as e:
            print(f"Error deleting document {collection}/{doc_id}: {e}")
            return False  # Return False on error

    async def query_collection(self, collection: str, filters: Optional[List[tuple]] = None,
                               order_by: Optional[tuple] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query a collection with optional filters, ordering, and limit."""
        try:
            query: AsyncQuery = self.db.collection(collection)

            if filters:
                for field, op, value in filters:
                    # Use keyword filter= argument
                    query = query.where(filter=FieldFilter(field, op, value))

            if order_by:
                field, direction_str = order_by
                direction = Query.DESCENDING if direction_str == 'DESCENDING' else Query.ASCENDING
                query = query.order_by(field, direction=direction)

            if limit:
                query = query.limit(limit)

            # Use await query.get()
            docs_snapshot = await query.get()
            return [doc.to_dict() for doc in docs_snapshot if doc.exists]

        except Exception as e:
            print(f"Error querying collection {collection}: {e}")
            return []  # Return empty list on error

    # verify_token remains the same (it's synchronous)
    def verify_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token."""
        try:
            decoded_token = self._auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None
