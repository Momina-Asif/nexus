from ninja import NinjaAPI, Schema
from ninja.responses import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema 
from .posts import post_router

# Create an instance of NinjaAPI
hp_router = NinjaAPI(urls_namespace='HPapi')
hp_router.add_router("/post/", post_router)

from django.conf import settings
import os

# @hp_router.get("/posts", auth=JWTAuth())
# def get_homepage_posts(request) -> Response:
#     if not request.user.is_authenticated:
#         return Response({"error": "Unauthorized"}, status=401)

#     # Retrieve the user profile for the authenticated user
#     try:
#         user_profile = UserProfile.objects.get(user=request.user)
#     except UserProfile.DoesNotExist:
#         return Response({"error": "User profile does not exist."}, status=404)

#     # Get the users the authenticated user is following
#     following_users = user_profile.following.all()

#     # Fetch posts from the users that the authenticated user is following
#     posts = Post.objects.filter(user_id__in=following_users).order_by('-post_date')

#     if not posts.exists():
#         return Response({"message": "No posts available."}, status=200)

#     # Construct the response data
#     response_data = []
#     for post in posts:
#         # Manually construct the post image URL based on the post_id
#         post_image_url = None
#         if post.post_image:
#             # Assuming your MEDIA_URL is configured in settings.py
#             post_image_url = os.path.join(settings.MEDIA_URL, f'posts/{post.post_id}/{post.post_id}.{post.post_image.name.split(".")[-1]}')

#         # Add the post data to the response
#         response_data.append({
#             "id": post.post_id,
#             "user": post.user_id.username,
#             "post_image": post_image_url,
#             "created_at": post.post_date.isoformat(),
#             "caption": post.caption,
#         })

#     return Response(response_data, status=200)


@hp_router.get("/posts", auth=JWTAuth())
def get_homepage_posts(request) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the user profile for the authenticated user
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile does not exist."}, status=404)

    # Get the users the authenticated user is following
    following_users = user_profile.following.all()

    # Include the authenticated user's own posts by adding them to the list of following_users
    following_and_self = list(following_users) + [request.user]

    # Fetch posts from both the authenticated user and the users they are following
    posts = Post.objects.filter(user_id__in=following_and_self).order_by('-post_date')

    if not posts.exists():
        return Response({"message": "No posts available."}, status=200)

    # Construct the response data
    response_data = []
    for post in posts:
        # Manually construct the post image URL based on the post_id
        post_image_url = None
        if post.post_image:
            post_image_url = os.path.join(settings.MEDIA_URL, f'posts/{post.post_id}.{post.post_image.name.split(".")[-1]}')

        # Get the number of likes and comments for each post
        likes_count = post.likes_list.count()  
        comments_count = post.comments.count() 

        response_data.append({
            "id": post.post_id,
            "user": post.user_id.username,
            "post_image": post_image_url,
            "created_at": post.post_date.isoformat(),
            "caption": post.caption,
            "likes_count": likes_count,
            "comments_count": comments_count,
        })

    return Response(response_data, status=200)
