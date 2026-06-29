from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

from .models import Profile, Follow, Block
from stories.models import Story

User = get_user_model()

class UserAccountTests(TestCase):
    def test_create_user_profile_signal(self):
        # Verify that a Profile is created automatically when a User is created
        user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.bio, '')
        self.assertEqual(user.profile.website, '')

    def test_follow_unfollow_logic(self):
        user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123')
        user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        
        # Follow
        Follow.objects.create(follower=user1, following=user2)
        self.assertTrue(Follow.objects.filter(follower=user1, following=user2).exists())
        self.assertEqual(user2.profile.followers_count, 1)
        self.assertEqual(user1.profile.following_count, 1)

    def test_blocking_logic(self):
        user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123')
        user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        
        Block.objects.create(blocker=user1, blocked=user2)
        self.assertTrue(Block.objects.filter(blocker=user1, blocked=user2).exists())

class StoriesExpiryTests(TestCase):
    def test_active_stories_manager_filters_expired(self):
        user = User.objects.create_user(username='storyuser', email='story@example.com', password='password123')
        
        # 1. Create a fresh story
        story_fresh = Story.objects.create(author=user, media_file='fresh.jpg')
        
        # 2. Create an expired story (older than 24 hours)
        story_expired = Story.objects.create(author=user, media_file='old.jpg')
        # Manually alter created_at using update to bypass auto_now_add override
        Story.objects.filter(id=story_expired.id).update(created_at=timezone.now() - timedelta(hours=25))
        
        # Query active stories
        active_stories = Story.active_objects.all()
        
        self.assertIn(story_fresh, active_stories)
        self.assertNotIn(story_expired, active_stories)
        self.assertEqual(active_stories.count(), 1)

class GamifiedRewardsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pointuser', email='point@example.com', password='password123')

    def test_points_reward_pipeline(self):
        # 1. Start with 0 points
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 0)

        # 2. Create a post -> should add 10 points
        from posts.models import Post
        post = Post.objects.create(author=self.user, caption="My first post")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 10)

        # 3. Like a post -> should add 2 points
        from posts.models import Like
        like = Like.objects.create(user=self.user, post=post)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 12)

        # 4. Comment on post -> should add 5 points
        from posts.models import Comment
        comment = Comment.objects.create(post=post, author=self.user, content="Great stuff!")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 17)

        # 5. Unlike -> should deduct 2 points
        like.delete()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 15)

        # 6. Delete post -> should deduct 10 points (also cascades and deletes comments, triggering comment deduction!)
        # Post (10 pts) + Comment (5 pts) = 15 points to be deducted when post is deleted
        post.delete()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 0)


class DailyLoginStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streakuser', email='streak@example.com', password='password123')
        self.client.login(username='streakuser', password='password123')

    def test_first_time_daily_login(self):
        # On the first request, the user has no last_login_date
        response = self.client.get('/')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.login_streak, 1)
        self.assertEqual(self.user.profile.points, 5)
        self.assertEqual(self.user.profile.last_login_date, timezone.localdate())
        
        # Check messages
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Daily login reward! +5 points awarded. Current streak: 1 day.", str(messages_list[0]))

    def test_same_day_login_does_not_reward_again(self):
        # First request awards points
        self.client.get('/')
        self.user.profile.refresh_from_db()
        initial_points = self.user.profile.points
        self.assertEqual(initial_points, 5)
        
        # Second request on the same day does nothing
        response = self.client.get('/')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.login_streak, 1)
        self.assertEqual(self.user.profile.points, initial_points)
        
        messages_list = list(response.context.get('messages', []))
        login_msgs = [str(m) for m in messages_list if "Daily login reward" in str(m)]
        # There might be the message from first request in session or none depending on middleware clear
        # But there shouldn't be a NEW duplicate message or increase in points.
        # Let's verify points didn't change
        self.assertEqual(self.user.profile.points, 5)

    def test_consecutive_days_streaks(self):
        today = timezone.localdate()
        profile = self.user.profile
        profile.last_login_date = today - timedelta(days=1)
        profile.login_streak = 1
        profile.points = 10
        profile.save()
        
        # Request on day 2
        response = self.client.get('/')
        profile.refresh_from_db()
        self.assertEqual(profile.login_streak, 2)
        self.assertEqual(profile.points, 15)  # 10 + 5
        self.assertEqual(profile.last_login_date, today)

    def test_seven_day_streak_bonus(self):
        today = timezone.localdate()
        profile = self.user.profile
        profile.last_login_date = today - timedelta(days=1)
        profile.login_streak = 6
        profile.points = 100
        profile.save()
        
        # Request on day 7
        response = self.client.get('/')
        profile.refresh_from_db()
        self.assertEqual(profile.login_streak, 7)
        self.assertEqual(profile.points, 155)  # 100 + 5 + 50 bonus
        self.assertEqual(profile.last_login_date, today)
        
        # Check messages
        messages_list = list(response.context['messages'])
        msg_str = " ".join([str(m) for m in messages_list])
        self.assertIn("7-Day Streak Bonus! +50 points!", msg_str)

    def test_thirty_day_streak_bonus(self):
        today = timezone.localdate()
        profile = self.user.profile
        profile.last_login_date = today - timedelta(days=1)
        profile.login_streak = 29
        profile.points = 500
        profile.save()
        
        # Request on day 30
        response = self.client.get('/')
        profile.refresh_from_db()
        self.assertEqual(profile.login_streak, 30)
        self.assertEqual(profile.points, 1005)  # 500 + 5 + 500 bonus
        self.assertEqual(profile.last_login_date, today)
        
        # Check messages
        messages_list = list(response.context['messages'])
        msg_str = " ".join([str(m) for m in messages_list])
        self.assertIn("30-Day Streak Bonus! +500 points!", msg_str)

    def test_broken_streak_reset(self):
        today = timezone.localdate()
        profile = self.user.profile
        profile.last_login_date = today - timedelta(days=3) # 3 days ago
        profile.login_streak = 5
        profile.points = 50
        profile.save()
        
        # Request today (streak broken)
        response = self.client.get('/')
        profile.refresh_from_db()
        self.assertEqual(profile.login_streak, 1) # reset to 1
        self.assertEqual(profile.points, 55)  # 50 + 5
        self.assertEqual(profile.last_login_date, today)
        
        # Check messages
        messages_list = list(response.context['messages'])
        msg_str = " ".join([str(m) for m in messages_list])
        self.assertIn("streak has been reset to 1 day", msg_str)


