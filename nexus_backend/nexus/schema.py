# schemas.py
from ninja import Schema

class SignUpSchema(Schema):
    username: str
    password: str
    email: str



class LoginSchema(Schema):
    username_or_email: str  # Allow either username or email
    password: str