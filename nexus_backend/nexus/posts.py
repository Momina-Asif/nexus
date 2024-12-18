from ninja import NinjaAPI, Schema, Router, File, Form, UploadedFile
from ninja.responses import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile, Comment, Notification
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema, CommentSchema, DeleteCommentSchema, DeletePostSchema, EditPostSchema, SearchLikeSchema
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from django.utils import timezone
from django.utils.timesince import timesince
from django.conf import settings


post_router = NinjaAPI(urls_namespace='postAPI')

post_message = "Post Not Found"

@post_router.post("/view-comments", auth=JWTAuth())
def get_comments(request, payload: PostSchema) -> Response:
    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": post_message}, status=404)

    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    comments = Comment.objects.filter(comment_post=post)

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

    return Response(response_data, status=200)


@post_router.post("/get-post", auth=JWTAuth())
def like_post(request, payload: PostSchema) -> Response:
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": post_message}, status=404)
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
    return Response(object_to_return, status=201)


@post_router.post("/toggle-like", auth=JWTAuth())
def like_post(request, payload: PostSchema) -> Response:
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": post_message}, status=404)

    message = ""
    if not post.likes_list.filter(id=request.user.id).exists():
        post.likes_list.add(request.user)
        message = "Post liked successfully"
        Notification.objects.create(
            notify_from=request.user,  
            notify_to=post.user_id,  
            notify_type="like",
            notify_text=f"{request.user.username} liked your post.",
            notify_post=post  
        )
    else:
        post.likes_list.remove(request.user)
        message = "Post unliked successfully"

    post.save()

    return Response({"success": True, "message": message}, status=201)

@post_router.post("/make-comment", auth=JWTAuth())
def create_comment(request, payload: CommentSchema) -> Response:
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": post_message}, status=404)

    comment = Comment.objects.create(
        comment_post=post,
        comment_user=request.user,
        comment_message=payload.comment_message,
        comment_date=timezone.now()
    )

    Notification.objects.create(
        notify_from=request.user,
        notify_to=post.user_id,  
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
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        comment = Comment.objects.get(comment_id=payload.comment_id)

        if comment.comment_user != request.user and comment.comment_post.user_id != request.user:
            return Response({"error": "You do not have permission to delete this comment."}, status=403)

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
        ext = post_image.name.split('.')[-1]  
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
   
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(post_id=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": post_message}, status=404)

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
        return Response({"success": False, "message": post_message}, status=404)

    if post.user_id != request.user:
        return Response({"success": False, "message": "You are not the owner of this post"}, status=403)

    post.caption = payload.caption
    post.save()

    return Response({
        "success": True,
        "message": "Post updated successfully",
        "post_id": post.post_id,
        "new_caption": post.caption
    }, status=200)


@post_router.post("/search-like", auth=JWTAuth())
def search_user_in_post_likes(request, payload: SearchLikeSchema) -> Response:
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        post = Post.objects.get(pk=payload.post_id)
    except Post.DoesNotExist:
        return Response({"error": post_message}, status=404)

    liked_users = post.likes_list.filter(username__icontains=payload.username)

    liked_users_data = []
    for user in liked_users:
        try:
            user_profile = UserProfile.objects.get(user=user)
            profile_image_url = (
                user_profile.profile_image.url if user_profile.profile_image else f"{
                    settings.MEDIA_URL}profile_images/default.png"
            )
        except UserProfile.DoesNotExist:
            profile_image_url = f"{
                settings.MEDIA_URL}profile_images/default.png"

        liked_users_data.append({
            "username": user.username,
            "profile_picture": profile_image_url,
        })

    return Response({
        "success": True,
        "liked_users": liked_users_data
    }, status=200)
