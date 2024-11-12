from ninja import NinjaAPI, Schema
from ninja.responses import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema 
from .posts import post_router

# Create an instance of NinjaAPI
hp_router = NinjaAPI(urls_namespace='HPapi')

from django.conf import settings
import os


@hp_router.get("/posts", auth=JWTAuth())
def get_homepage_posts(request) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile does not exist."}, status=404)

    following_users = user_profile.following.all()

    following_and_self = list(following_users) + [request.user]

    posts = Post.objects.filter(user_id__in=following_and_self).order_by('-post_date')

    if not posts.exists():
        return Response({"message": "No posts available."}, status=200)

    response_data = []
    for post in posts:
        post_image_url = None
        if post.post_image:
            post_image_url = os.path.join(settings.MEDIA_URL, f'posts/{post.post_id}.{post.post_image.name.split(".")[-1]}')

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
