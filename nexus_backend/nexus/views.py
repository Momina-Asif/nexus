from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login as auth_login
from ninja import Schema, Router
from ninja.errors import HttpError
from .schema import SignUpSchema, LoginSchema

router = Router()


#login
@router.post("/login")
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
        auth_login(request, user)
        return {"success": True, "message": "User logged in successfully", "user_id": user.id}
    else:
        raise HttpError(400, "Invalid username/email or password")


#signup
@router.post("/signup/")
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

    return {"success": True, "message": "User created successfully", "user_id": user.id}
