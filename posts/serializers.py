from rest_framework import serializers
from .models import Post, PostMedia, Comment, Like, SavePost, SavedCollection, Hashtag
from accounts.serializers import UserSerializer

class PostMediaSerializer(serializers.ModelSerializer):
    is_video = serializers.BooleanField(read_only=True)

    class Meta:
        model = PostMedia
        fields = ('id', 'file', 'order', 'is_video')

class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ('id', 'name')

class CommentReplySerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.ImageField(source='author.profile.avatar', read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'author', 'author_username', 'author_avatar', 'content', 'created_at')

class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.ImageField(source='author.profile.avatar', read_only=True)
    replies = CommentReplySerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'post', 'author', 'author_username', 'author_avatar', 'content', 'parent', 'replies', 'created_at')

class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_avatar = serializers.ImageField(source='author.profile.avatar', read_only=True)
    author_is_verified = serializers.SerializerMethodField()
    media = PostMediaSerializer(many=True, read_only=True)
    hashtags = HashtagSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ('id', 'author', 'author_username', 'author_avatar', 'author_is_verified', 'caption', 'location', 'media', 'hashtags', 'likes_count', 'comments_count', 'is_liked', 'is_saved', 'created_at')

    def get_author_is_verified(self, obj):
        return obj.author.is_staff or obj.author.username in ['raj', 'priya', 'admin']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.saved_by.filter(user=request.user).exists()
        return False
