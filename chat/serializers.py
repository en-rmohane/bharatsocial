from rest_framework import serializers
from .models import Message

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.ImageField(source='sender.profile.avatar', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)
    receiver_avatar = serializers.ImageField(source='receiver.profile.avatar', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'sender_username', 'sender_avatar', 'receiver', 'receiver_username', 'receiver_avatar', 'content', 'image', 'is_read', 'created_at')
