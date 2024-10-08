from django.contrib import admin

# Register your models here.
from django.contrib.auth.models import User  # Import the built-in User model
from .models import Post, UserProfile  # Import your custom models

# Check if User is already registered
if not admin.site.is_registered(User):
    admin.site.register(User)

# Register the Post model
admin.site.register(Post)
admin.site.register(UserProfile)
