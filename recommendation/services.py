import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import F, Avg, Count
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import UserActivity, UserInterest, CreatorScore, PostMetadata, ReelMetadata, FeedCache, TrendingTopics
from posts.models import Post, Like, Comment, SavePost, Hashtag
from reels.models import Reel, ReelLike, ReelComment
from accounts.models import Follow

logger = logging.getLogger(__name__)
User = get_user_model()

class UserActivityLogger:
    @classmethod
    def log_activity(cls, user, activity_type, content_type=None, content_id=None, duration=0.0, device='', language='', category=''):
        if not user or not user.is_authenticated:
            return None
        
        try:
            # Resolve category automatically if content_id and content_type is provided
            if not category and content_id and content_type:
                if content_type == 'post':
                    metadata = PostMetadata.objects.filter(post_id=content_id).first()
                    if metadata:
                        category = metadata.category
                elif content_type == 'reel':
                    metadata = ReelMetadata.objects.filter(reel_id=content_id).first()
                    if metadata:
                        category = metadata.category

            activity = UserActivity.objects.create(
                user=user,
                activity_type=activity_type,
                content_type=content_type or '',
                content_id=content_id,
                duration=duration,
                device=device,
                language=language,
                category=category
            )
            
            # Real-time trigger to update user interest score for that category
            if category:
                UserInterestEngine.update_realtime_interest(user, category, activity_type, duration)
                
            return activity
        except Exception as e:
            logger.error(f"[UserActivityLogger] Error logging activity: {e}", exc_info=True)
            return None

class UserInterestEngine:
    ACTIVITY_WEIGHTS = {
        'like': 10.0,
        'comment': 20.0,
        'share': 30.0,
        'save': 35.0,
        'follow': 50.0,
        'unfollow': -50.0,
        'story_view': 5.0,
        'story_reaction': 15.0,
        'reel_watch': 15.0, # base weight
        'post_impression': 2.0,
        'reel_impression': 2.0,
        'category_visit': 5.0,
        'search': 10.0,
    }

    @classmethod
    def update_realtime_interest(cls, user, category, activity_type, duration=0.0):
        weight = cls.ACTIVITY_WEIGHTS.get(activity_type, 1.0)
        
        # Scaling weight for watch duration of video
        if activity_type == 'reel_watch' and duration > 0.0:
            # If watch duration is high, give extra weight
            if duration >= 15.0:
                weight += 10.0
            elif duration >= 5.0:
                weight += 5.0

        if weight == 0.0:
            return

        try:
            with transaction.atomic():
                interest, created = UserInterest.objects.get_or_create(
                    user=user,
                    topic=category,
                    defaults={'score': 0.0}
                )
                interest.score = max(0.0, interest.score + weight)
                interest.save()
        except Exception as e:
            logger.error(f"[UserInterestEngine] Error updating interest for {user.username}: {e}")

    @classmethod
    def apply_decay(cls, decay_factor=0.95):
        """
        Applies a daily decay factor to all user interest scores to keep them dynamic.
        Runs daily via a Celery background job.
        """
        try:
            UserInterest.objects.all().update(score=F('score') * decay_factor)
            # Cleanup scores that drop close to zero to keep DB size optimized
            UserInterest.objects.filter(score__lt=0.5).delete()
        except Exception as e:
            logger.error(f"[UserInterestEngine] Error applying interest decay: {e}")

class CreatorScoringEngine:
    @classmethod
    def recalculate_scores(cls):
        """
        Runs as a background job to update metrics for creators.
        """
        try:
            # Aggregate stats for each user who has posted posts or reels
            creators = User.objects.filter(is_active=True).annotate(
                total_posts=Count('posts', distinct=True),
                total_reels=Count('reels', distinct=True)
            ).filter(models.Q(total_posts__gt=0) | models.Q(total_reels__gt=0))

            for creator in creators:
                # 1. Follower count
                followers = Follow.objects.filter(following=creator).count()
                
                # 2. Aggregated Likes and Comments on creator's posts
                posts = Post.objects.filter(author=creator)
                reels = Reel.objects.filter(author=creator)
                
                post_likes = Like.objects.filter(post__in=posts).count()
                post_comments = Comment.objects.filter(post__in=posts).count()
                reel_likes = ReelLike.objects.filter(reel__in=reels).count()
                reel_comments = ReelComment.objects.filter(reel__in=reels).count()
                
                total_interactions = post_likes + post_comments + reel_likes + reel_comments
                total_content = posts.count() + reels.count()
                
                engagement_rate = 0.0
                if total_content > 0:
                    engagement_rate = total_interactions / total_content
                
                # Base Creator Score = (followers * 0.1) + (engagement_rate * 2.0)
                base_score = (followers * 0.1) + (engagement_rate * 2.0)
                
                # Update or create CreatorScore entry
                score_obj, _ = CreatorScore.objects.get_or_create(creator=creator)
                score_obj.follower_count = followers
                score_obj.engagement_rate = engagement_rate
                
                # Deduct creator score dynamically if spam/manipulation score is high
                deduction = score_obj.spam_score * 5.0
                score_obj.creator_score = max(0.0, base_score - deduction)
                score_obj.save()

                # Sync creator score to metadata models
                PostMetadata.objects.filter(post__author=creator).update(creator_score=score_obj.creator_score)
                ReelMetadata.objects.filter(reel__author=creator).update(creator_score=score_obj.creator_score)
                
        except Exception as e:
            logger.error(f"[CreatorScoringEngine] Error recalculating creator scores: {e}", exc_info=True)

