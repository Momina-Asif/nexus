from django.core.files.storage import default_storage
from django.conf import settings
from ninja import Query
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from .models import UserProfile, Post
from ninja import NinjaAPI
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from ninja import Schema, File, Form,  UploadedFile
from typing import Optional
from ninja import Body

user_router = NinjaAPI(urls_namespace='userAPI')



user_router = NinjaAPI(urls_namespace='userAPI')

@user_router.post("/edit-profile", auth=JWTAuth())
def edit_profile(request,  
    username: str = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    profile_picture: Optional[UploadedFile] = File(None)) -> Response:
    
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Get the user's profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)
    
    # Check if any data was provided
    if not any([username, first_name, last_name, bio, profile_picture]):
        raise HttpError(status_code=400, detail="Bad request. No data provided.")

    # Update fields if provided in the form data
    if username:
        request.user.username = username
    if first_name:
        request.user.first_name = first_name
    if last_name:
        request.user.last_name = last_name
    if bio:
        user_profile.bio = bio
    if profile_picture:
        # If a profile image exists, delete it
        if user_profile.profile_image:
            user_profile.profile_image.delete(save=False)  # Delete the old image file
        # Save the new image
        image_name = f'profile_images/{request.user.id}.png'
        image_path = default_storage.save(image_name, ContentFile(profile_picture.read()))
        user_profile.profile_image = image_path  # Assign the new image file to the model field
    
    # Save updated user and profile information
    request.user.save()
    user_profile.save()

    # Define the profile picture URL with a default fallback
    profile_picture_url = (
        user_profile.profile_image.url if user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png"
    )

    return Response({
        "success": True,
        "message": "Profile updated successfully",
        "user": {
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "bio": user_profile.bio,
            "profile_picture": profile_picture_url,
        }
    }, status=200)


@user_router.post("/search-user", auth=JWTAuth())
def search_user(request, username: str = Form(...)) -> Response:
    
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)
    
    # Filter users by username containing the search query
    users = User.objects.filter(username__icontains=username)
    
    # Prepare response data including the profile picture
    user_data = []
    for user in users:
        # Check if user has a profile image, otherwise set to default
        user_profile = UserProfile.objects.get(user=user) if hasattr(user, 'userprofile') else None
        profile_picture_url = (
            user_profile.profile_image.url if user_profile and user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png"
        )
        
        user_data.append({
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": profile_picture_url
        })
    
    # Return the response with matching users and status code 200
    return Response({"users": user_data}, status=200)

@user_router.post("/user-profile", auth=JWTAuth())
def user_profile(request, body: dict = Body(...)) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Get the username from the JSON body
    username = body.get('username')
    
    if not username:
        return Response({"error": "Username is required"}, status=400)

    try:
        # Get the user profile by username
        searched_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Get the user profile information
    user_profile = UserProfile.objects.get(user=searched_user)

    # Get the authenticated user's profile to check their followers
    auth_user_profile = UserProfile.objects.get(user=request.user)

    follows_searched_user = request.user in user_profile.followers.all()

    searched_user_follows = searched_user in auth_user_profile.followers.all()

    posts_data = []
    if follows_searched_user or request.user == searched_user:  # Include posts if follows or same user
        posts = Post.objects.filter(user_id=searched_user)
        posts_data = [
            {
                "post_id": post.post_id,
                "post_image": post.post_image.url if post.post_image else f"{settings.MEDIA_URL}posts/default.png"
            }
            for post in posts
        ]

    user_data = {
        "username": searched_user.username,
        "first_name": searched_user.first_name,
        "last_name": searched_user.last_name,
        "bio": user_profile.bio,
        "profile_picture": user_profile.profile_image.url if user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png",
        "posts": posts_data,
        "follows_searched_user": follows_searched_user,
        "searched_user_follows": searched_user_follows
    }

    return Response({"user_profile": user_data}, status=200)
