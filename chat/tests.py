from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from chat.models import Message

User = get_user_model()

class ChatAPITests(APITestCase):
    def setUp(self):
        # Create test users with unique email addresses
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        self.unrelated_user = User.objects.create_user(username='unrelated', email='unrelated@example.com', password='password123')
        
        # Create profiles if they don't auto-create (depending on post_save signals, usually CustomUser profile creation is handled)
        # Let's ensure profiles exist if needed, otherwise ignore.
        
    def test_message_auto_deletion_after_5_minutes(self):
        # Authenticate self.user1
        self.client.login(username='user1', password='password123')
        
        # Create a message just now
        msg_now = Message.objects.create(sender=self.user1, receiver=self.user2, content="Hello now")
        
        # Create a message 6 minutes ago
        msg_old = Message.objects.create(sender=self.user1, receiver=self.user2, content="Hello old")
        # Manually alter created_at since auto_now_add is set
        Message.objects.filter(id=msg_old.id).update(created_at=timezone.now() - timezone.timedelta(minutes=6))
        
        # Make request to message list API
        url = reverse('api_chat_messages', kwargs={'username': 'user2'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that only 1 message is returned
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], "Hello now")
        
        # Check that msg_old is deleted from database
        self.assertFalse(Message.objects.filter(id=msg_old.id).exists())
        self.assertTrue(Message.objects.filter(id=msg_now.id).exists())

    def test_manual_message_deletion(self):
        # Authenticate self.user1
        self.client.login(username='user1', password='password123')
        
        msg = Message.objects.create(sender=self.user1, receiver=self.user2, content="Delete me")
        
        url = reverse('api_delete_message', kwargs={'message_id': msg.id})
        
        # Test unauthorized deletion (not logged in)
        self.client.logout()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test unauthorized deletion (logged in as unrelated user)
        self.client.login(username='unrelated', password='password123')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test authorized deletion (as sender user1)
        self.client.login(username='user1', password='password123')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"success": True})
        self.assertFalse(Message.objects.filter(id=msg.id).exists())

    def test_manual_thread_deletion(self):
        # Authenticate self.user1
        self.client.login(username='user1', password='password123')
        
        # Create messages in the thread
        Message.objects.create(sender=self.user1, receiver=self.user2, content="Msg 1")
        Message.objects.create(sender=self.user2, receiver=self.user1, content="Msg 2")
        # Unrelated message thread
        unrelated_msg = Message.objects.create(sender=self.user1, receiver=self.unrelated_user, content="Keep me")
        
        url = reverse('api_delete_thread', kwargs={'username': 'user2'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"success": True})
        
        # Check that user1-user2 messages are deleted
        self.assertEqual(Message.objects.filter(sender=self.user1, receiver=self.user2).count(), 0)
        self.assertEqual(Message.objects.filter(sender=self.user2, receiver=self.user1).count(), 0)
        
        # Check that unrelated thread messages still exist
        self.assertTrue(Message.objects.filter(id=unrelated_msg.id).exists())
