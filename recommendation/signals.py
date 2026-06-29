import re
from django.db.models import Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from posts.models import Post, Like, Comment, SavePost
from reels.models import Reel, ReelLike, ReelComment
from accounts.models import Follow
from .models import PostMetadata, ReelMetadata, CreatorScore, UserActivity
from .services import UserActivityLogger
from .utilities import detect_language, classify_category, analyze_sentiment

# Helpers to update engagement score dynamically
def update_post_engagement_score(post):
    try:
        likes_cnt = Like.objects.filter(post=post).count()
        comments_cnt = Comment.objects.filter(post=post).count()
        saves_cnt = SavePost.objects.filter(post=post).count()
        
        # Weighted engagement score
        score = (likes_cnt * 2.0) + (comments_cnt * 5.0) + (saves_cnt * 10.0)
        
        PostMetadata.objects.filter(post=post).update(engagement_score=score)
    except Exception:
        pass

def update_reel_engagement_score(reel):
    try:
        likes_cnt = ReelLike.objects.filter(reel=reel).count()
        comments_cnt = ReelComment.objects.filter(reel=reel).count()
        
        # Average watch duration from UserActivity logs
        avg_dur = UserActivity.objects.filter(
            activity_type='reel_watch',
            content_type='reel',
            content_id=reel.id
        ).aggregate(avg_val=Avg('duration'))['avg_val'] or 0.0
        
        score = (likes_cnt * 2.0) + (comments_cnt * 5.0) + (avg_dur * 1.5)
        
        ReelMetadata.objects.filter(reel=reel).update(engagement_score=score)
    except Exception:
        pass


# 1. Post and Reel Metadata Synchronization
@receiver(post_save, sender=Post)
def save_post_metadata(sender, instance, created, **kwargs):
    try:
        creator_score = 0.0
        cscore_obj = CreatorScore.objects.filter(creator=instance.author).first()
        if cscore_obj:
            creator_score = cscore_obj.creator_score
            
        hashtags = re.findall(r'#(\w+)', instance.caption)
        hashtags = [t.lower() for t in hashtags]
        
        lang = detect_language(instance.caption)
        category = classify_category(instance.caption)
        sentiment_score = analyze_sentiment(instance.caption)
        
        metadata, created_meta = PostMetadata.objects.get_or_create(
            post=instance,
            defaults={
                'category': category,
                'hashtags': hashtags,
                'language': lang,
                'creator_score': creator_score,
                'sentiment_score': sentiment_score
            }
        )
        if not created_meta:
            metadata.category = category
            metadata.hashtags = hashtags
            metadata.language = lang
            metadata.creator_score = creator_score
            metadata.sentiment_score = sentiment_score
            metadata.save()
    except Exception:
        pass

@receiver(post_save, sender=Reel)
def save_reel_metadata(sender, instance, created, **kwargs):
    try:
        creator_score = 0.0
        cscore_obj = CreatorScore.objects.filter(creator=instance.author).first()
        if cscore_obj:
            creator_score = cscore_obj.creator_score
            
        hashtags = re.findall(r'#(\w+)', instance.caption)
        hashtags = [t.lower() for t in hashtags]
        
        lang = detect_language(instance.caption)
        category = classify_category(instance.caption)
        sentiment_score = analyze_sentiment(instance.caption)
        
        metadata, created_meta = ReelMetadata.objects.get_or_create(
            reel=instance,
            defaults={
                'category': category,
                'hashtags': hashtags,
                'language': lang,
                'creator_score': creator_score,
                'sentiment_score': sentiment_score
            }
        )
        if not created_meta:
            metadata.category = category
            metadata.hashtags = hashtags
            metadata.language = lang
            metadata.creator_score = creator_score
            metadata.sentiment_score = sentiment_score
            metadata.save()
    except Exception:
        pass


# 2. Activity Tracking Signals
# Likes
@receiver(post_save, sender=Like)
def log_post_like_save(sender, instance, created, **kwargs):
    if created:
        UserActivityLogger.log_activity(
            user=instance.user,
            activity_type='like',
            content_type='post',
            content_id=instance.post.id
        )
        update_post_engagement_score(instance.post)

@receiver(post_delete, sender=Like)
def log_post_like_delete(sender, instance, **kwargs):
    update_post_engagement_score(instance.post)

@receiver(post_save, sender=ReelLike)
def log_reel_like_save(sender, instance, created, **kwargs):
    if created:
        UserActivityLogger.log_activity(
            user=instance.user,
            activity_type='like',
            content_type='reel',
            content_id=instance.reel.id
        )
        update_reel_engagement_score(instance.reel)

@receiver(post_delete, sender=ReelLike)
def log_reel_like_delete(sender, instance, **kwargs):
    update_reel_engagement_score(instance.reel)

# Comments
@receiver(post_save, sender=Comment)
def log_post_comment_save(sender, instance, created, **kwargs):
    if created:
        UserActivityLogger.log_activity(
            user=instance.author,
            activity_type='comment',
            content_type='post',
            content_id=instance.post.id
        )
        update_post_engagement_score(instance.post)

@receiver(post_delete, sender=Comment)
def log_post_comment_delete(sender, instance, **kwargs):
    update_post_engagement_score(instance.post)

@receiver(post_save, sender=ReelComment)
def log_reel_comment_save(sender, instance, created, **kwargs):
    if created:
        UserActivityLogger.log_activity(
            user=instance.author,
            activity_type='comment',
            content_type='reel',
            content_id=instance.reel.id
        )
        update_reel_engagement_score(instance.reel)

@receiver(post_delete, sender=ReelComment)
def log_reel_comment_delete(sender, instance, **kwargs):
    update_reel_engagement_score(instance.reel)

# Saves
@receiver(post_save, sender=SavePost)
def log_post_save_save(sender, instance, created, **kwargs):
    if created:
        UserActivityLogger.log_activity(
            user=instance.user,
            activity_type='save',
            content_type='post',
            content_id=instance.post.id
        )
        update_post_engagement_score(instance.post)

@receiver(post_delete, sender=SavePost)
def log_post_save_delete(sender, instance, **kwargs):
    update_post_engagement_score(instance.post)

# Follows
@receiver(post_save, sender=Follow)
def log_follow_save(sender, instance, created, **kwargs):
    if created:
        UserActivityLogger.log_activity(
            user=instance.follower,
            activity_type='follow',
            content_type='user',
            content_id=instance.following.id
        )

@receiver(post_delete, sender=Follow)
def log_follow_delete(sender, instance, **kwargs):
    UserActivityLogger.log_activity(
        user=instance.follower,
        activity_type='unfollow',
        content_type='user',
        content_id=instance.following.id
    )
