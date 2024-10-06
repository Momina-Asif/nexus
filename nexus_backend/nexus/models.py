from django.db import models

# Create your models here.

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Post Model
class Post(models.Model):
    postID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    postImage = models.TextField()
    caption = models.CharField(max_length=255)
    likesList = models.ManyToManyField(User, related_name='liked_posts', blank=True)  
    postDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.userID.username}: {self.caption}'

# Comment Model
class Comment(models.Model):
    commentID = models.AutoField(primary_key=True)
    commentPost = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    commentUser = models.ForeignKey(User, on_delete=models.CASCADE)
    commentMessage = models.TextField()
    commentDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.commentUser.username} on {self.commentPost.caption}'


# Message Model
class Message(models.Model):
    messageFrom = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    messageTo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    messageText = models.TextField()
    messageTime = models.DateTimeField(auto_now_add=True)
    roomid = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.messageFrom.username} to {self.messageTo.username}: {self.messageText[:20]}...'

# Story Model
class Story(models.Model):
    storyUser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    storyText = models.TextField(blank=True)
    storyImage = models.TextField()
    storyTime = models.DateTimeField(auto_now_add=True)
    
    @property

    def expiry_time(self):
        return self.storyTime + timedelta(hours=24)


    def is_expired(self):
        return timezone.now() > self.expiry_time

    def __str__(self):
        return f'{self.storyUser.username} posted a story'

# Notification Model
class Notification(models.Model):
    notifyFrom = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notifyTo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    notifyType = models.CharField(max_length=50)  # Could be 'like', 'comment', etc.
    notifyText = models.TextField(blank=True)
    notifyPost = models.ForeignKey(Post, on_delete=models.CASCADE, blank=True, null=True)  # Optional reference to post
    notifyTime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Notification to {self.notifyTo.username}'

# Extending the Django User model with additional fields
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    profileImage = models.TextField(blank=True)   # Profile picture
    bio = models.TextField(blank=True)
    pendingRequests = models.ManyToManyField(User, related_name='friend_requests', blank=True)  # Friend requests
    sendRequests = models.ManyToManyField(User, related_name='sent_requests', blank=True)
    followers = models.ManyToManyField(User, related_name='followed_by', blank=True)  
    following = models.ManyToManyField(User, related_name='following', blank=True) 


    def __str__(self):
        return self.user.username