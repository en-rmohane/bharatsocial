from rest_framework import serializers
from .models import Reel, ReelComment, ReelLike

class ReelCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.ImageField(source='author.profile.avatar', read_only=True)

    class Meta:
        model = ReelComment
        fields = ('id', 'reel', 'author', 'author_username', 'author_avatar', 'content', 'created_at')

class ReelSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.ImageField(source='author.profile.avatar', read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Reel
        fields = ('id', 'author', 'author_username', 'author_avatar', 'video_file', 'caption', 'likes_count', 'comments_count', 'is_liked', 'created_at')

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
