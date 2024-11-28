from django.core.files.storage import default_storage
from django.conf import settings
from ninja import Query
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from .models import UserProfile, Post, Notification, Conversation
from ninja import NinjaAPI
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from ninja import Schema, File, Form,  UploadedFile
from typing import Optional
from ninja import Body
from .schema import SearchUserSchema, UnfollowUserSchema, FollowUserSchema, SearchFollowSchema
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
    if not any([username, first_name, last_name, bio, profile_picture, previous_password, new_password]):
        return Response({"error": "No data provided"}, status=400)

    # Validate and update fields
    if username:
        if User.objects.filter(username=username).exclude(id=request.user.id).exists():
            return Response({"error": "Username is already taken"}, status=400)
        request.user.username = username

    if first_name:
        request.user.first_name = first_name

    if last_name:
        request.user.last_name = last_name

    if bio:
        user_profile.bio = bio

    if previous_password and new_password:
        if not request.user.check_password(previous_password):
            return Response({"error": "Previous password is incorrect"}, status=400)
        request.user.set_password(new_password)

    if profile_picture:
        if user_profile.profile_image:
            user_profile.profile_image.delete(
                save=False)  # Delete the old image file

        extension = profile_picture.name.split(".")[-1]
        image_name = f'profile_images/{request.user.id}.{extension}'
        image_path = default_storage.save(
            image_name, ContentFile(profile_picture.read()))
        user_profile.profile_image = image_path

    # Save updated user and profile information
    request.user.save()
    user_profile.save()

    # Define the profile picture URL with a default fallback
    profile_picture_url = (
        user_profile.profile_image.url
        if user_profile.profile_image
        else f"{settings.MEDIA_URL}profile_images/default.png"
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

    # Return an empty array if the username is an empty string
    if not payload.username.strip():
        return Response({"users": []}, status=200)

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
        is_following = request.user.following.filter(id=user.id).exists()

        user_data.append({
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_picture": profile_picture_url,
            "is_following": is_following
        })

    # Return the response with matching users
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
    is_requested = False
    if (request.user in user_profile.pending_requests.all()):
        is_requested = True

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
        "is_requested": is_requested,
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
        unfollowed_user_profile = UserProfile.objects.get(
            user=user_to_unfollow)
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


# @user_router.get("/view-following", auth=JWTAuth())
# def view_following(request, payload: FollowUserSchema) -> Response:
#     # Ensure the user is authenticated
#     if not request.user.is_authenticated:
#         return Response({"error": "Unauthorized"}, status=401)

#     # Extract the username from the payload
#     username = payload.username

#     try:
#         # Fetch the user profile of the requested user
#         user_profile = UserProfile.objects.get(user__username=username)
#     except UserProfile.DoesNotExist:
#         return Response({"error": "User profile not found"}, status=404)

#     # Check if the requested user is followed by the authenticated user or is the authenticated user
#     if request.user == user_profile.user or user_profile.user in request.user.following.all():
#         # Retrieve the following list of the requested user
#         following = user_profile.user.following.all()

#         # Prepare the list of people the user is following with necessary details
#         following_list = []
#         for followed_user in following:
#             followed_user_profile = UserProfile.objects.get(user=followed_user)
#             profile_image_url = (
#                 followed_user_profile.profile_image.url if followed_user_profile.profile_image else f"{
#                     settings.MEDIA_URL}profile_images/default.png"
#             )

#             following_list.append({
#                 "username": followed_user.username,
#                 "user_id": followed_user.id,
#                 "profile_picture": profile_image_url
#             })

#         return Response({
#             "following": following_list
#         }, status=200)
#     else:
#         return Response({"error": "You are not authorized to view this user's following list"}, status=403)


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
            notify_text=f"{
                request.user.username} has sent you a follow request."
        )

        return Response({
            "success": True,
            "message": f"Follow request sent to {user_to_follow.username}."
        }, status=200)

    # Notification.objects.filter(
    #     notify_from=request.user,
    #     notify_to=user_to_follow,
    #     notify_type="follow_request"
    # ).delete()

    followed_user_profile.pending_requests.remove(request.user)
    followed_user_profile.save()
    return Response({
        "success": True,
        "message": f"You have cancelled a follow request to {user_to_follow.username}."
    }, status=200)


