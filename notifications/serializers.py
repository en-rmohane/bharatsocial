from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    post_image = serializers.SerializerMethodField()
    reel_video = serializers.SerializerMethodField()
    comment_content = serializers.CharField(source='comment.content', read_only=True)
    notification_text = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'sender', 'sender_username', 'sender_avatar', 'notification_type', 'notification_text', 'post', 'post_image', 'reel', 'reel_video', 'comment_content', 'is_read', 'created_at')

    def get_sender_avatar(self, obj):
        try:
            if obj.sender and hasattr(obj.sender, 'profile') and obj.sender.profile and obj.sender.profile.avatar:
                return obj.sender.profile.avatar.url
        except Exception:
            pass
        return '/media/avatars/default.png'

    def get_post_image(self, obj):
        if obj.post and obj.post.media.exists():
            return obj.post.media.first().file.url
        return None

    def get_reel_video(self, obj):
        if obj.reel:
            return obj.reel.video_file.url
        return None
