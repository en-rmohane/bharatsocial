from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

class AIAssistAPITests(TestCase):
    def setUp(self):
        from unittest.mock import patch
        self.groq_patcher = patch('posts.ai_helpers.AIPlatformConnector.call_groq_api', return_value=None)
        self.mock_groq = self.groq_patcher.start()

        self.ollama_patcher = patch('posts.ai_helpers.AIPlatformConnector.call_ollama_api', return_value=None)
        self.mock_ollama = self.ollama_patcher.start()

        self.client = APIClient()
        self.user = User.objects.create_user(username='aitestuser', email='aitest@example.com', password='password123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('api_ai_assist')

    def tearDown(self):
        self.groq_patcher.stop()
        self.ollama_patcher.stop()

    def test_ai_assist_response_keys(self):
        payload = {
            'category': 'Travel',
            'keywords': 'sunset, mountains, nature',
            'length': 'Medium',
            'language': 'en'
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('best_time', data)
        self.assertIn('hashtags', data)
        self.assertIn('caption', data)
        self.assertIn('scores', data)
        self.assertIn('safety', data)
        
        self.assertIn('#sunset', data['hashtags'])
        self.assertIn('#mountains', data['hashtags'])
        self.assertIn('#nature', data['hashtags'])

    def test_ai_content_improver(self):
        url = reverse('api_ai_content_improver')
        payload = {'caption': 'A simple photo at the beach'}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('improved_caption', response.json())

    def test_ai_translation(self):
        url = reverse('api_ai_translation')
        payload = {'caption': 'Hello world #nature', 'target_lang': 'hi'}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('translated_text', response.json())

    def test_ai_bio_generator(self):
        url = reverse('api_ai_bio_generator')
        payload = {'interests': 'coding, music', 'style': 'Creator'}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('bio', response.json())

    def test_ai_safety_filter(self):
        url = reverse('api_ai_safety_filter')
        payload = {'text': 'Double your cash, click here to win!'}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_safe'])

    def test_ai_connector_fallback_on_api_error(self):
        from unittest.mock import patch
        from posts.ai_helpers import AIPlatformConnector
        
        # Test that if call_ollama_api returns None, we still get a valid caption and hashtags
        with patch.object(AIPlatformConnector, 'call_ollama_api', return_value=None):
            caption = AIPlatformConnector.generate_captions('Travel', 'sunset', 'Short', 'en')
            self.assertIsNotNone(caption)
            self.assertIn('sunset', caption.lower())
            
            tags = AIPlatformConnector.generate_hashtags(caption, 'Travel', 'sunset')
            self.assertIn('#sunset', tags)
            
    def test_ai_connector_live_ollama_api_success(self):
        from unittest.mock import patch
        from posts.ai_helpers import AIPlatformConnector
        
        mocked_caption = "A beautiful live sunset caption 🌅"
        with patch.object(AIPlatformConnector, 'call_ollama_api', return_value=mocked_caption):
            caption = AIPlatformConnector.generate_captions('Travel', 'sunset', 'Short', 'en')
            self.assertEqual(caption, mocked_caption)

    def test_non_repeating_captions_session_in_api(self):
        # Hit the AI Assist endpoint multiple times and verify that the generated captions differ
        payload = {
            'category': 'Travel',
            'keywords': 'sunset',
            'length': 'Medium',
            'language': 'en'
        }
        
        generated_captions = set()
        for _ in range(5):
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(response.status_code, 200)
            caption = response.json()['caption']
            generated_captions.add(caption)
            
        # Since we use randomized fallback openings/middles/closings + random variation suffixes,
        # they should be unique (no repeats).
        self.assertGreater(len(generated_captions), 1)
        
        # Verify that session history list exists and contains entries
        session = self.client.session
        self.assertIn('generated_captions_history', session)
        self.assertEqual(len(session['generated_captions_history']), 5)

    def test_support_for_new_categories(self):
        # Verify that a newly added category, e.g., 'Sports', generates a valid caption
        payload = {
            'category': 'Sports',
            'keywords': 'cricket',
            'length': 'Medium',
            'language': 'en'
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        
        caption = response.json()['caption']
        self.assertIsNotNone(caption)
        self.assertIn('cricket', caption.lower())

    def test_ai_caption_feedback_api(self):
        from posts.models import AICaptionFeedback
        url = reverse('api_ai_assist_feedback')
        payload = {
            'category': 'Travel',
            'keywords': 'mountains',
            'caption': 'Stunning peaks view',
            'rating': 1
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify saved in db
        feedback = AICaptionFeedback.objects.get(id=response.json()['feedback_id'])
        self.assertEqual(feedback.category, 'Travel')
        self.assertEqual(feedback.rating, 1)
        self.assertEqual(feedback.generated_caption, 'Stunning peaks view')

    def test_ai_caption_feedback_learning_loop(self):
        from posts.models import AICaptionFeedback
        from posts.ai_helpers import AIPlatformConnector
        from unittest.mock import patch
        
        # Stop setup patchers temporarily to control mock specifically for this test
        self.groq_patcher.stop()
        
        # Create some liked and disliked captions in the database
        AICaptionFeedback.objects.create(
            user=self.user,
            category='Travel',
            keywords='sunset',
            generated_caption='LOVED_CAPTION_123',
            rating=1
        )
        AICaptionFeedback.objects.create(
            user=self.user,
            category='Travel',
            keywords='sunset',
            generated_caption='DISLIKED_CAPTION_987',
            rating=-1
        )
        
        # Mock call_groq_api to capture the system prompt
        with patch.object(AIPlatformConnector, 'call_groq_api') as mock_groq:
            mock_groq.return_value = "Mocked Response"
            
            AIPlatformConnector.generate_captions('Travel', 'sunset', 'Medium', 'en')
            
            # Check that call_groq_api was called
            self.assertTrue(mock_groq.called)
            
            # Inspect system_prompt argument
            call_args = mock_groq.call_args
            system_prompt = call_args[1].get('system_prompt', '')
            
            # Verify that the positive and negative few-shot examples were injected!
            self.assertIn('LOVED_CAPTION_123', system_prompt)
            self.assertIn('DISLIKED_CAPTION_987', system_prompt)
            self.assertIn('examples of captions that users LIKED', system_prompt)
            self.assertIn('examples of captions that users DISLIKED', system_prompt)
            
        # Restart setup patcher for other tests tearDown
        self.groq_patcher.start()


