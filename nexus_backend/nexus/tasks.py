from celery import shared_task
from django.utils import timezone
from .models import Story

@shared_task
def delete_expired_stories():
    # Get the current time
    now = timezone.now()

    # Delete stories whose expiration time has passed
    expired_stories = Story.objects.filter(expires_at__lte=now)
    expired_stories.delete()

    return f"{expired_stories.count()} expired stories deleted."
