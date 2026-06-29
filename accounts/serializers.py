from rest_framework import serializers
from .models import CustomUser, Profile, Follow, Block

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'username', 'avatar', 'cover_photo', 'bio', 'website', 'followers_count', 'following_count', 'points')

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'is_private', 'profile', 'is_verified')

    def get_is_verified(self, obj):
        return obj.is_staff or obj.username in ['raj', 'priya', 'admin']

class FollowSerializer(serializers.ModelSerializer):
    follower_username = serializers.CharField(source='follower.username', read_only=True)
    following_username = serializers.CharField(source='following.username', read_only=True)

    class Meta:
        model = Follow
        fields = ('id', 'follower', 'follower_username', 'following', 'following_username', 'created_at')
