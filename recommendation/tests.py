from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch

from posts.models import Post, Like, Comment, SavePost
from reels.models import Reel, ReelLike, ReelComment
from accounts.models import Follow, Block
from recommendation.models import PostMetadata, ReelMetadata, UserActivity, UserInterest, FeedCache, TrendingTopics
from recommendation.services import UserActivityLogger
from recommendation.algorithms import ScoringEngine

User = get_user_model()

class RecommendationTests(TestCase):
    def setUp(self):
        # Setup users
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        self.user3 = User.objects.create_user(username='user3', email='user3@example.com', password='password123')

        # Create posts and trigger signal parsing
        self.post1 = Post.objects.create(author=self.user2, caption="Great cricket match today! #cricket #ipl")
        self.post2 = Post.objects.create(author=self.user3, caption="Loving this new travel destination #travel #wanderlust")
        self.post3 = Post.objects.create(author=self.user2, caption="Tech talk about django and python coding #tech #coding")

        # Create reels
        self.reel1 = Reel.objects.create(author=self.user2, caption="Awesome cricket wickets compilation! #cricket")
        self.reel2 = Reel.objects.create(author=self.user3, caption="Exploring the mountains in India #travel")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def test_metadata_created_via_signals(self):
        # Metadata should be automatically created/updated when Post or Reel is saved
        post_meta = PostMetadata.objects.filter(post=self.post1).first()
        self.assertIsNotNone(post_meta)
        self.assertEqual(post_meta.category, 'Cricket')
        self.assertIn('cricket', post_meta.hashtags)
        
        reel_meta = ReelMetadata.objects.filter(reel=self.reel1).first()
        self.assertIsNotNone(reel_meta)
        self.assertEqual(reel_meta.category, 'Cricket')

    def test_user_activity_logger_and_realtime_interest(self):
        # Log post impression
        activity = UserActivityLogger.log_activity(
            user=self.user1,
            activity_type='post_impression',
            content_type='post',
            content_id=self.post1.id
        )
        self.assertIsNotNone(activity)
        self.assertEqual(activity.category, 'Cricket')
        
        # Check that user interest was created
        interest = UserInterest.objects.filter(user=self.user1, topic='Cricket').first()
        self.assertIsNotNone(interest)
        self.assertEqual(interest.score, 2.0) # base impression weight is 2.0

    def test_social_activity_signals(self):
        # Liking a post should log activity and update engagement score
        Like.objects.create(user=self.user1, post=self.post1)
        
        # check user activity
        act = UserActivity.objects.filter(user=self.user1, activity_type='like', content_type='post', content_id=self.post1.id).first()
        self.assertIsNotNone(act)
        
        # check post engagement score
        post_meta = PostMetadata.objects.get(post=self.post1)
        self.assertEqual(post_meta.engagement_score, 2.0) # 1 like * 2.0 = 2.0

    def test_follow_unfollow_signals(self):
        Follow.objects.create(follower=self.user1, following=self.user2)
        
        # check follow activity
        follow_act = UserActivity.objects.filter(user=self.user1, activity_type='follow', content_id=self.user2.id).first()
        self.assertIsNotNone(follow_act)
        
        # delete follow (unfollow)
        Follow.objects.filter(follower=self.user1, following=self.user2).delete()
        unfollow_act = UserActivity.objects.filter(user=self.user1, activity_type='unfollow', content_id=self.user2.id).first()
        self.assertIsNotNone(unfollow_act)

    def test_scoring_engine_and_blocking_exclusions(self):
        # Block user3
        Block.objects.create(blocker=self.user1, blocked=self.user3)
        
        # Feed candidates should not include posts from user3 (post2)
        recommended_posts = ScoringEngine.get_recommended_feed(self.user1, feed_type='post')
        self.assertNotIn(self.post2.id, recommended_posts)
        self.assertIn(self.post1.id, recommended_posts)
        self.assertIn(self.post3.id, recommended_posts)

    @patch('recommendation.cache.RedisCacheManager.get_feed_cache')
    def test_feed_cache_fallbacks(self, mock_get_feed_cache):
        # Test that feed endpoint serves from cache when available
        mock_get_feed_cache.return_value = [self.post3.id, self.post1.id]
        
        url = reverse('api_post_feed')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        results = response.data['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], self.post3.id)
        self.assertEqual(results[1]['id'], self.post1.id)

    def test_log_activity_api(self):
        url = reverse('activity-list')
        payload = {
            'activity_type': 'search',
            'category': '#ipl',
            'device': 'Mobile',
            'language': 'en'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['activity_type'], 'search')
        self.assertEqual(response.data['category'], '#ipl')

    def test_user_interests_api(self):
        # Populate interests
        UserInterest.objects.create(user=self.user1, topic='Tech', score=42.0)
        
        url = reverse('interest-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['topic'], 'Tech')
        self.assertEqual(response.data[0]['score'], 42.0)

    def test_trending_topics_api(self):
        TrendingTopics.objects.create(topic_type='category', name='Travel', score=15.0)
        
        url = reverse('trending-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Travel')
        self.assertEqual(response.data[0]['score'], 15.0)

    def test_sentiment_classification_utility(self):
        from recommendation.utilities import analyze_sentiment
        # Positive caption
        pos_score = analyze_sentiment("Great and wonderful ipl cricket match! ❤️")
        self.assertGreater(pos_score, 0.0)
        
        # Negative caption
        neg_score = analyze_sentiment("Worst, bad, and ugly experience ever. 👎")
        self.assertLess(neg_score, 0.0)
        
        # Neutral caption
        neutral_score = analyze_sentiment("This is a simple table.")
        self.assertEqual(neutral_score, 0.0)

    def test_sentiment_based_recommendation_ranking(self):
        # Create posts with positive, neutral and negative captions
        pos_post = Post.objects.create(author=self.user2, caption="Awesome and great day! ❤️")
        neg_post = Post.objects.create(author=self.user2, caption="Bad, worst, and terrible pain. 😭")
        
        # Verify that their metadata sentiment scores got calculated via signals
        pos_meta = PostMetadata.objects.get(post=pos_post)
        neg_meta = PostMetadata.objects.get(post=neg_post)
        self.assertGreater(pos_meta.sentiment_score, 0.0)
        self.assertLess(neg_meta.sentiment_score, 0.0)
        
        # Simulate user1 liking the positive post to set positive preferred sentiment
        Like.objects.create(user=self.user1, post=pos_post)
        
        # Run scoring engine recommendations
        recommended_ids = ScoringEngine.get_recommended_feed(self.user1, feed_type='post')
        
        # Verify that pos_post is recommended higher or exists, and Neg post is ranked lower
        self.assertIn(pos_post.id, recommended_ids)
        if neg_post.id in recommended_ids:
            # pos_post should rank before neg_post due to sentiment matching score boost
            pos_index = recommended_ids.index(pos_post.id)
            neg_index = recommended_ids.index(neg_post.id)
            self.assertLess(pos_index, neg_index)
