from ninja import NinjaAPI, Router, File, Form, UploadedFile
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from .models import Story, UserProfile, User
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .schema import ViewStorySchema, ViewUserStorySchema, HideUserFromStorySchema, UpdateStoryVisibilitySchema
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

story_router = NinjaAPI(urls_namespace='storyAPI')


@story_router.post("/hide-user-from-story", auth=JWTAuth())
def hide_user_from_story(request, payload: HideUserFromStorySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Extract story ID and user ID from the payload
    story_id = payload.story_id
    user_id = payload.user_id

    try:
        # Fetch the story by story_id
        story = Story.objects.get(story_id=story_id)
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)

    # Ensure the requesting user is the owner of the story or has permission
    if story.story_user != request.user:
        return Response({"error": "You are not authorized to hide users from this story"}, status=403)

    try:
        # Fetch the user to hide from the story
        user_to_hide = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # If the user is already hidden from the story, return a message
    if user_to_hide in story.hidden_from.all():
        return Response({"message": "User is already hidden from this story"}, status=200)

    # Add the user to the hidden_from list of the story
    story.hidden_from.add(user_to_hide)
    story.save()

    return Response({"success": True, "message": f"User {user_to_hide.username} is now hidden from the story"}, status=200)


@story_router.post("/create-story", auth=JWTAuth())
def create_story(request, caption: str = Form(None), post_image: UploadedFile = File()) -> Response:

    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    story = Story.objects.create(story_user=request.user, story_text=caption)

    if post_image:
        ext = post_image.name.split('.')[-1]
        image_name = f'stories/{story.story_id}.{ext}'
        image_path = default_storage.save(
            image_name, ContentFile(post_image.read()))
        story.story_image = image_path
        story.save()

    return Response({
        "success": True,
        "message": "Story created successfully",
        "story_id": story.story_id,
        "story_image": story.story_image.url if story.story_image else None,
        "expiry_time": story.story_time.isoformat(),
    }, status=201)


@story_router.post("/view-stories", auth=JWTAuth())
def get_user_stories(request, payload: ViewUserStorySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Extract username from the payload
    username = payload.username

    try:
        user_profile = UserProfile.objects.get(user__username=username)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)

    # Fetch all stories by the user that are not hidden from the current user
    stories = Story.objects.filter(story_user=user_profile.user).exclude(
        hidden_from=request.user).order_by('story_id')

    # Check if the authenticated user is the owner of the stories
    is_owner = request.user == user_profile.user

    # Count total stories by the user
    total_stories = stories.count()

    # Count how many stories the authenticated user has viewed
    viewed_by_user_count = sum(
        1 for story in stories if request.user in story.viewed_by.all())

    if payload.index >= stories.__len__():
        payload.index = 0

    if stories.exists():
        story = stories[payload.index]

        # Prepare response data
        return Response({
            "username": user_profile.user.username,
            "user_id": user_profile.user.id,
            "total_stories": total_stories,
            "viewed_by_user_count": viewed_by_user_count,
            "id": story.story_id,
            "caption": story.story_text,
            "image": story.story_image.url if story.story_image else None,
            "time": story.story_time.isoformat(),
            "viewed_by_count": story.viewed_by.count() if is_owner else None,
            "is_owner": is_owner
        }, status=200)
    else:
        return Response({"error": "No visible stories found for this user"}, status=404)


@story_router.post("/view-story", auth=JWTAuth())
def mark_story_as_viewed(request, payload: ViewStorySchema) -> Response:
    # Ensure the user is authenticated
    print("IN")
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    # Retrieve the story and viewer user by the provided story_id and username
    try:
        # Fetch the story by its ID
        story = Story.objects.get(pk=payload.story_id)
        # Fetch the user (not UserProfile) by username
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)
    except ObjectDoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Check if the user has already viewed the story
    if story.viewed_by.filter(id=request.user.id).exists():
        return Response({"message": "User has already viewed this story"}, status=200)

    # Add the user to the viewed_by list
    story.viewed_by.add(request.user)
    story.save()

    return Response({
        "success": True,
        "message": f"added to viewed_by list for story {payload.story_id}"
    }, status=200)


