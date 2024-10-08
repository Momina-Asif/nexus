# from django.urls import path
# from .api import api  # Import the NinjaAPI instance
# from .views import signup, login,  protected_view

# urlpatterns = [
#     path("api/", api.urls), 
#     path('api/signup/', signup, name='signup'),
#     path('api/login/', login, name='login'),
#     path('api/token/', api.urls),  # Add the token routes
# ]

# urls.py

from django.urls import path
from .api import api  # Import the NinjaAPI instance

urlpatterns = [
    path("api/", api.urls),  # This will include all routes defined in api.py
]
