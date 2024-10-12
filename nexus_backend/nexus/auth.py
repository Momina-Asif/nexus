from ninja import NinjaAPI, Router
from .schema import SignUpSchema, LoginSchema  # Ensure your schemas are imported correctly
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from ninja.errors import HttpError

auth_router = NinjaAPI(urls_namespace='authapi')

# Define the signup route
@auth_router.post("/signup/")
def signup(request, payload: SignUpSchema):
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, "Username already taken")

    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Email already in use")

    user = User.objects.create(
        username=payload.username,
        password=make_password(payload.password),
        email=payload.email,
    )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    return {
        "success": True,
        "message": "User created successfully",
        "user_id": user.id,
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

# Define the login route
@auth_router.post("/login/")
def login(request, payload: LoginSchema):
    username_or_email = payload.username_or_email
    password = payload.password

    # Check if the input is an email or username
    if '@' in username_or_email:
        try:
            user = User.objects.get(email=username_or_email)
            user = authenticate(username=user.username, password=password)
        except User.DoesNotExist:
            raise HttpError(400, "Invalid email or password")
    else:
        user = authenticate(username=username_or_email, password=password)

    if user is not None:
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return {
            "success": True,
            "message": "User logged in successfully",
            "user_id": user.id,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
    else:
        raise HttpError(400, "Invalid username/email or password")

