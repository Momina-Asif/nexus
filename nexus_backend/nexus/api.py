# api.py

from ninja import NinjaAPI, Router
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import signup, login  # Import your view functions
from .schema import SignUpSchema, LoginSchema  # Ensure your schemas are imported correctly

api = NinjaAPI()

# Create a router for JWT authentication routes
jwt_router = Router()

# Define the token routes using the JWT router
@jwt_router.post("/token/")
def token_obtain(request):
    return TokenObtainPairView.as_view()(request)

@jwt_router.post("/token/refresh/")
def token_refresh(request):
    return TokenRefreshView.as_view()(request)

# Add the JWT router to the main API
api.add_router("/auth", jwt_router)

# Define the signup route
@api.post("/signup/")
def user_signup(request, payload: SignUpSchema):
    return signup(request, payload)

# Define the login route
@api.post("/login/")
def user_login(request, payload: LoginSchema):
    return login(request, payload)
