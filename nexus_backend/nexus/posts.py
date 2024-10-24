from ninja import NinjaAPI, Schema, Router, File, Form, UploadedFile
from ninja.responses import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile, Comment
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema, CommentSchema
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

post_router = Router()

@post_router.post("/view-comments", auth=JWTAuth())
def get_comments(request, payload: PostSchema) -> Response:
    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

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

    return Response(response_data, status=200)


@post_router.post("/view-likes", auth=JWTAuth())
def get_likes(request, payload: PostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

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

    return Response(response_data, status=200)


@post_router.post("/like-post", auth=JWTAuth())
def like_post(request, payload: PostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    # Add the logged-in user to the likes_list of the post
    post.likes_list.add(request.user)

    # Prepare a response message
    return Response({"success": True, "message": "Post liked successfully"}, status=201)

@post_router.post("/unlike-post", auth=JWTAuth())
def unlike_post(request, payload: PostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    # Remove the logged-in user from the likes_list of the post
    post.likes_list.remove(request.user)

    # Prepare a response message
    return Response({"success": True, "message": "Post unliked successfully"}, status=200)

@post_router.post("/make-comment", auth=JWTAuth())
def create_comment(request, payload: CommentSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)
    
    # Retrieve the post using the provided post_id
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    # Create the comment
    comment = Comment.objects.create(
        comment_post=post,
        comment_user=request.user,
        comment_message=payload.comment_message
    )

    return Response({
        "success": True,
        "message": "Comment added successfully",
        "comment_id": comment.comment_id,
        "comment_user": comment.comment_user.username,
        "comment_message": comment.comment_message,
        "comment_date": comment.comment_date.isoformat(),
    }, status=201)


@post_router.delete("/delete-comment", auth=JWTAuth())
def delete_comment(request, comment_id: int) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Retrieve the comment to be deleted
        comment = Comment.objects.get(comment_id=comment_id)
        
        # Check if the authenticated user is the owner of the comment
        if comment.comment_user != request.user and comment.comment_post.user_id != request.user.id:
            return Response({"error": "You do not have permission to delete this comment."}, status=403)
        
        # Delete the comment
        comment.delete()
        
        return Response({"success": True, "message": "Comment deleted successfully"}, status=204)
        
    except Comment.DoesNotExist:
        return Response({"error": "Comment not found"}, status=404)

@post_router.post("/create-post", auth=JWTAuth())
def create_post(request, caption: str = Form(None), post_image: UploadedFile = File(None)) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Create the post first to get the post ID
    post = Post.objects.create(user_id=request.user, caption=caption)

    # Save the uploaded image with the post ID as the filename
    if post_image:
        ext = post_image.name.split('.')[-1]  # Get file extension
        image_name = f'posts/{post.post_id}.{ext}'
        image_path = default_storage.save(image_name, ContentFile(post_image.read()))
        post.post_image = image_path
        post.save()  # Save the post again with the updated image path

    return Response({
        "success": True,
        "message": "Post created successfully",
        "post_id": post.post_id,
        "post_image": post.post_image.url if post.post_image else None
    }, status=201)