class AntiSpamSystem:
    @classmethod
    def detect_spam_activities(cls):
        """
        Scans UserActivity logs to identify bot patterns and suspicious actions.
        Runs hourly as a Celery job.
        """
        try:
            cutoff = timezone.now() - timedelta(hours=2)
            # Find users who have done too many likes, comments or follows in a short window
            suspicious_actions = UserActivity.objects.filter(
                created_at__gte=cutoff,
                activity_type__in=['like', 'comment', 'follow']
            ).values('user').annotate(
                action_count=Count('id')
            ).filter(action_count__gt=200) # Threshold of 200 actions in 2 hours

            for entry in suspicious_actions:
                user_id = entry['user']
                cls.flag_suspicious_account(user_id, spam_increase=2.0)

            # Detect Follow-Unfollow patterns
            # Find users who have follow and unfollow events on same days
            unfollow_cutoff = timezone.now() - timedelta(days=1)
            follows = UserActivity.objects.filter(
                created_at__gte=unfollow_cutoff,
                activity_type='follow'
            ).values('user').annotate(follow_count=Count('id'))

            unfollows = UserActivity.objects.filter(
                created_at__gte=unfollow_cutoff,
                activity_type='unfollow'
            ).values('user').annotate(unfollow_count=Count('id'))

            unfollow_map = {item['user']: item['unfollow_count'] for item in unfollows}
            for item in follows:
                user_id = item['user']
                follow_cnt = item['follow_count']
                unfollow_cnt = unfollow_map.get(user_id, 0)
                
                if follow_cnt > 30 and unfollow_cnt > 30:
                    # User is doing mass follow/unfollow loops
                    cls.flag_suspicious_account(user_id, spam_increase=3.5)

        except Exception as e:
            logger.error(f"[AntiSpamSystem] Error running spam scanning: {e}", exc_info=True)

    @classmethod
    def flag_suspicious_account(cls, user_id, spam_increase=1.0):
        try:
            creator_score, _ = CreatorScore.objects.get_or_create(creator_id=user_id)
            creator_score.spam_score = min(10.0, creator_score.spam_score + spam_increase)
            if creator_score.spam_score >= 8.0:
                creator_score.is_flagged = True
            creator_score.save()
            logger.warning(f"[AntiSpamSystem] Flagged/updated user {user_id} with spam score: {creator_score.spam_score}")
        except Exception as e:
            logger.error(f"[AntiSpamSystem] Error flagging account {user_id}: {e}")

class FeedPrecomputationService:
    @classmethod
    def precompute_all_feeds(cls):
        """
        Runs as background job to pre-populate caches for active users.
        """
        try:
            # Compute feeds for active users (logged in within past 3 days)
            active_cutoff = timezone.now() - timedelta(days=3)
            active_users = User.objects.filter(last_login__gte=active_cutoff)

            for user in active_users:
                cls.generate_and_cache_feed(user, 'post')
                cls.generate_and_cache_feed(user, 'reel')
        except Exception as e:
            logger.error(f"[FeedPrecomputationService] Error in bulk precomputing: {e}", exc_info=True)

    @classmethod
    def generate_and_cache_feed(cls, user, feed_type):
        from .algorithms import ScoringEngine
        from .cache import RedisCacheManager
        
        try:
            # Generate the list of recommended IDs
            recommended_ids = ScoringEngine.get_recommended_feed(user, feed_type=feed_type, limit=100)
            
            # Save to database FeedCache
            FeedCache.objects.update_or_create(
                user=user,
                feed_type=feed_type,
                defaults={'content_ids': recommended_ids}
            )
            
            # Warm up Redis Cache
            RedisCacheManager.set_feed_cache(user.id, feed_type, recommended_ids)
            
            return recommended_ids
        except Exception as e:
            logger.error(f"[FeedPrecomputationService] Error precomputing {feed_type} feed for {user.username}: {e}", exc_info=True)
            return []
