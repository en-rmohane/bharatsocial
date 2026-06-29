from django.urls import path
from . import views

urlpatterns = [
    # Rendered views
    path('direct/t/', views.chat_inbox_view, name='chat_inbox'),
    path('direct/t/<str:username>/', views.chat_inbox_view, name='chat_inbox_user'),
    
    # API endpoints
    path('api/chat/users/', views.get_chat_users, name='api_chat_users'),
    path('api/chat/messages/<str:username>/', views.message_list_create_api, name='api_chat_messages'),
    path('api/chat/messages/<str:username>/read/', views.mark_thread_read, name='api_mark_thread_read'),
    path('api/chat/messages/delete/<int:message_id>/', views.delete_message_api, name='api_delete_message'),
    path('api/chat/messages/delete-thread/<str:username>/', views.delete_thread_api, name='api_delete_thread'),
]
