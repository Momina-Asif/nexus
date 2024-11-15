from django.core.files.storage import default_storage
from django.conf import settings
from ninja import Query
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from .models import UserProfile, Post, Notification
from ninja import NinjaAPI
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from ninja import Schema, File, Form,  UploadedFile
from typing import Optional
from ninja import Body
from .schema import SearchUserSchema, UnfollowUserSchema, FollowUserSchema
from django.contrib.auth.hashers import make_password
from django.utils.timesince import timesince

user_router = NinjaAPI(urls_namespace='userAPI')


user_router = NinjaAPI(urls_namespace='userAPI')


@user_router.post("/edit-profile", auth=JWTAuth())
def edit_profile(request,
                 username: str = Form(None),
                 first_name: Optional[str] = Form(None),
                 last_name: Optional[str] = Form(None),
                 bio: Optional[str] = Form(None),
                 previous_password: Optional[str] = Form(None),
                 new_password: Optional[str] = Form(None),
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
        raise HttpError(status_code=400,
                        detail="Bad request. No data provided.")

    print(profile_picture)

    # Update fields if provided in the form data
    if username:
        request.user.username = username
    if first_name:
        request.user.first_name = first_name
    if last_name:
        request.user.last_name = last_name
    if bio:
        user_profile.bio = bio
    if previous_password and new_password:
        if (previous_password == request.user.password):
            request.user.password = make_password(new_password)
        # else:
            # send an appropriate error respone
    if profile_picture:
        # If a profile image exists, delete it
        if user_profile.profile_image:
            user_profile.profile_image.delete(
                save=False)  # Delete the old image file
        # Save the new image
        image_name = f'profile_images/{request.user.id}.png'
        image_path = default_storage.save(
            image_name, ContentFile(profile_picture.read()))
        # Assign the new image file to the model field

        user_profile.profile_image = image_path

    # Save updated user and profile information
    request.user.save()
    user_profile.save()

    # Define the profile picture URL with a default fallback
    profile_picture_url = (
        user_profile.profile_image.url if user_profile.profile_image else f"{
            settings.MEDIA_URL}profile_images/default.png"
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
def search_user(request, payload: SearchUserSchema) -> Response:

    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Filter users by username containing the search query
    users = User.objects.filter(username__icontains=payload.username)

    # Prepare response data including the profile picture
    user_data = []
    for user in users:
        # Check if user has a profile image, otherwise set to default
        user_profile = UserProfile.objects.get(
            user=user) if hasattr(user, 'userprofile') else None
        profile_picture_url = (
            user_profile.profile_image.url if user_profile and user_profile.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"
        )
        is_following = False
        if (request.user.following.filter(id=user.id).exists()):
            is_following = True

        user_data.append({
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": profile_picture_url,
            "is_following": is_following
        })

    # Return the response with matching users and status code 200
    return Response({"users": user_data}, status=200)


@user_router.post("/user-profile", auth=JWTAuth())
def user_profile(request, payload: SearchUserSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Get the username from the JSON body
    username = payload.username

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

    followers_count = user_profile.followers.all().count()
    following_count = user_profile.following.all().count()

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

    user_is_himself = False
    if (request.user == searched_user):
        user_is_himself = True

    user_data = {
        "username": searched_user.username,
        "first_name": searched_user.first_name,
        "last_name": searched_user.last_name,
        "bio": user_profile.bio,
        "profile_picture": user_profile.profile_image.url if user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png",
        "posts": posts_data,
        "follows_searched_user": follows_searched_user,
        "searched_user_follows": searched_user_follows,
        "user_is_himself": user_is_himself,
        "followers_count": followers_count,
        "following_count": following_count
    }

    return Response({"user_profile": user_data}, status=200)


@user_router.post("/unfollow", auth=JWTAuth())
def unfollow_user(request, payload: UnfollowUserSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Check if the user exists
    try:
        user_to_unfollow = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Ensure the authenticated user is not unfollowing themselves
    if user_to_unfollow == request.user:
        return Response({"error": "You cannot unfollow yourself."}, status=400)

    # Get the UserProfile objects for both users
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        unfollowed_user_profile = UserProfile.objects.get(user=user_to_unfollow)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found for one or both users."}, status=404)

    # Remove the user from the following and followers lists
    if user_to_unfollow in user_profile.following.all():
        user_profile.following.remove(user_to_unfollow)
    if request.user in unfollowed_user_profile.followers.all():
        unfollowed_user_profile.followers.remove(request.user)

    return Response({
        "success": True,
        "message": f"You have successfully unfollowed {user_to_unfollow.username}."
    }, status=200)

@user_router.get("/view-following", auth=JWTAuth())
def view_following(request, payload: FollowUserSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Extract the username from the payload
    username = payload.username

    try:
        # Fetch the user profile of the requested user
        user_profile = UserProfile.objects.get(user__username=username)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)

    # Check if the requested user is followed by the authenticated user or is the authenticated user
    if request.user == user_profile.user or user_profile.user in request.user.following.all():
        # Retrieve the following list of the requested user
        following = user_profile.user.following.all()

        # Prepare the list of people the user is following with necessary details
        following_list = []
        for followed_user in following:
            followed_user_profile = UserProfile.objects.get(user=followed_user)
            profile_image_url = (
                followed_user_profile.profile_image.url if followed_user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png"
            )

            following_list.append({
                "username": followed_user.username,
                "user_id": followed_user.id,
                "profile_image": profile_image_url
            })

        return Response({
            "following": following_list
        }, status=200)
    else:
        return Response({"error": "You are not authorized to view this user's following list"}, status=403)


@user_router.post("/follow", auth=JWTAuth())
def follow_user(request, payload: FollowUserSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Check if the user to follow exists
    try:
        user_to_follow = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Ensure the authenticated user is not trying to follow themselves
    if user_to_follow == request.user:
        return Response({"error": "You cannot follow yourself."}, status=400)

    # Get the UserProfile objects for both users
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        followed_user_profile = UserProfile.objects.get(user=user_to_follow)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found for one or both users."}, status=404)

    # Add the authenticated user to the pending_requests of the target user
    if request.user not in followed_user_profile.pending_requests.all():
        followed_user_profile.pending_requests.add(request.user)
        followed_user_profile.save()

        # Create a notification
        Notification.objects.create(
            notify_from=request.user,
            notify_to=user_to_follow,
            notify_type="follow_request",
            notify_text=f"{request.user.username} has sent you a follow request."
        )

        return Response({
            "success": True,
            "message": f"Follow request sent to {user_to_follow.username}."
        }, status=200)

    return Response({
        "success": False,
        "message": f"You have already sent a follow request to {user_to_follow.username}."
    }, status=400)


@user_router.post("/accept-follow-request", auth=JWTAuth())
def accept_follow_request(request, payload: FollowUserSchema) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Fetch the user who sent the follow request
        requester = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"success": False, "message": "Requester not found"}, status=404)

    try:
        # Fetch the profile of the current user
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"success": False, "message": "User profile not found"}, status=404)

    # Check if the requester is in the pending_requests list
    if requester not in user_profile.pending_requests.all():
        return Response({"success": False, "message": "No follow request from this user"}, status=400)

    # Update follower and following lists
    user_profile.pending_requests.remove(requester)  # Remove from pending requests
    user_profile.followers.add(requester)           # Add to followers
    requester_profile = UserProfile.objects.get(user=requester)
    requester_profile.following.add(request.user)   # Add the current user to requester's following

    # Create a notification for the requester
    Notification.objects.create(
        notify_from=request.user,
        notify_to=requester,
        notify_type="Follow Accepted",
        notify_text=f"{request.user.username} accepted your follow request"
    )

    # Create a notification for the user who accepted the request
    Notification.objects.create(
        notify_from=requester,
        notify_to=request.user,
        notify_type="Follow Request Accepted",
        notify_text=f"You accepted the follow request from {requester.username}"
    )

    return Response({
        "success": True,
        "message": f"You have accepted the follow request from {payload.username}",
    }, status=200)


