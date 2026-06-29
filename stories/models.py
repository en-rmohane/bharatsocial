from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class ActiveStoryManager(models.Manager):
    def get_queryset(self):
        # Retrieve only stories from the last 24 hours
        cutoff = timezone.now() - timedelta(hours=24)
        return super().get_queryset().filter(created_at__gte=cutoff)

class Story(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stories')
    media_file = models.FileField(upload_to='stories/')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager() # Default manager
    active_objects = ActiveStoryManager() # Expired story filter manager

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Story by {self.author.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def is_video(self):
        name = self.media_file.name.lower()
        return name.endswith('.mp4') or name.endswith('.mov') or name.endswith('.avi') or name.endswith('.webm')

class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('story', 'viewer')

    def __str__(self):
        return f"{self.viewer.username} viewed story {self.story.id}"

class StoryReaction(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=50, default='❤️') # e.g. emoji string
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to story {self.story.id}"