@user_router.post("/cancel-request", auth=JWTAuth())
def cancel_request(request, payload: FollowUserSchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Check if the user to follow exists
    try:
        user_to_cancel = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Get the UserProfile objects for both users
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        cancelled_user_profile = UserProfile.objects.get(user=user_to_cancel)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found for one or both users."}, status=404)

    requester = User.objects.get(username=payload.username)

    Notification.objects.filter(
        notify_from=requester,
        notify_to=request.user,
        notify_type="follow_request"
    ).delete()
    user_profile.pending_requests.remove(requester)
    cancelled_user_profile.sent_requests.remove(request.user)
    cancelled_user_profile.save()
    user_profile.save()
    return Response({
        "success": True,
        "message": f"You have cancelled a follow request to {user_to_cancel.username}."
    }, status=200)


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

    # Delete the pending notification (if it exists)
    Notification.objects.filter(
        notify_from=requester,
        notify_to=request.user,
        notify_type="follow_request"
    ).delete()

    # Update follower and following lists
    user_profile.pending_requests.remove(
        requester)  # Remove from pending requests
    user_profile.followers.add(requester)             # Add to followers
    requester_profile = UserProfile.objects.get(user=requester)
    # Add the current user to requester's following
    requester_profile.following.add(request.user)
    requester_profile.sent_requests.remove(request.user)

    user_profile.save()
    requester_profile.save()

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
        notify_text=f"You accepted the follow request from {
            requester.username}"
    )
    existing_conversation = Conversation.objects.filter(
        users=request.user
    ).filter(
        users=requester
    ).first()

    # If no existing conversation is found, create a new one
    if not existing_conversation:
        conversation = Conversation.objects.create()
        conversation.users.add(request.user, requester)
        conversation.save()

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
    notifications = Notification.objects.filter(notify_to=request.user).order_by(
        '-notify_time')  # Get notifications for the user

    # Prepare the response data
    response_data = []

    for notification in notifications:
        profile = UserProfile.objects.get(user=notification.notify_from)
        post_url = None
        if (notification.notify_type == "like" or notification.notify_type == "comment"):
            notified_post = Post.objects.get(
                post_id=notification.notify_post.post_id)
            post_url = notified_post.post_image.url
        response_data.append({
            "notify_from": notification.notify_from.username,
            "notify_text": notification.notify_text,
            # Human-readable time difference
            "notify_date": timesince(notification.notify_time) + " ago",
            "notify_type": notification.notify_type,
            "post_id": notification.notify_post.post_id if notification.notify_post else None,
            "profile_picture": profile.profile_image.url if profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png",
            "post_image": post_url

        })

    return Response(response_data, status=200)


# @user_router.get("/view-followers", auth=JWTAuth())
# def view_followers(request, payload: FollowUserSchema) -> Response:
#     # Ensure the user is authenticated
#     if not request.user.is_authenticated:
#         return Response({"error": "Unauthorized"}, status=401)

#     # Extract the username from the

#     username = payload.username

#     try:
#         # Fetch the user profile of the requested user
#         user_profile = UserProfile.objects.get(user__username=username)
#     except UserProfile.DoesNotExist:
#         return Response({"error": "User profile not found"}, status=404)

#     # Check if the requested user is followed by the authenticated user or is the authenticated user
#     if request.user == user_profile.user or user_profile.user in request.user.following.all():
#         # Retrieve the followers of the requested user
#         followers = user_profile.user.followers.all()

#         # Prepare the list of followers with necessary details
#         followers_list = []
#         for follower in followers:
#             follower_profile = UserProfile.objects.get(user=follower)
#             profile_image_url = (
#                 follower_profile.profile_image.url if follower_profile.profile_image else f"{
#                     settings.MEDIA_URL}profile_images/default.png"
#             )

#             followers_list.append({
#                 "username": follower.username,
#                 "user_id": follower.id,
#                 "profile_image": profile_image_url
#             })

#         return Response({
#             "followers": followers_list
#         }, status=200)
#     else:
#         return Response({"error": "You are not authorized to view this user's followers"}, status=403)


@user_router.post("/search-followers", auth=JWTAuth())
def search_followers_of_user(request, payload: SearchFollowSchema) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        target_user = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    target_user_profile = UserProfile.objects.get(user=target_user)

    followers = target_user_profile.followers.all()

    # Filter the followers list by the search string
    filtered_followers = followers.filter(
        username__icontains=payload.search_string)

    followers_data = []
    for user in filtered_followers:
        user_profile = UserProfile.objects.get(
            user=user) if hasattr(user, 'userprofile') else None
        profile_picture_url = (
            user_profile.profile_image.url
            if user_profile and user_profile.profile_image
            else f"{settings.MEDIA_URL}profile_images/default.png"
        )

        followers_data.append({
            "username": user_profile.user.username,
            "profile_picture": profile_picture_url,
        })

    return Response({"followers": followers_data}, status=200)


@user_router.post("/search-following", auth=JWTAuth())
def search_following_of_user(request, payload: SearchFollowSchema) -> Response:

    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        target_user = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    target_user_profile = UserProfile.objects.get(user=target_user)

    following = target_user_profile.following.all()

    # Filter the following list by the search string
    filtered_following = following.filter(
        username__icontains=payload.search_string)

    following_data = []
    for user in filtered_following:
        user_profile = UserProfile.objects.get(
            user=user) if hasattr(user, 'userprofile') else None
        profile_picture_url = (
            user_profile.profile_image.url
            if user_profile and user_profile.profile_image
            else f"{settings.MEDIA_URL}profile_images/default.png"
        )

        following_data.append({
            "username": user_profile.user.username,
            "profile_picture": profile_picture_url,
        })

    return Response({"following": following_data}, status=200)



@user_router.post("/remove-follower", auth=JWTAuth())
def remove_follower(request, payload: FollowUserSchema) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "UserProfile not found for the requested user."}, status=404)

    try:
        target_user = User.objects.get(username=payload.username)
    except User.DoesNotExist:
        return Response({"error": "Target user not found."}, status=404)

    if target_user in user_profile.followers.all():
        user_profile.followers.remove(target_user)
        
        target_profile = UserProfile.objects.get(user=target_user)
        target_profile.following.remove(request.user)

        return Response({
            "message": f"{payload.username} has been removed from your followers.",
        }, status=200)
    else:
        return Response({
            "message": f"{payload.username} is not in your followers.",
            "followers": [follower.username for follower in user_profile.followers.all()]
        }, status=400)
