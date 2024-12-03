from ninja import NinjaAPI, Router, File, Form, UploadedFile
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from .models import Story, UserProfile, User
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .schema import ViewStorySchema, ViewUserStorySchema, HideUserFromStorySchema, UpdateStoryVisibilitySchema, SearchViewerSchema
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

story_router = NinjaAPI(urls_namespace='storyAPI')

story_message = "Story Not Found"

@story_router.post("/hide-user-from-story", auth=JWTAuth())
def hide_user_from_story(request, payload: HideUserFromStorySchema) -> Response:
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    story_id = payload.story_id
    user_id = payload.user_id

    try:
        story = Story.objects.get(story_id=story_id)
    except Story.DoesNotExist:
        return Response({"error": story_message}, status=404)

    if story.story_user != request.user:
        return Response({"error": "You are not authorized to hide users from this story"}, status=403)

    try:
        user_to_hide = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    if user_to_hide in story.hidden_from.all():
        return Response({"message": "User is already hidden from this story"}, status=200)

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
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    username = payload.username

    try:
        user_profile = UserProfile.objects.get(user__username=username)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)

    stories = Story.objects.filter(story_user=user_profile.user).exclude(
        hidden_from=request.user).order_by('story_id')

    is_owner = request.user == user_profile.user

    total_stories = stories.count()

    viewed_by_user_count = sum(
        1 for story in stories if request.user in story.viewed_by.all())

    if payload.index >= stories.__len__():
        payload.index = 0

    if stories.exists():
        story = stories[payload.index]
        user_profile_image_url = (
            user_profile.profile_image.url if user_profile.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"
            )

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
            "profile_image": user_profile_image_url,
            "is_owner": is_owner
        }, status=200)
    else:
        return Response({"error": "No visible stories found for this user"}, status=404)


@story_router.post("/view-story", auth=JWTAuth())
def mark_story_as_viewed(request, payload: ViewStorySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
       
        story = Story.objects.get(pk=payload.story_id)
       
    except Story.DoesNotExist:
        return Response({"error": story_message}, status=404)
    except ObjectDoesNotExist:
        return Response({"error": "User not found"}, status=404)

    if story.viewed_by.filter(id=request.user.id).exists():
        return Response({"message": "User has already viewed this story"}, status=200)

    story.viewed_by.add(request.user)
    story.save()

    return Response({
        "success": True,
        "message": f"added to viewed_by list for story {payload.story_id}"
    }, status=200)


@story_router.get("/friends-stories", auth=JWTAuth())
def get_friends_with_stories(request) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=404)

    friends_with_stories = []

    user_stories = get_user_stories(request.user)

    if user_stories.exists():
        friends_with_stories.append({
            "username": request.user.username,
            "user_id": request.user.id,
            "profile_image": get_profile_image_url(user_profile),
            "story_index_to_view": get_story_index_to_view(user_stories, request.user),
            "yet_to_view": has_unviewed_stories(user_stories, request.user)
        })

    friends = user_profile.following.all()
    for friend in friends:
        stories = get_user_stories(friend)
        if stories.exists():
            friend_profile = UserProfile.objects.get(user=friend)
            friends_with_stories.append({
                "username": friend.username,
                "user_id": friend.id,
                "profile_image": get_profile_image_url(friend_profile),
                "story_index_to_view": get_story_index_to_view(stories, request.user),
                "yet_to_view": has_unviewed_stories(stories, request.user)
            })

    return Response({"friends_with_stories": friends_with_stories})


def get_user_stories(user):
    return Story.objects.filter(story_user=user).exclude(hidden_from=user)


def get_profile_image_url(user_profile):
    return user_profile.profile_image.url if user_profile.profile_image else f"{settings.MEDIA_URL}profile_images/default.png"


def get_story_index_to_view(stories, user):
    return sum(1 for story in stories if story.viewed_by.filter(id=user.id).exists())


def has_unviewed_stories(stories, user):
    story_index_to_view = get_story_index_to_view(stories, user)
    return story_index_to_view < stories.count()

@story_router.post("/visibility", auth=JWTAuth())
def get_story_visibility(request, payload: ViewStorySchema) -> Response:
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": story_message}, status=404)

    if request.user != story.story_user:
        return Response({"error": "You are not authorized to view the visibility of this story"}, status=403)

    followers = story.story_user.userprofile.followers.all()

    hidden_users = story.hidden_from.all()

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
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        # Fetch the story by its ID
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": story_message}, status=404)

    if request.user != story.story_user:
        return Response({"error": "You are not authorized to update the visibility of this story"}, status=403)

    current_hidden_users = set(story.hidden_from.all())

    requested_hidden_users = set(User.objects.filter(
        username__in=payload.hidden_usernames))

    users_to_hide = requested_hidden_users - current_hidden_users
    story.hidden_from.add(*users_to_hide)

    users_to_unhide = current_hidden_users - requested_hidden_users
    story.hidden_from.remove(*users_to_unhide)

    return Response({
        "success": True,
        "message": "Story visibility updated successfully",
        "hidden_from": [user.username for user in story.hidden_from.all()]
    }, status=200)


@story_router.post("/delete-story", auth=JWTAuth())
def delete_story(request, payload: ViewStorySchema) -> Response:
    
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": story_message}, status=404)

    if request.user != story.story_user:
        return Response({
            "error": "You are not authorized to delete this story"
        }, status=403)
    
    if story.story_image: 
        story.story_image.delete(save=False)

    story.delete()

    return Response({
        "success": True,
        "message": "Story deleted successfully"
    }, status=200)


@story_router.post("/search-viewer", auth=JWTAuth())
def search_story_viewer(request, payload: SearchViewerSchema) -> Response:
   
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": story_message}, status=404)

    if request.user != story.story_user:
        return Response({"error": "You are not authorized to view viewers of this story"}, status=403)

    viewers = story.viewed_by.filter(username__icontains=payload.username)

    viewers_data = []
    for viewer in viewers:
        try:
            viewer_profile = UserProfile.objects.get(user=viewer)
            profile_image_url = (
                viewer_profile.profile_image.url if viewer_profile.profile_image else f"{
                    settings.MEDIA_URL}profile_images/default.png"
            )
        except UserProfile.DoesNotExist:
            profile_image_url = f"{
                settings.MEDIA_URL}profile_images/default.png"

        viewers_data.append({
            "id": viewer.id,
            "username": viewer.username,
            "profile_picture": profile_image_url,
        })

    return Response({
        "success": True,
        "viewers": viewers_data
    }, status=200)
