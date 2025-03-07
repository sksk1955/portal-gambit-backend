import firebase_admin
from firebase_admin import credentials, db, firestore, auth
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    try:
        # Get the path to service account file from environment variable
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if not service_account_path:
            raise ValueError("Firebase service account path not found in environment variables")

        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.getenv('FIREBASE_DATABASE_URL'),
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
        })
        
        # Initialize Firestore client
        db_client = firestore.client()
        
        return db_client
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise