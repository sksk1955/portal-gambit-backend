from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import re
from utils.jwt_utils import verify_token

security = HTTPBearer()

class FirebaseAuthMiddleware:
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        """Initialize middleware with optional paths to exclude from authentication."""
        self.app = app
        default_exclude_paths = [
            r"^/auth/token$",  # Exclude the token endpoint
            # Add any other paths that should be public
        ]
        self.exclude_paths = (exclude_paths or []) + default_exclude_paths
        self.exclude_patterns = [re.compile(pattern) for pattern in self.exclude_paths]

    async def __call__(self, scope, receive, send):
        """Process each request through the middleware."""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive=receive)
        
        # Check if path should be excluded from authentication
        path = request.url.path
        if any(pattern.match(path) for pattern in self.exclude_patterns):
            return await self.app(scope, receive, send)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await self.app(scope, receive, send)

        try:
            # Get the Authorization header
            credentials: HTTPAuthorizationCredentials = await security(request)
            token = credentials.credentials

            # Verify the JWT token
            try:
                decoded_token = verify_token(token)
                # Add the decoded token to request state
                request.state.user = decoded_token
            except Exception as e:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid authentication credentials: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Continue processing the request
            return await self.app(scope, receive, send)

        except HTTPException as http_ex:
            raise http_ex
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"}
            ) 