@story_router.get("/friends-stories", auth=JWTAuth())
def get_friends_with_stories(request) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Get the user's profile
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)

    # Get the user's friends (people they are following)
    # You can filter this to only the users the current user follows
    # Assuming user_profile is an instance of UserProfile
    friends = list(user_profile.following.all())
    friends.append(request.user)

    friends_with_stories = []
    for friend in friends:
        # Fetch the friend's stories that are NOT hidden from the current user
        stories = Story.objects.filter(
            story_user=friend).exclude(hidden_from=request.user)
        # own_stories = Story.objects.filter(
        #     story_user=request.user)
        # print("OWN", own_stories)

        if stories.exists():
            story_index_to_view = 0
            for story in stories:
                if story.viewed_by.filter(id=request.user.id).exists():
                    story_index_to_view += 1

            # If the friend has posted stories, retrieve their profile
            friend_profile = UserProfile.objects.get(user=friend)

            # Handle the profile image URL
            profile_image_url = (
                friend_profile.profile_image.url if friend_profile.profile_image else f"{
                    settings.MEDIA_URL}profile_images/default.png"
            )

            # Prepare the data for the response
            friends_with_stories.append({
                "username": friend.username,
                "user_id": friend.id,
                "profile_image": profile_image_url,
                "story_index_to_view": story_index_to_view if story_index_to_view < stories.__len__() else 0,
                "yet_to_view": False if story_index_to_view == stories.__len__() else True
            })

    return Response({
        "friends_with_stories": friends_with_stories
    }, status=200)


@story_router.post("/viewers", auth=JWTAuth())
def get_story_viewers(request, payload: ViewStorySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)

    # Check if the authenticated user is the one who posted the story
    if request.user != story.story_user:
        return Response({"error": "You are not authorized to view the viewers of this story"}, status=403)

    # Get the viewers of the story (the users who have viewed the story)
    viewers = story.viewed_by.all()

    # Prepare the response with the usernames of users who have viewed the story
    viewers_list = []
    for viewer in viewers:
        viewer_profile = UserProfile.objects.get(user=viewer)
        profile_image_url = (
            viewer_profile.profile_image.url if viewer_profile.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"
        )
        viewers_list.append({
            "username": viewer.username,
            "profile_picture": profile_image_url
        })

    return Response({
        "story_id": payload.story_id,
        "viewers_list": viewers_list
    }, status=200)


@story_router.post("/visibility", auth=JWTAuth())
def get_story_visibility(request, payload: ViewStorySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Fetch the story by its ID
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)

    # Check if the authenticated user is the one who posted the story
    if request.user != story.story_user:
        return Response({"error": "You are not authorized to view the visibility of this story"}, status=403)

    # Get the story owner's followers
    followers = story.story_user.userprofile.followers.all()

    # Get the users the story is hidden from
    hidden_users = story.hidden_from.all()

    # Prepare the response data
    visibility_data = []
    for follower in followers:
        visibility_data.append({
            "username": follower.username,
            "profile_picture": follower.userprofile.profile_image.url if follower.userprofile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png",
            "is_hidden": follower in hidden_users
        })

    return Response({
        "story_id": payload.story_id,
        "visibility": visibility_data
    }, status=200)


@story_router.post("/update-visibility", auth=JWTAuth())
def update_story_visibility(request, payload: UpdateStoryVisibilitySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Fetch the story by its ID
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)

    # Check if the authenticated user is the one who posted the story
    if request.user != story.story_user:
        return Response({"error": "You are not authorized to update the visibility of this story"}, status=403)

    # Get the current list of users the story is hidden from
    current_hidden_users = set(story.hidden_from.all())

    # Fetch the list of users from the request
    requested_hidden_users = set(User.objects.filter(
        username__in=payload.hidden_usernames))

    # Add the new users to the hidden list
    users_to_hide = requested_hidden_users - current_hidden_users
    story.hidden_from.add(*users_to_hide)

    # Remove users who are no longer in the hidden list
    users_to_unhide = current_hidden_users - requested_hidden_users
    story.hidden_from.remove(*users_to_unhide)

    return Response({
        "success": True,
        "message": "Story visibility updated successfully",
        "hidden_from": [user.username for user in story.hidden_from.all()]
    }, status=200)
