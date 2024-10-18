from ninja import Schema
from typing import Optional

class SignUpSchema(Schema):
    username: str
    email: str
    password: str
    first_name: str
    last_name: Optional[str] = None

class LoginSchema(Schema):
    username_or_email: str  # Allow either username or email
    password: str

class PostSchema(Schema):
    post_id: int

class CommentSchema(Schema):
    post_id: int
    comment_message: str