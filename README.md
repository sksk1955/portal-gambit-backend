# Portal Gambit Backend

Backend API service for the Portal Gambit chess variant game, built with FastAPI and Firebase Authentication.

## Description

Portal Gambit Backend is a RESTful API service that powers the Portal Gambit chess variant game. It provides endpoints for user profiles, friend management, game history, and analytics, with secure authentication using Firebase.

## Features

- User profile management
- Friend system
- Game history tracking
- Analytics
- Firebase Authentication
- CORS support
- OpenAPI documentation (Swagger UI)

## Tech Stack

- Python 3.x
- FastAPI
- Firebase Admin SDK
- Uvicorn (ASGI server)
- Pydantic for data validation
- Python-dotenv for environment management

## Prerequisites

- Python 3.x
- Firebase project credentials
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd portal-gambit-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Unix or MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
FIREBASE_CREDENTIALS=path/to/your/firebase-credentials.json
# Add other environment variables as needed
```

## Running the Application

To run the development server:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Swagger UI documentation at `http://localhost:8000/docs`
- ReDoc documentation at `http://localhost:8000/redoc`

## Project Structure

```
portal-gambit-backend/
├── config/         # Configuration files
├── middleware/     # Custom middleware (including Firebase Auth)
├── models/        # Data models
├── routes/        # API route handlers
├── schemas/       # Pydantic schemas
├── services/      # Business logic
├── utils/         # Utility functions
├── .env           # Environment variables
├── main.py        # Application entry point
└── requirements.txt
```

## API Endpoints

- `/` - Root endpoint with API information
- `/profile/*` - User profile management
- `/friends/*` - Friend system endpoints
- `/history/*` - Game history endpoints
- `/analytics/*` - Analytics endpoints
- `/auth/*` - Authentication endpoints
