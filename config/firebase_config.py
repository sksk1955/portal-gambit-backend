import os

import firebase_admin
from dotenv import load_dotenv
from google.cloud.firestore_v1.async_client import AsyncClient

# Load environment variables
load_dotenv()

_db_client: AsyncClient = None  # Cache the client instance


def initialize_firebase():
    """Initialize Firebase Admin SDK and return an Async Firestore client."""
    global _db_client
    if _db_client:
        print("Using cached Firestore AsyncClient.")
        return _db_client

    try:
        # Get the path to service account file from environment variable
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH',
                                         'config/firebase_service_account.json')  # Default path

        if os.path.exists(service_account_path):
            cred = firebase_admin.credentials.Certificate(service_account_path)
            print(f"Initializing Firebase from path: {service_account_path}...")
        else:
            raise ValueError(
                "Firebase credentials not found. Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_CONFIG_STRING.")

        # Initialize Firebase Admin SDK only if not already initialized
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                # databaseURL and storageBucket are often optional for Firestore only
                # 'databaseURL': os.getenv('FIREBASE_DATABASE_URL'),
                # 'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
            })
            print("Firebase Admin App Initialized.")
        else:
            print("Firebase Admin App already initialized.")

        # Initialize Firestore Async client
        # Pass the project ID explicitly if needed, often inferred from creds
        from google.auth import default
        credentials, project_id = default()
        _db_client = AsyncClient(project=project_id, credentials=credentials)  # Use AsyncClient
        print(f"Firestore AsyncClient Initialized for project: {_db_client.project}")

        return _db_client
    except Exception as e:
        print(f"Error initializing Firebase/Firestore: {e}")
        raise
