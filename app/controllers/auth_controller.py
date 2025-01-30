from app.services.auth_service import AuthService

class AuthController:
    @staticmethod
    async def signup(email: str, password: str):
        try:
            user = await AuthService.create_user(email, password)
            return {"message": "User created successfully", "uid": user.uid}
        except Exception as e:
            raise Exception(str(e))

    @staticmethod
    async def login(email: str, password: str):
        try:
            user = await AuthService.login_user(email, password)
            return {"message": "User logged in successfully", "uid": user.uid}
        except Exception as e:
            raise Exception(str(e)) 