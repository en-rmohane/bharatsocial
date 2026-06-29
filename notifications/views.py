from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer

@login_required
def notifications_view(request):
    return render(request, 'notifications/list.html')

# --- API Endpoints ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list_api(request):
    # Fetch notifications for current user
    notifications = Notification.objects.filter(recipient=request.user).select_related('sender', 'sender__profile', 'post', 'reel', 'comment')[:50]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    notification = Notification.objects.filter(recipient=request.user, id=notification_id).first()
    if notification:
        notification.is_read = True
        notification.save()
        return Response({"success": True})
    return Response({"error": "Notification not found"}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({"success": True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notifications_count(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return Response({"unread_count": count})
