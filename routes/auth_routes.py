from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import auth
from schemas.auth_schemas import FirebaseTokenRequest, TokenResponse, TokenData
from utils.jwt_utils import create_tokens_for_user, verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/token", response_model=TokenResponse)
async def get_token(request: FirebaseTokenRequest):
    """Exchange Firebase token for backend JWT token."""
    try:
        # Verify Firebase token
        decoded_token = auth.verify_id_token(request.firebase_token)
        
        # Create our own JWT token
        tokens = create_tokens_for_user(decoded_token)
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Firebase token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.get("/verify", response_model=TokenData)
async def verify_access_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the backend JWT token."""
    try:
        payload = verify_token(credentials.credentials)
        return TokenData(
            uid=payload["uid"],
            email=payload.get("email"),
            email_verified=payload.get("email_verified", False)
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        ) 