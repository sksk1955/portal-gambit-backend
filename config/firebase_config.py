import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

cred = credentials.Certificate('config/firebase_config.json') 
firebase_admin.initialize_app(cred)
db = firestore.client()