from django.db import models
from django.conf import settings
from .managers import PostMetadataManager, ReelMetadataManager

class PostMetadata(models.Model):
    post = models.OneToOneField('posts.Post', on_delete=models.CASCADE, related_name='metadata')
    category = models.CharField(max_length=100, default='General', db_index=True)
    subcategory = models.CharField(max_length=100, blank=True)
    hashtags = models.JSONField(default=list)
    language = models.CharField(max_length=10, default='en', db_index=True)
    creator_score = models.FloatField(default=0.0, db_index=True)
    trending_score = models.FloatField(default=0.0, db_index=True)
    engagement_score = models.FloatField(default=0.0, db_index=True)
    freshness_score = models.FloatField(default=1.0, db_index=True)
    quality_score = models.FloatField(default=1.0, db_index=True)
    sentiment_score = models.FloatField(default=0.0, db_index=True)

    objects = PostMetadataManager()

    def __str__(self):
        return f"PostMetadata {self.post.id} - Cat: {self.category}"

class ReelMetadata(models.Model):
    reel = models.OneToOneField('reels.Reel', on_delete=models.CASCADE, related_name='metadata')
    category = models.CharField(max_length=100, default='General', db_index=True)
    subcategory = models.CharField(max_length=100, blank=True)
    hashtags = models.JSONField(default=list)
    language = models.CharField(max_length=10, default='en', db_index=True)
    creator_score = models.FloatField(default=0.0, db_index=True)
    trending_score = models.FloatField(default=0.0, db_index=True)
    engagement_score = models.FloatField(default=0.0, db_index=True)
    freshness_score = models.FloatField(default=1.0, db_index=True)
    quality_score = models.FloatField(default=1.0, db_index=True)
    sentiment_score = models.FloatField(default=0.0, db_index=True)

    objects = ReelMetadataManager()

    def __str__(self):
        return f"ReelMetadata {self.reel.id} - Cat: {self.category}"

class UserActivity(models.Model):
    ACTIVITY_TYPES = (
        ('post_impression', 'Post Impression'),
        ('reel_impression', 'Reel Impression'),
        ('reel_watch', 'Reel Watch'),
        ('story_view', 'Story View'),
        ('story_reaction', 'Story Reaction'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('share', 'Share'),
        ('save', 'Save'),
        ('follow', 'Follow'),
        ('unfollow', 'Unfollow'),
        ('profile_visit', 'Profile Visit'),
        ('search', 'Search'),
        ('category_visit', 'Category Visit'),
        ('session', 'Session'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities', db_index=True)
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES, db_index=True)
    content_type = models.CharField(max_length=50, blank=True, db_index=True) # e.g. 'post', 'reel', 'story'
    content_id = models.IntegerField(null=True, blank=True, db_index=True)
    duration = models.FloatField(default=0.0) # for reels/session duration in seconds
    device = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=10, blank=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.created_at}"

class UserInterest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interests', db_index=True)
    topic = models.CharField(max_length=100, db_index=True)
    score = models.FloatField(default=0.0, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('user', 'topic')
        ordering = ['-score']

    def __str__(self):
        return f"{self.user.username} - {self.topic}: {self.score}"

class FeedCache(models.Model):
    FEED_TYPES = (
        ('post', 'Post Feed'),
        ('reel', 'Reel Feed'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feed_caches', db_index=True)
    feed_type = models.CharField(max_length=10, choices=FEED_TYPES, db_index=True)
    content_ids = models.JSONField(default=list)
    generated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('user', 'feed_type')

    def __str__(self):
        return f"{self.user.username} - {self.feed_type} Cache (Count: {len(self.content_ids)})"

class TrendingTopics(models.Model):
    TOPIC_TYPES = (
        ('hashtag', 'Hashtag'),
        ('category', 'Category'),
    )
    topic_type = models.CharField(max_length=20, choices=TOPIC_TYPES, db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    score = models.FloatField(default=0.0, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('topic_type', 'name')
        ordering = ['-score']

    def __str__(self):
        return f"Trending {self.topic_type} - {self.name}: {self.score}"

class CreatorScore(models.Model):
    creator = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='creator_score')
    creator_score = models.FloatField(default=0.0, db_index=True)
    engagement_rate = models.FloatField(default=0.0)
    spam_score = models.FloatField(default=0.0, db_index=True)
    follower_count = models.IntegerField(default=0)
    is_flagged = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Creator {self.creator.username} - Score: {self.creator_score}"

class RecommendationAnalytics(models.Model):
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Analytics snapshot at {self.created_at}"
