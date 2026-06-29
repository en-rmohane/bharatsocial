from django.urls import path
from . import views

urlpatterns = [
    # Rendered views
    path('notifications/', views.notifications_view, name='notifications'),
    
    # API endpoints
    path('api/notifications/', views.notifications_list_api, name='api_notifications_list'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='api_mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='api_mark_all_notifications_read'),
    path('api/notifications/unread-count/', views.unread_notifications_count, name='api_unread_notifications_count'),
]
