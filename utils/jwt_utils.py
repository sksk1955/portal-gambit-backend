import os
from datetime import datetime, timedelta, timezone  # Use timezone-aware objects
from typing import Optional

from dotenv import load_dotenv
from fastapi import HTTPException
from jose import JWTError, jwt

load_dotenv()

# Get JWT settings from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY must be set in environment variables")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()

    # Set expiration time using timezone-aware datetime
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    # Ensure standard claims like 'iat' are included if needed, though jose might add them.
    # Add 'iat' (issued at) claim
    to_encode.setdefault("iat", datetime.now(timezone.utc))

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify a JWT token and return its payload."""
    try:
        # Decode the token, ignoring audience verification for internal use
        # Explicitly pass options to disable audience verification
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}  # <--- FIX: Ignore audience verification
        )
        if "uid" not in payload:
            raise JWTError("Missing 'uid' claim in token payload.")
        # Optional: Add expiration check here if not handled by decode
        # exp = payload.get("exp")
        # if exp is None or datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
        #     raise ExpiredSignatureError("Token has expired.")
        return payload
    except JWTError as e:  # Catch specific JOSE errors first
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:  # Catch other potential errors during decoding
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: Unexpected error ({type(e).__name__})",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_tokens_for_user(firebase_user: dict) -> dict:
    """Create access token from Firebase user data."""
    # Extract relevant user data
    user_data = {
        "uid": firebase_user["uid"],
        "email": firebase_user.get("email"),
        "email_verified": firebase_user.get("email_verified", False),
        # Add other claims from firebase_user if needed for the backend token
        # e.g., "name": firebase_user.get("name")
    }

    # Create access token
    access_token = create_access_token(user_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }