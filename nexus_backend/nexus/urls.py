# urls.py

from django.urls import path
from .auth import auth_router as authapis
from .homepage import hp_router as homepageapi
from .posts import post_router as postsapi
from .story import story_router as storyapi
from .user import user_router as userapi

urlpatterns = [
    path("auth/", authapis.urls),
    path("homepage/", homepageapi.urls),
    path("posts/", postsapi.urls),
    path("story/", storyapi.urls),
    path("user/", userapi.urls),
]
