import math
import random
import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import UserInterest, CreatorScore, PostMetadata, ReelMetadata, UserActivity, TrendingTopics
from posts.models import Post, Like, Comment
from reels.models import Reel, ReelLike, ReelComment
from accounts.models import Follow, Block

logger = logging.getLogger(__name__)
User = get_user_model()

class ScoringEngine:
    @classmethod
    def get_recommended_feed(cls, user, feed_type='post', limit=50):
        """
        Calculates recommendations using the formula:
        Score = (Interest*0.4) + (Engagement*0.2) + (Freshness*0.15) + (Creator*0.1) + (Trending*0.1) + (Diversity*0.05)
        Applies duplicate filters and the 80/20 personalization/discovery rule.
        """
        try:
            # 1. Fetch user block exclusion list
            blocking_ids = Block.objects.filter(blocker=user).values_list('blocked_id', flat=True)
            blocked_by_ids = Block.objects.filter(blocked=user).values_list('blocker_id', flat=True)
            exclude_user_ids = list(blocking_ids) + list(blocked_by_ids)
            
            # 2. Exclude already seen content (No duplicates rule)
            cutoff_seen = timezone.now() - timezone.timedelta(hours=24)
            seen_ids = UserActivity.objects.filter(
                user=user,
                activity_type=f"{feed_type}_impression",
                created_at__gte=cutoff_seen
            ).values_list('content_id', flat=True)
            exclude_content_ids = list(seen_ids)

            # 3. Pull candidates
            if feed_type == 'post':
                candidates = Post.objects.exclude(
                    Q(author_id__in=exclude_user_ids) | Q(id__in=exclude_content_ids)
                ).select_related('author', 'author__profile').prefetch_related('media')
                
                # Fetch metadata in bulk to prevent N+1 queries
                meta_map = {m.post_id: m for m in PostMetadata.objects.all()}
            else:
                candidates = Reel.objects.exclude(
                    Q(author_id__in=exclude_user_ids) | Q(id__in=exclude_content_ids)
                ).select_related('author', 'author__profile')
                
                meta_map = {m.reel_id: m for m in ReelMetadata.objects.all()}

            # 4. Fetch user interests mapping
            user_interests = {ui.topic: ui.score for ui in UserInterest.objects.filter(user=user)}

            # 4.5 Calculate user's preferred sentiment score dynamically from their liked posts/reels
            liked_post_ids = Like.objects.filter(user=user).values_list('post_id', flat=True)
            liked_reel_ids = ReelLike.objects.filter(user=user).values_list('reel_id', flat=True)
            
            from django.db.models import Avg
            liked_post_sentiment = PostMetadata.objects.filter(post_id__in=liked_post_ids).aggregate(avg_val=Avg('sentiment_score'))['avg_val']
            liked_reel_sentiment = ReelMetadata.objects.filter(reel_id__in=liked_reel_ids).aggregate(avg_val=Avg('sentiment_score'))['avg_val']
            
            sentiments = [s for s in [liked_post_sentiment, liked_reel_sentiment] if s is not None]
            user_preferred_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            # 5. Fetch user followings (to score personalized items)
            following_ids = set(Follow.objects.filter(follower=user).values_list('following_id', flat=True))

            scored_candidates = []
            now = timezone.now()

            # Track category frequencies for Diversity Score
            category_counts = {}

            for item in candidates:
                item_id = item.id
                meta = meta_map.get(item_id)
                
                # Default metadata if not created yet
                category = meta.category if meta else 'General'
                language = meta.language if meta else 'en'
                creator_score = meta.creator_score if meta else 0.0
                trending_score = meta.trending_score if meta else 0.0
                engagement_score = meta.engagement_score if meta else 0.0
                item_sentiment = meta.sentiment_score if meta else 0.0
                
                # Calculate scores
                # A. Interest Score (0 to 100 normalized)
                interest_val = user_interests.get(category, 0.0)
                interest_score = min(100.0, interest_val)

                # A.2 Sentiment Match Score (0 to 100 normalized)
                # Diff ranges from 0.0 to 2.0. Match is (1 - diff/2) * 100.
                sentiment_diff = abs(item_sentiment - user_preferred_sentiment)
                sentiment_match_score = (1.0 - (sentiment_diff / 2.0)) * 100.0

                # B. Engagement Score (0 to 100)
                engagement_val = min(100.0, engagement_score)

                # C. Freshness Score (exponential decay)
                time_delta = (now - item.created_at).total_seconds() / 3600.0 # hours
                freshness_val = math.exp(-0.015 * time_delta) * 100.0 # 0 to 100

                # D. Creator Score
                creator_val = min(100.0, creator_score)

                # E. Trending Score
                trending_val = min(100.0, trending_score)

                # F. Diversity Score (sequential or local frequency penalty)
                freq = category_counts.get(category, 0)
                diversity_val = max(0.0, (1.0 - (freq / 10.0)) * 100.0)

                # Compute Total Score
                final_score = (
                    (interest_score * 0.35) +
                    (sentiment_match_score * 0.10) +
                    (engagement_val * 0.20) +
                    (freshness_val * 0.15) +
                    (creator_val * 0.10) +
                    (trending_val * 0.05) +
                    (diversity_val * 0.05)
                )

                # Boost slightly if the user follows this creator (Personalization boost)
                is_followed = item.author_id in following_ids
                if is_followed:
                    final_score += 15.0 # Boost personalized items

                scored_candidates.append({
                    'item': item,
                    'category': category,
                    'is_followed': is_followed,
                    'score': final_score
                })

                # Increment frequency
                category_counts[category] = category_counts.get(category, 0) + 1

            # Sort by final score descending
            scored_candidates.sort(key=lambda x: x['score'], reverse=True)

            # 6. Apply 80% Personalized vs 20% Discovery split
            # Split items into:
            # - Personalized: Creators they follow, or matches their top interests (score > threshold)
            # - Discovery: Creators they do not follow, or general trends
            personalized_pool = [x['item'].id for x in scored_candidates if x['is_followed']]
            discovery_pool = [x['item'].id for x in scored_candidates if not x['is_followed']]

            # Fallbacks if pools are small
            if len(personalized_pool) < int(limit * 0.8):
                # Pull top scored items into personalized pool even if not followed
                extra_needed = int(limit * 0.8) - len(personalized_pool)
                candidates_not_followed = [x['item'].id for x in scored_candidates if not x['is_followed']]
                personalized_pool += candidates_not_followed[:extra_needed]
                discovery_pool = candidates_not_followed[extra_needed:]

            # Merge lists in a 4:1 ratio (80% / 20%)
            final_feed = []
            p_idx = 0
            d_idx = 0

            while len(final_feed) < limit:
                # Add 4 personalized
                for _ in range(4):
                    if p_idx < len(personalized_pool):
                        val = personalized_pool[p_idx]
                        if val not in final_feed:
                            final_feed.append(val)
                        p_idx += 1
                
                # Add 1 discovery
                if d_idx < len(discovery_pool):
                    val = discovery_pool[d_idx]
                    if val not in final_feed:
                        final_feed.append(val)
                    d_idx += 1
                
                # Safety break
                if p_idx >= len(personalized_pool) and d_idx >= len(discovery_pool):
                    break

            # Fallback to general ranked list if nothing generated
            if not final_feed:
                final_feed = [x['item'].id for x in scored_candidates[:limit]]

            return final_feed
        except Exception as e:
            logger.error(f"[ScoringEngine] Error scoring feed: {e}", exc_info=True)
            return []
