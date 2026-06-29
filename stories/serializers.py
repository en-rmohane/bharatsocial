from rest_framework import serializers
from .models import Story, StoryView, StoryReaction

class StoryReactionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = StoryReaction
        fields = ('id', 'story', 'user', 'username', 'reaction_type', 'created_at')

class StorySerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.ImageField(source='author.profile.avatar', read_only=True)
    is_video = serializers.BooleanField(read_only=True)
    reactions = StoryReactionSerializer(many=True, read_only=True)
    views_count = serializers.SerializerMethodField()
    has_viewed = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = ('id', 'author', 'author_username', 'author_avatar', 'media_file', 'is_video', 'reactions', 'views_count', 'has_viewed', 'music_url', 'music_title', 'filter_style', 'animation_style', 'created_at')

    def get_views_count(self, obj):
        return obj.views.count()

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.views.filter(viewer=request.user).exists()
        return False
