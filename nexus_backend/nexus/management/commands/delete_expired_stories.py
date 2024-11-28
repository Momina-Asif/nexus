from django.core.management.base import BaseCommand
from django.utils.timezone import now
from nexus.models import Story

class Command(BaseCommand):
    help = 'Deletes stories that have expired'

    def handle(self, *args, **kwargs):
        
        expired_stories = Story.objects.filter(
            expires_at__lte=now())
        count = expired_stories.count()

        for story in expired_stories:
            if story.story_image: 
                story.story_image.delete(save=False)

        expired_stories.delete()
        self.stdout.write(f'{count} expired stories deleted.')
