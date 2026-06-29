import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class RedisCacheManager:
    @classmethod
    def get_feed_cache(cls, user_id, feed_type):
        key = f"feed_cache:{user_id}:{feed_type}"
        try:
            return cache.get(key)
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error getting feed cache: {e}")
            return None

    @classmethod
    def set_feed_cache(cls, user_id, feed_type, content_ids, timeout=3600):
        key = f"feed_cache:{user_id}:{feed_type}"
        try:
            cache.set(key, content_ids, timeout)
            return True
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error setting feed cache: {e}")
            return False

    @classmethod
    def delete_feed_cache(cls, user_id, feed_type):
        key = f"feed_cache:{user_id}:{feed_type}"
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error deleting feed cache: {e}")
            return False

    @classmethod
    def get_user_interests(cls, user_id):
        key = f"user_interests:{user_id}"
        try:
            return cache.get(key)
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error getting user interests cache: {e}")
            return None

    @classmethod
    def set_user_interests(cls, user_id, interests, timeout=1800):
        key = f"user_interests:{user_id}"
        try:
            cache.set(key, interests, timeout)
            return True
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error setting user interests cache: {e}")
            return False

    @classmethod
    def get_trending_topics(cls, topic_type):
        key = f"trending_topics:{topic_type}"
        try:
            return cache.get(key)
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error getting trending topics cache: {e}")
            return None

    @classmethod
    def set_trending_topics(cls, topic_type, topics, timeout=1800):
        key = f"trending_topics:{topic_type}"
        try:
            cache.set(key, topics, timeout)
            return True
        except Exception as e:
            logger.error(f"[RedisCacheManager] Error setting trending topics cache: {e}")
            return False
