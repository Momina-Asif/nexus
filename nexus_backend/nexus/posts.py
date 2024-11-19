from ninja import NinjaAPI, Schema, Router, File, Form, UploadedFile
from ninja.responses import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile, Comment, Notification
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema, CommentSchema, DeleteCommentSchema, DeletePostSchema, EditPostSchema
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from django.utils import timezone
from django.utils.timesince import timesince
from django.conf import settings


post_router = NinjaAPI(urls_namespace='postAPI')


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
    comments = Comment.objects.filter(comment_post=post)
    print("COM", comments)

    # Prepare the response data
    response_data = []
    for comment in comments:
        commented_by = UserProfile.objects.get(user=comment.comment_user)

        profile_picture_url = (
            commented_by.profile_image.url if commented_by.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"

        )
        time_ago = timesince(comment.comment_date)
        response_data.append({
            "comment_id": comment.comment_id,
            "comment_user": comment.comment_user.username,
            "comment_message": comment.comment_message,
            "time_lapsed": time_ago,
            "profile_picture": profile_picture_url,
            "is_owner": True if comment.comment_user == request.user or request.user == post.user_id else False
        })

    # response_data = [
        # {
        #     "comment_id": comment.comment_id,
        #     "comment_user": comment.comment_user.username,
        #     "comment_message": comment.comment_message,
        #     "comment_date": comment.comment_date.isoformat(),
        # }
    #     for comment in comments
    # ]

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

    response_data = []

    for user in liked_users:
        liked_user_profile = UserProfile.objects.get(user=user)
        profile_image_url = (
            liked_user_profile.profile_image.url if liked_user_profile.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"
        )
        response_data.append({
            "username": user.username,
            "profile_picture": profile_image_url
        })

    # Prepare the response data

    return Response(response_data, status=200)


@post_router.post("/get-post", auth=JWTAuth())
def like_post(request, payload: PostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)
    post_image_url = os.path.join(
        settings.MEDIA_URL, f'posts/{post.post_id}.{post.post_image.name.split(".")[-1]}')

    likes_count = post.likes_list.count()
    current_user_has_liked = False
    if (post.likes_list.filter(id=request.user.id).exists()):
        current_user_has_liked = True

    user_profile = UserProfile.objects.get(user=post.user_id)
    profile_picture_url = (
        user_profile.profile_image.url if user_profile.profile_image else f"{
            settings.MEDIA_URL}profile_images/default.png"
    )

    object_to_return = {
        "id": post.post_id,
        "user": post.user_id.username,
        "post_image": post_image_url,
        "created_at": timesince(post.post_date),
        "caption": post.caption,
        "likes_count": likes_count,
        "has_liked": current_user_has_liked,
        "profile_picture": profile_picture_url,
        "is_owner": True if post.user_id == request.user else False
    }

    # Add the logged-in user to the likes_list of the post

    # Prepare a response message
    return Response(object_to_return, status=201)


@post_router.post("/toggle-like", auth=JWTAuth())
def like_post(request, payload: PostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the post using the provided post_id from the payload
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    # Add or remove the logged-in user to the likes_list of the post
    message = ""
    if not post.likes_list.filter(id=request.user.id).exists():
        post.likes_list.add(request.user)
        message = "Post liked successfully"
        Notification.objects.create(
            notify_from=request.user,  # The user who liked the post
            notify_to=post.user_id,  # The post owner
            notify_type="like",
            notify_text=f"{request.user.username} liked your post.",
            notify_post=post  # Link to the post
        )
    else:
        post.likes_list.remove(request.user)
        message = "Post unliked successfully"

    post.save()

    # Prepare a response message
    return Response({"success": True, "message": message}, status=201)


# @post_router.post("/unlike-post", auth=JWTAuth())
# def unlike_post(request, payload: PostSchema) -> Response:
#     # Ensure the user is authenticated
#     if not request.user.is_authenticated:
#         return Response({"error": "Unauthorized"}, status=401)

#     # Retrieve the post using the provided post_id from the payload
#     try:
#         post = Post.objects.get(post_id=payload.post_id)
#     except Post.DoesNotExist:
#         return Response({"error": "Post not found"}, status=404)

#     # Remove the logged-in user from the likes_list of the post
#     post.likes_list.remove(request.user)

#     # Prepare a response message
#     return Response({"success": True, "message": "Post unliked successfully"}, status=200)

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
        comment_message=payload.comment_message,
        comment_date=timezone.now()
    )

    # Create the notification for the post owner
    notification = Notification.objects.create(
        notify_from=request.user,
        notify_to=post.user_id,  # The post owner gets the notification
        notify_type="comment",
        notify_text=f"{request.user.username} commented on your post: {
            payload.comment_message}",
        notify_post=post
    )

    return Response({
        "success": True,
        "message": "Comment added successfully",
        "comment_id": comment.comment_id,
        "comment_user": comment.comment_user.username,
        "comment_message": comment.comment_message,
        "time_lapsed": timesince(comment.comment_date)
    }, status=201)


