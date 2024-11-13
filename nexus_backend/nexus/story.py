from ninja import NinjaAPI, Router, File, Form, UploadedFile
from ninja.responses import Response
from ninja_jwt.authentication import JWTAuth
from .models import Story, UserProfile, User
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .schema import ViewStorySchema, ViewUserStorySchema
from django.core.exceptions import ObjectDoesNotExist

story_router = NinjaAPI(urls_namespace='storyAPI')


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

    # Fetch all stories by the user and order by story_id in ascending order
    stories = Story.objects.filter(story_user=user_profile.user).order_by(
        'story_id')  # Ascending order

    # Check if the authenticated user is the owner of the stories
    is_owner = request.user == user_profile.user

    # Count total stories by the user
    total_stories = stories.count()

    # Count how many stories the authenticated user has viewed
    viewed_by_user_count = sum(
        1 for story in stories if request.user in story.viewed_by.all())

    if (payload.index >= stories._len_()):
        payload.index = 0

    story = stories[payload.index]

    # Prepare response data
    # stories_data = [
    #     {
    # "story_id": story.story_id,
    # "story_text": story.story_text,
    # "story_image": story.story_image.url if story.story_image else None,
    # "story_time": story.story_time.isoformat(),
    # # Only include viewed_by_count if the authenticated user is the owner
    # "viewed_by_count": story.viewed_by.count() if is_owner else None,
    #     }
    #     for story in stories
    # ]

    print("RET")

    return Response({
        "username": user_profile.user.username,
        "user_id": user_profile.user.id,
        "total_stories": total_stories,
        "viewed_by_user_count": viewed_by_user_count,
        "id": story.story_id,
        "caption": story.story_text,
        "image": story.story_image.url if story.story_image else None,
        "time": story.story_time.isoformat(),
        # Only include viewed_by_count if the authenticated user is the owner
        "viewed_by_count": story.viewed_by.count() if is_owner else None,
        "is_owner": is_owner
        # "stories": stories_data,
    }, status=200)


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
    friends = User.objects.all()
    # friends = user_profile.following.all()
    print("PRO", friends)

    friends_with_stories = []
    for friend in friends:
        # Fetch the friend's stories
        stories = Story.objects.filter(story_user=friend)

        if stories.exists():
            story_index_to_view = 0
            for story in stories:
                if story.viewed_by.filter(id=request.user.id).exists():
                    story_index_to_view += 1
            # If the friend has posted stories, retrieve their profile
            friend_profile = UserProfile.objects.get(user=friend)

            # Handle the profile image URL
            profile_image_url = friend_profile.profile_image.url if friend_profile.profile_image else None

            # Prepare the data for the response
            friends_with_stories.append({
                "username": friend.username,
                "user_id": friend.id,
                "profile_image": profile_image_url,
                "story_index_to_view": story_index_to_view if story_index_to_view < stories._len_() else 0,
                "yet_to_view": False if story_index_to_view == stories._len_() else True
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
        # Fetch the story by its ID
        story = Story.objects.get(pk=payload.story_id)
    except Story.DoesNotExist:
        return Response({"error": "Story not found"}, status=404)

    # Check if the authenticated user is the one who posted the story
    if request.user != story.story_user:
        return Response({"error": "You are not authorized to view the viewers of this story"}, status=403)

    # Get the viewers of the story (the users who have viewed the story)
    viewers = story.viewed_by.all()

    # Prepare the response with the usernames of users who have viewed the story
    viewers_usernames = [viewer.username for viewer in viewers]

    return Response({
        "story_id": payload.story_id,
        "viewed_by": viewers_usernames
    }, status=200)