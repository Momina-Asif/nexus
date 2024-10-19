# urls.py

from django.urls import path
from .auth import auth_router as authapis
from .homepage import hp_router as homepageapi
from .create import create_router as createapi

urlpatterns = [
    path("auth/", authapis.urls),
    path("homepage/", homepageapi.urls),
    path("create/", createapi.urls),
]
