from django.urls import path
from .api import api  # Import the NinjaAPI instance
from .views import signup, login

urlpatterns = [
    path("api/", api.urls), 
    path('api/signup/', signup, name='signup'),
    path('api/login/', login, name='login'),
]
