from firebase_admin import firestore, auth
from typing import Optional, Any, Dict, List

class BaseService:
    def __init__(self, db: firestore.Client):
        self.db = db
        self._auth = auth

    async def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document from Firestore."""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting document: {e}")
            return None

    async def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """Create or update a document in Firestore."""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(data)
            return True
        except Exception as e:
            print(f"Error setting document: {e}")
            return False

    async def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update fields in a document."""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.update(data)
            return True
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from Firestore."""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    async def query_collection(self, collection: str, filters: List[tuple] = None, 
                             order_by: tuple = None, limit: int = None) -> List[Dict[str, Any]]:
        """Query a collection with optional filters, ordering, and limit."""
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, op, value in filters:
                    query = query.where(field, op, value)
            
            if order_by:
                field, direction = order_by
                query = query.order_by(field, direction=direction)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Error querying collection: {e}")
            return []

    def verify_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token."""
        try:
            decoded_token = self._auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Error verifying token: {e}")
            return None 