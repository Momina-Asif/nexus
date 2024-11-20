from ninja import NinjaAPI, Router
from ninja.responses import Response  # Correct import for Response
from .schema import SignUpSchema, LoginSchema
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile
from django.conf import settings

auth_router = NinjaAPI(urls_namespace='authapi')

# Define the signup route


@auth_router.post("/signup", response={201: dict, 400: dict})
def signup(request, payload: SignUpSchema):
    print("IN")
    if User.objects.filter(username=payload.username).exists():
        return Response({"success": False, "message": "Username already taken"}, status=400)

    if User.objects.filter(email=payload.email).exists():
        return Response({"success": False, "message": "Email already in use"}, status=400)

    # Create the user
    user = User.objects.create(
        username=payload.username,
        password=make_password(payload.password),
        email=payload.email,
    )

    # Create the user profile
    user_profile_data = {}
    if payload.first_name:
        user_profile_data['first_name'] = payload.first_name
    if payload.last_name:
        user_profile_data['last_name'] = payload.last_name

    UserProfile.objects.create(user=user, **user_profile_data)

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    return Response({
        "success": True,
        "message": "User created successfully",
        "user_id": user.id,
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }, status=201)

# Define the login route


@auth_router.post("/login", response={200: dict, 401: dict, 404: dict})
def login(request, payload: LoginSchema):
    username_or_email = payload.username_or_email
    password = payload.password

    if '@' in username_or_email:
        try:
            user = User.objects.get(email=username_or_email)
            user = authenticate(username=user.username, password=password)
            if user is None:
                return Response({"success": False, "message": "Invalid password"}, status=401)
        except User.DoesNotExist:
            return Response({"success": False, "message": "Email not found"}, status=404)
    else:
        user = authenticate(username=username_or_email, password=password)
        if user is None:
            if User.objects.filter(username=username_or_email).exists():
                return Response({"success": False, "message": "Invalid password"}, status=401)
            else:
                return Response({"success": False, "message": "Username not found"}, status=404)

    # If authentication is successful
    refresh = RefreshToken.for_user(user)

    # Fetch user profile and profile picture
    try:
        user_profile = UserProfile.objects.get(user=user)
        profile_picture_url = (
            user_profile.profile_image.url if user_profile.profile_image
            else f"{settings.MEDIA_URL}profile_images/default.png"
        )
    except UserProfile.DoesNotExist:
        profile_picture_url = f"{settings.MEDIA_URL}profile_images/default.png"

    return Response({
        "success": True,
        "message": "User logged in successfully",
        "username": user.username,
        "profile_picture": profile_picture_url,
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }, status=200)



@auth_router.post("/logout", response={200: dict, 400: dict})
def logout(request):
    # Get the token from the Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            refresh_token = RefreshToken(token)
            # Blacklist the refresh token
            refresh_token.blacklist()
            return Response({"success": True, "message": "Logged out successfully"}, status=200)
        except Exception as e:
            return Response({"success": False, "message": "Invalid token or unable to blacklist"}, status=400)
    else:
        return Response({"success": False, "message": "Authorization header is missing or invalid"}, status=400)
