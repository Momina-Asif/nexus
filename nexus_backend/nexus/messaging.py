import os
from django.conf import settings
from ninja import NinjaAPI, Schema
from ninja.responses import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, UserProfile, Conversation, Message, User
from ninja_jwt.authentication import JWTAuth
from .schema import PostSchema
from django.utils.timesince import timesince
from django.utils import timezone
from .schema import ConversationMessagesSchema, NewMessageSchema

# Create an instance of NinjaAPI
message_router = NinjaAPI(urls_namespace='message_api')


@message_router.get("/chats-preview", auth=JWTAuth())
def get_homepage_posts(request) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        conversations = Conversation.objects.filter(users=request.user)

        chat_previews = []

        for conversation in conversations:
            other_users = conversation.users.exclude(id=request.user.id)
            conversation_with = other_users.first()
            other_user_profile = UserProfile.objects.get(
                user=conversation_with)
            profile_picture_url = (
                other_user_profile.profile_image.url if other_user_profile.profile_image else f"{
                    settings.MEDIA_URL}profile_images/default.png"
            )
            chat_previews.append({
                "id": conversation.id,
                "username": conversation_with.username,
                "profile_picture": profile_picture_url
            })
        return Response(chat_previews, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


@message_router.post("/chat-messages", auth=JWTAuth())
def get_chat_messages(request, payload: ConversationMessagesSchema) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:

        conversation = Conversation.objects.get(id=payload.convo_id)

        other_user = conversation.users.exclude(id=request.user.id)
        conversation_with = other_user.first()
        other_user_profile = UserProfile.objects.get(user=conversation_with)

        user_profile = UserProfile.objects.get(user=request.user)

        sender_profile_picture = (
            user_profile.profile_image.url if user_profile.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"
        )

        receiver_profile_picture = (
            other_user_profile.profile_image.url if other_user_profile.profile_image else f"{
                settings.MEDIA_URL}profile_images/default.png"
        )

        chat_messages = Message.objects.filter(
            belongs_in=payload.convo_id).order_by("created_at")

        messages = []

        for message in chat_messages:
            messages.append({
                "content": message.content,
                "is_owner": True if message.producer == request.user else False
            })

        response_object = {
            "sender_profile_picture": sender_profile_picture,
            "receiver_profile_picture": receiver_profile_picture,
            "username": conversation_with.username,
            "messages": messages
        }

        return Response(response_object, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


@message_router.post("/add-message", auth=JWTAuth())
def get_chat_messages(request, payload: NewMessageSchema) -> Response:
    if not request.user.is_authenticated:
        return Response({"error": "Unauthorized"}, status=401)

    try:
        receiver_profile = User.objects.get(username=payload.receiver_username)
        conversation = Conversation.objects.get(id=payload.convo_id)
        Message.objects.create(
            belongs_in=conversation,
            producer=request.user,
            consumer=receiver_profile,
            content=payload.content,
            created_at=timezone.now()
        )

        return Response({"message": "Message created successfully"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)
