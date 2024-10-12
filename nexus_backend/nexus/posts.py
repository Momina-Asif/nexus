from ninja import NinjaAPI, Schema
from ninja.responses import Response
from ninja import Router
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile, Comment
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema, CommentSchema

post_router = Router()

@post_router.post("/view-comments/", auth=JWTAuth())
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


@post_router.post("/view-likes/", auth=JWTAuth())
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


@post_router.post("/like-post/", auth=JWTAuth())
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

@post_router.post("/unlike-post/", auth=JWTAuth())
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

@post_router.post("/make-comment/", auth=JWTAuth())
def create_comment(request, payload: CommentSchema):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return {"error": "Unauthorized"}, 401
    
    # Retrieve the post using the provided post_id
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return {"error": "Post not found"}, 404

    # Create the comment
    comment = Comment.objects.create(
        comment_post=post,
        comment_user=request.user,
        comment_message=payload.comment_message
    )

    return {
        "success": True,
        "message": "Comment added successfully",
        "comment_id": comment.comment_id,
        "comment_user": comment.comment_user.username,
        "comment_message": comment.comment_message,
        "comment_date": comment.comment_date.isoformat(),
    }


@post_router.delete("/delete-comment/", auth=JWTAuth())
def delete_comment(request, comment_id: int):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return {"error": "Unauthorized"}, 401

    try:
        # Retrieve the comment to be deleted
        comment = Comment.objects.get(comment_id=comment_id)
        
        # Check if the authenticated user is the owner of the comment
        if comment.comment_user != request.user and comment.post.user_id != request.user:
            return {"error": "You do not have permission to delete this comment."}, 403
        
        # Delete the comment
        comment.delete()
        
        return {"success": True, "message": "Comment deleted successfully"}
        
    except Comment.DoesNotExist:
        return {"error": "Comment not found"}, 404