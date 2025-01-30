from firebase_admin import auth

class AuthService:
    @staticmethod
    def create_user(email, password):
        try:
            user = auth.create_user(
                email=email,
                password=password,
                email_verified=False
            )
            return user
        except auth.AuthError as e:
            raise Exception(f"Authentication error: {str(e)}")

    @staticmethod
    def login_user(email, password):
        try:
            # Note: Firebase Admin SDK cannot verify passwords
            # This should be done using the Firebase Client SDK
            # Here we just verify the user exists
            user = auth.get_user_by_email(email)
            return user
        except auth.AuthError as e:
            raise Exception(f"Authentication error: {str(e)}")

    @staticmethod
    def verify_token(id_token):
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except auth.AuthError as e:
            raise Exception(f"Token verification error: {str(e)}") 