@user_router.get("/view-notifications", auth=JWTAuth())
def view_notifications(request) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)
    
    # Retrieve notifications for the authenticated user
    notifications = Notification.objects.filter(notify_to=request.user).order_by('-notify_date')  # Get notifications for the user
    
    # Prepare the response data
    response_data = [
        {
            "notification_id": notification.id,
            "notify_from": notification.notify_from.username,
            "notify_text": notification.notify_text,
            "notify_date": timesince(notification.notify_date) + " ago",  # Human-readable time difference
            "notify_type": notification.notify_type,
            "post_id": notification.notify_post.post_id if notification.notify_post else None
        }
        for notification in notifications
    ]
    
    return Response(response_data, status=200)

@user_router.get("/view-followers", auth=JWTAuth())
def view_followers(request, payload: FollowUserSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Extract the username from the 
    
    username = payload.username

    try:
        # Fetch the user profile of the requested user
        user_profile = UserProfile.objects.get(user__username=username)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)

    # Check if the requested user is followed by the authenticated user or is the authenticated user
    if request.user == user_profile.user or user_profile.user in request.user.following.all():
        # Retrieve the followers of the requested user
        followers = user_profile.user.followers.all()

        # Prepare the list of followers with necessary details
        followers_list = []
        for follower in followers:
            follower_profile = UserProfile.objects.get(user=follower)
            profile_image_url = (
                follower_profile.profile_image.url if follower_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png"
            )

            followers_list.append({
                "username": follower.username,
                "user_id": follower.id,
                "profile_image": profile_image_url
            })

        return Response({
            "followers": followers_list
        }, status=200)
    else:
        return Response({"error": "You are not authorized to view this user's followers"}, status=403)
