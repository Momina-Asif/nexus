from ninja import NinjaAPI
from .views import signup, login
from .schema import SignUpSchema, LoginSchema

api = NinjaAPI()

# Define the signup route
@api.post("/signup/")
def user_signup(request, payload: SignUpSchema):
    return signup(request, payload)

@api.post("/login/")
def user_login(request, payload: LoginSchema):
    return login(request, payload)