class FollowersFollowingAPITests(TestCase):
    def setUp(self):
        from django.urls import reverse
        from rest_framework.test import APIClient
        self.user1 = User.objects.create_user(username='alice', email='alice@example.com', password='password123')
        self.user2 = User.objects.create_user(username='bob', email='bob@example.com', password='password123')
        self.user3 = User.objects.create_user(username='charlie', email='charlie@example.com', password='password123')
        
        Follow.objects.create(follower=self.user2, following=self.user1) # bob follows alice
        Follow.objects.create(follower=self.user1, following=self.user3) # alice follows charlie
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def test_get_followers_list(self):
        url = reverse('api_user_followers', kwargs={'username': 'alice'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'bob')
        self.assertFalse(response.data[0]['is_following'])

    def test_get_following_list(self):
        url = reverse('api_user_following', kwargs={'username': 'alice'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'charlie')
        self.assertTrue(response.data[0]['is_following'])

class EmailVerificationTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.user = User.objects.create_user(username='verifyme', email='verifyme@example.com', password='password123')
        
    def test_check_username_api(self):
        url = reverse('api_check_username')
        
        # Test username that exists
        response = self.client.get(url, {'username': 'verifyme'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['available'])
        
        # Test username that doesn't exist
        response = self.client.get(url, {'username': 'unique_user'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['available'])
        
    def test_signup_stores_session_data_and_sends_otp(self):
        url = reverse('signup')
        payload = {
            'first_name': 'New',
            'last_name': 'User',
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'BharatSocialSecretPass123!',
            'password2': 'BharatSocialSecretPass123!'
        }
        from unittest.mock import patch
        with patch('accounts.views.send_mail') as mock_send_mail:
            response = self.client.post(url, payload)
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, reverse('signup_verify_otp'))
            
            # Should have sent an email containing a 6 digit code
            self.assertTrue(mock_send_mail.called)
            # Should NOT create database record yet
            self.assertFalse(User.objects.filter(username='newuser').exists())
            
    def test_signup_otp_verification_success(self):
        # Set up active signup session
        session = self.client.session
        session['signup_data'] = {
            'first_name': 'Verify',
            'last_name': 'Me',
            'username': 'verifieduser',
            'email': 'verified@example.com',
            'password': 'password123'
        }
        session['signup_otp'] = '123456'
        from django.utils.timezone import now
        session['signup_otp_time'] = now().isoformat()
        session.save()
        
        url = reverse('signup_verify_otp')
        response = self.client.post(url, {'otp': '123456'})
        
        # Verify redirect to feed
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('feed'))
        
        # Verify user created in DB and verified
        user = User.objects.get(username='verifieduser')
        self.assertEqual(user.first_name, 'Verify')
        self.assertEqual(user.last_name, 'Me')
        self.assertTrue(user.email_verified)
        
    def test_signup_otp_verification_failure(self):
        session = self.client.session
        session['signup_data'] = {
            'first_name': 'Fail',
            'last_name': 'Me',
            'username': 'failuser',
            'email': 'fail@example.com',
            'password': 'password123'
        }
        session['signup_otp'] = '123456'
        from django.utils.timezone import now
        session['signup_otp_time'] = now().isoformat()
        session.save()
        
        url = reverse('signup_verify_otp')
        response = self.client.post(url, {'otp': '000000'})
        
        # Verify stays on verify otp template showing error
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='failuser').exists())

    def test_google_oauth_mock_flow(self):
        # Trigger redirect view (local dev bypass)
        url = reverse('google_login')
        with self.settings(GOOGLE_CLIENT_ID='MOCK_CLIENT_ID', GOOGLE_CLIENT_SECRET='MOCK_CLIENT_SECRET'):
            response = self.client.get(url)
        
        # Should redirect directly to callback with code=mock_dev_google_code
        self.assertEqual(response.status_code, 302)
        self.assertIn('google/callback/?code=mock_dev_google_code', response.url)
        
        # Callback check
        callback_url = reverse('google_callback')
        callback_response = self.client.get(callback_url, {'code': 'mock_dev_google_code'})
        
        # Should redirect to feed
        self.assertEqual(callback_response.status_code, 302)
        self.assertRedirects(callback_response, reverse('feed'))
        
        # User should be created with email_verified = True
        google_user = User.objects.get(email="google_test_user@gmail.com")
        self.assertEqual(google_user.first_name, 'Google')
        self.assertEqual(google_user.last_name, 'User')
        self.assertTrue(google_user.email_verified)




