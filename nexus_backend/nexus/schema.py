from ninja import Schema, File, Form,  UploadedFile
from typing import Optional
from ninja.files import UploadedFile
from typing import List

class EditUserSchema(Schema):
    username: str = Form(None)
    first_name: Optional[str] = Form(None)
    last_name: Optional[str] = Form(None)
    bio: Optional[str] = Form(None)
    profile_picture: Optional[UploadedFile] = File(None)


class SignUpSchema(Schema):
    username: str
    email: str
    password: str
    first_name: str
    last_name: Optional[str] = None


class LoginSchema(Schema):
    username_or_email: str
    password: str


class PostSchema(Schema):
    post_id: int


class CommentSchema(Schema):
    post_id: int
    comment_message: str

class DeletePostSchema(Schema):
    post_id: int


class DeleteCommentSchema(Schema):
    comment_id: int


class ViewStorySchema(Schema):
    story_id: int


class ViewUserStorySchema(Schema):
    username: str
    index: int


class SearchUserSchema(Schema):
    username: str

class UnfollowUserSchema(Schema):
    username: str

class FollowUserSchema(Schema):
    username: str


class EditPostSchema(Schema):
    post_id: int 
    caption: str


class HideUserFromStorySchema(Schema):
    story_id: int
    user_id: int


class SearchFollowSchema(Schema):
    username: str
    search_string: str

class UpdateStoryVisibilitySchema(Schema):
    story_id: int
    hidden_usernames: List[str] 

class SearchViewerSchema(Schema):
    story_id: int
    username: str


