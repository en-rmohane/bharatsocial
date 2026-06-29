import logging
import re
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

from .services import UserInterestEngine, CreatorScoringEngine, AntiSpamSystem, FeedPrecomputationService
from .models import TrendingTopics, UserActivity
from posts.models import Post

logger = logging.getLogger(__name__)

@shared_task
def calculate_interest_decay():
    """
    Applies daily interest decay to user interests.
    """
    logger.info("[tasks] Running interest decay job...")
    UserInterestEngine.apply_decay(decay_factor=0.95)

@shared_task
def recalculate_creator_scores():
    """
    Recalculates scores and engagement levels for creators.
    """
    logger.info("[tasks] Running creator scoring job...")
    CreatorScoringEngine.recalculate_scores()

@shared_task
def detect_spam_activities():
    """
    Scans for spam accounts and bot patterns.
    """
    logger.info("[tasks] Running spam detection scans...")
    AntiSpamSystem.detect_spam_activities()

@shared_task
def precompute_user_feeds():
    """
    Precomputes personalized feeds for active users.
    """
    logger.info("[tasks] Running feed precomputation job...")
    FeedPrecomputationService.precompute_all_feeds()

@shared_task
def recalculate_trending_topics():
    """
    Aggregates recent interactions to discover trending categories and hashtags.
    """
    logger.info("[tasks] Running trending topics job...")
    try:
        cutoff = timezone.now() - timedelta(days=1)
        
        # 1. Trending Categories
        categories = UserActivity.objects.filter(
            created_at__gte=cutoff,
            category__isnull=False
        ).exclude(category='').values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        for cat in categories:
            TrendingTopics.objects.update_or_create(
                topic_type='category',
                name=cat['category'],
                defaults={'score': float(cat['count'])}
            )
            
        # 2. Trending Hashtags
        hashtags_counts = {}
        posts = Post.objects.filter(created_at__gte=cutoff)
        for post in posts:
            tags = re.findall(r'#(\w+)', post.caption)
            for tag in tags:
                tag = tag.lower()
                hashtags_counts[tag] = hashtags_counts.get(tag, 0) + 5.0 # Weight for posting
                
        # Also count search queries targeting hashtags
        searches = UserActivity.objects.filter(
            created_at__gte=cutoff,
            activity_type='search'
        )
        for s in searches:
            if s.category and s.category.startswith('#'):
                tag = s.category[1:].lower()
                hashtags_counts[tag] = hashtags_counts.get(tag, 0) + 1.0 # Weight for search
                
        # Sync to DB
        for tag, score in hashtags_counts.items():
            TrendingTopics.objects.update_or_create(
                topic_type='hashtag',
                name=tag,
                defaults={'score': float(score)}
            )
            
        # Clean up stale trends
        TrendingTopics.objects.filter(updated_at__lt=cutoff).delete()
        logger.info("[tasks] Trending topics sync complete.")
    except Exception as e:
        logger.error(f"[tasks] Error calculating trending topics: {e}", exc_info=True)
