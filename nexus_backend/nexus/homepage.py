from ninja import NinjaAPI, Schema
from ninja.responses import Response  # Correct way to import Response from ninja
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema 
from .posts import post_router

# Create an instance of NinjaAPI
hp_router = NinjaAPI(urls_namespace='HPapi')
hp_router.add_router("/post/", post_router)

@hp_router.get("/posts/", auth=JWTAuth())
def get_homepage_posts(request):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Get the logged-in user's profile
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile does not exist."}, status=404)

    # Get the list of users that the logged-in user is following
    following_users = user_profile.following.all()

    # Retrieve posts made by followed users
    posts = Post.objects.filter(user_id__in=following_users).order_by('-post_date')

    response_data = [
        {
            "id": post.post_id,
            "user": post.user_id.username,
            "post_image": post.post_image,
            "created_at": post.post_date.isoformat(),
            "caption": post.caption,
        }
        for post in posts
    ]

    return Response(response_data)


@hp_router.post("/view-comments/", auth=JWTAuth())
def get_comments(request, payload: PostSchema):
    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return {"error": "Post not found"}, 404

    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return {"error": "Unauthorized"}, 401


    # Get comments related to the post
    comments = post.comments.all()

    # Prepare the response data
    response_data = [
        {
            "comment_id": comment.comment_id,
            "comment_user": comment.comment_user.username,
            "comment_message": comment.comment_message,
            "comment_date": comment.comment_date.isoformat(),
        }
        for comment in comments
    ]

    return response_data


@hp_router.post("/view-likes/", auth=JWTAuth())
def get_likes(request, payload: PostSchema):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return {"error": "Unauthorized"}, 401

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return {"error": "Post not found"}, 404

    # Get the users who liked the post
    liked_users = post.likes_list.all()

    # Prepare the response data
    response_data = [
        {
            "user_id": user.id,
            "username": user.username,
        }
        for user in liked_users
    ]

    return response_data


@hp_router.post("/like-post/", auth=JWTAuth())
def like_post(request, payload: PostSchema):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return {"error": "Unauthorized"}, 401

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return {"error": "Post not found"}, 404

    # Add the logged-in user to the likes_list of the post
    post.likes_list.add(request.user)

    # Prepare a response message
    return {"success": True, "message": "Post liked successfully"}

@hp_router.post("/unlike-post/", auth=JWTAuth())
def unlike_post(request, payload: PostSchema):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return {"error": "Unauthorized"}, 401

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return {"error": "Post not found"}, 404

    # Remove the logged-in user from the likes_list of the post
    post.likes_list.remove(request.user)

    # Prepare a response message
    return {"success": True, "message": "Post unliked successfully"}

