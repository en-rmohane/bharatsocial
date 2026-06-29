from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('follow', 'Followed You'),
        ('like', 'Liked Your Post'),
        ('comment', 'Commented On Your Post'),
        ('message', 'Sent You A Message'),
        ('reel_like', 'Liked Your Reel'),
        ('reel_comment', 'Commented On Your Reel'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    reel = models.ForeignKey('reels.Reel', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    comment = models.ForeignKey('posts.Comment', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.sender.username} {self.get_notification_type_display()}"
