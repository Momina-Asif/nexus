from django.contrib import admin

# Register your models here.
from django.contrib.auth.models import User  # Import the built-in User model
from .models import Post, UserProfile, Notification, Comment, Message, Story  # Import your custom models

# Check if User is already registered
if not admin.site.is_registered(User):
    admin.site.register(User)

# Register the Post model
admin.site.register(Post)
admin.site.register(UserProfile)
admin.site.register(Notification)
admin.site.register(Comment)
admin.site.register(Message)
admin.site.register(Story)
