# urls.py

from django.urls import path
from .auth import auth_router as authapis

urlpatterns = [
    path("auth/", authapis.urls),
]
