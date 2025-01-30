from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel

from app.controllers.auth_controller import AuthController
from app.middleware.auth_middleware import require_auth

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserCredentials(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        user = auth.create_user(email=email, password=password)
        return JSONResponse({"message": "User created successfully", "uid": user.uid})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(credentials: UserCredentials):
    try:
        return await AuthController.login(credentials.email, credentials.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Example of a protected route
@router.get("/me")
@require_auth
def get_user_profile():
    return {'user': request.user}, 200
