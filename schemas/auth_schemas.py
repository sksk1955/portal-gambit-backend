from pydantic import BaseModel
from typing import Optional

class FirebaseTokenRequest(BaseModel):
    """Schema for Firebase token authentication request."""
    firebase_token: str

class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    """Schema for JWT token payload."""
    uid: str
    email: Optional[str] = None
    email_verified: Optional[bool] = False 