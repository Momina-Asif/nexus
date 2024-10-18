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

@hp_router.get("/posts", auth=JWTAuth())
def get_homepage_posts(request) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile does not exist."}, status=404)

    following_users = user_profile.following.all()

    posts = Post.objects.filter(user_id__in=following_users).order_by('-post_date')

    response_data = [
        {
            "id": post.post_id,
            "user": post.user_id.username,
            "post_image": post.post_image.url if post.post_image else None,  # Ensure post_image is URL
            "created_at": post.post_date.isoformat(),
            "caption": post.caption,
        }
        for post in posts
    ]

    return Response(response_data, status=200)
