
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.utils import timezone
import os
# Post Model


def post_image_directory(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'{instance.post_id}.{ext}'
    return os.path.join('posts', filename)


class Post(models.Model):
    post_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='posts')
    post_image = models.ImageField(
        upload_to=post_image_directory, blank=True, null=True)
    caption = models.TextField(max_length=255, blank=True)
    likes_list = models.ManyToManyField(
        User, related_name='liked_posts', blank=True)
    post_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.post_id}: {self.caption}'


# Comment Model
class Comment(models.Model):
    comment_id = models.AutoField(primary_key=True)
    comment_post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='comments')
    comment_user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment_message = models.TextField()
    comment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.comment_user.username} on {self.comment_post.caption}'

# Notification Model


class Notification(models.Model):
    notification_id = models.AutoField(
        primary_key=True)
    notify_from = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_notifications')
    notify_to = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_notifications')
    notify_type = models.CharField(max_length=50)
    notify_text = models.TextField(blank=True)
    notify_post = models.ForeignKey(
        Post, on_delete=models.CASCADE, blank=True, null=True)
    notify_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Notification to {self.notify_to.username}'

# UserProfile Model


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    first_name = models.CharField(
        max_length=30, null=False, blank=False, default='User')
    last_name = models.CharField(max_length=50)
    profile_image = models.ImageField(
        upload_to='profile_images/', blank=True, null=True) 
    bio = models.TextField(blank=True)
    pending_requests = models.ManyToManyField(
        User, related_name='friend_requests', blank=True)
    sent_requests = models.ManyToManyField(
        User, related_name='sent_requests', blank=True)
    followers = models.ManyToManyField(
        User, related_name='followed_by', blank=True)
    following = models.ManyToManyField(
        User, related_name='following', blank=True)

    # Story Model


class Story(models.Model):
    story_id = models.AutoField(primary_key=True)
    story_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='stories')
    story_text = models.TextField(blank=True)
    story_image = models.ImageField(
        upload_to='media/story', blank=True, null=True)
    story_time = models.DateTimeField(auto_now_add=True)
    viewed_by = models.ManyToManyField(
        User, related_name='viewed_by', blank=True)
    hidden_from = models.ManyToManyField(
        User, related_name='hidden_from', blank=True)

    def default_expiration_time():
        return timezone.now() + timedelta(days=1)

    expires_at = models.DateTimeField(default=default_expiration_time)

    def __str__(self):
        return f'{self.story_user.username} posted a story'


class Conversation(models.Model):
    id = models.AutoField(primary_key=True)
    users = models.ManyToManyField(
        User, related_name="involved_users", blank=True)


class Message(models.Model):
    id = models.AutoField(primary_key=True)
    producer = models.ForeignKey(
        User, related_name="sender", on_delete=models.PROTECT)
    consumer = models.ForeignKey(
        User, related_name="receiver", on_delete=models.PROTECT)
    content = models.TextField()
    belongs_in = models.ForeignKey(
        Conversation, related_name="belongs_in", on_delete=models.CASCADE)
    created_at = models.DateTimeField()