@post_router.post("/delete-comment", auth=JWTAuth())
def delete_comment(request, payload: DeleteCommentSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Retrieve the comment to be deleted
        comment = Comment.objects.get(comment_id=payload.comment_id)

        # Check if the authenticated user is the owner of the comment
        if comment.comment_user != request.user and comment.comment_post.user_id != request.user:
            return Response({"error": "You do not have permission to delete this comment."}, status=403)

        # Delete the comment
        comment.delete()

        return Response({"success": True, "message": "Comment deleted successfully"}, status=201)

    except Comment.DoesNotExist:
        return Response({"error": "Comment not found"}, status=404)


@post_router.post("/create-post", auth=JWTAuth())
def create_post(request, caption: str = Form(None), post_image: UploadedFile = File(None)) -> Response:

    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    post = Post.objects.create(user_id=request.user, caption=caption)

    if post_image:
        ext = post_image.name.split('.')[-1]  # Get file extension
        image_name = f'posts/{post.post_id}.{ext}'
        image_path = default_storage.save(
            image_name, ContentFile(post_image.read()))
        post.post_image = image_path
        post.save()

    return Response({
        "success": True,
        "message": "Post created successfully",
        "post_id": post.post_id,
        "post_image": post.post_image.url if post.post_image else None
    }, status=201)


@post_router.post("/delete-post", auth=JWTAuth())
def delete_post(request, payload: DeletePostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    if post.user_id != request.user:
        return Response({"error": "You are not authorized to delete this post"}, status=403)

    if post.post_image:
        post.post_image.delete(save=False)

    post.delete()

    return Response({
        "success": True,
        "message": "Post deleted successfully",
        "post_id": payload.post_id
    }, status=200)


@post_router.post("/edit-post", auth=JWTAuth())
def edit_post(request, payload: EditPostSchema) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"success": False, "message": "Post not found"}, status=404)

    # Check if the current user is the owner of the post
    if post.user_id != request.user:
        return Response({"success": False, "message": "You are not the owner of this post"}, status=403)

    # Update the caption
    post.caption = payload.caption
    post.save()

    return Response({
        "success": True,
        "message": "Post updated successfully",
        "post_id": post.post_id,
        "new_caption": post.caption
    }, status=200)


@post_router.post("/search-like", auth=JWTAuth())
def search_user_in_post_likes(request, payload: PostSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Fetch the post by its ID
        post = Post.objects.get(pk=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=404)

    # Search for users in the likes of the post
    liked_users = post.likes_list.filter(username__icontains=payload.username)

    liked_users_data = []
    for user in liked_users:
        try:
            user_profile = UserProfile.objects.get(user=user)
            profile_image_url = (
                user_profile.profile_image.url if user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png"
            )
        except UserProfile.DoesNotExist:
            profile_image_url = f"{settings.MEDIA_URL}profile_images/default.png"

        liked_users_data.append({
            "username": user.username,
            "first_name": user_profile.first_name if user_profile else "User",
            "last_name": user_profile.last_name if user_profile else "",
            "profile_image": profile_image_url,
        })

    return Response({
        "success": True,
        "liked_users": liked_users_data
    }, status=200)


