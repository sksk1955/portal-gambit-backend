# middleware/auth_middleware.py

import logging
import re
from typing import Optional, List

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status
# Import Response and JSONResponse
from starlette.responses import JSONResponse

from utils.jwt_utils import verify_token

security = HTTPBearer()
logger = logging.getLogger(__name__)


class FirebaseAuthMiddleware:
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        """Initialize middleware with optional paths to exclude from authentication."""
        self.app = app
        default_exclude_paths = [
            r"^/auth/token$",
            r"^/$",
            r"^/docs$",
            r"^/openapi.json$",
            r"^/redoc$",
            r"^/favicon\.ico$",
        ]
        self.exclude_paths = (exclude_paths or []) + default_exclude_paths
        self.exclude_patterns = [re.compile(pattern) for pattern in self.exclude_paths]

    async def __call__(self, scope, receive, send):
        """Process each request through the middleware."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path

        if any(pattern.match(path) for pattern in self.exclude_patterns) or request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # --- Explicitly handle potential exceptions from security() and verify_token() ---
        try:
            credentials: HTTPAuthorizationCredentials = await security(request)
            token = credentials.credentials
            decoded_token = verify_token(token)
            request.state.user = decoded_token
            # Proceed only if token is valid
            await self.app(scope, receive, send)

        except HTTPException as http_exc:
            # If security() or verify_token() raised an HTTPException (403 or 401),
            # construct and send the response manually.
            response = JSONResponse(
                status_code=http_exc.status_code,
                content={"detail": http_exc.detail},
                headers=http_exc.headers,  # Include headers like WWW-Authenticate
            )
            await response(scope, receive, send)
            return  # Stop processing here

        except Exception as e:
            # Catch any other unexpected errors during the auth process
            logger.exception(f"Unexpected error during authentication middleware for path {path}: {e}")
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal Server Error during authentication process"},
            )
            await response(scope, receive, send)
            return  # Stop processing here
