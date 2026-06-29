from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Message
from .serializers import MessageSerializer
from accounts.models import CustomUser, Follow

@login_required
def chat_inbox_view(request, username=None):
    return render(request, 'chat/chat.html')

# --- API Endpoints ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_users(request):
    """
    Get a list of users with whom the current user has exchanged messages (recent_chats),
    plus suggestions (followed users and other users) to start new conversations.
    """
    # Auto-delete messages older than 5 minutes (excluding snaps)
    Message.objects.filter(is_snap=False, created_at__lt=timezone.now() - timezone.timedelta(minutes=5)).delete()
    # Auto-delete expired snaps
    Message.objects.filter(is_snap=True, expires_at__lt=timezone.now()).delete()
    
    user_id = request.user.id
    
    # 1. Get users from message history
    history_users = CustomUser.objects.filter(
        Q(sent_messages__receiver=request.user) | Q(received_messages__sender=request.user)
    ).exclude(id=user_id).distinct()
    
    # 2. Get followed users as alternative to start new chats (limit to 7 to prevent N+1 query locks)
    following_users = CustomUser.objects.filter(
        followers__follower=request.user
    ).exclude(id__in=history_users).distinct()[:7]
    
    # 3. Get generic suggestions to chat with
    following_ids = list(following_users.values_list('id', flat=True))
    history_ids = list(history_users.values_list('id', flat=True))
    
    from accounts.models import Block
    blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    
    exclude_ids = history_ids + following_ids + list(blocking_ids) + list(blocked_by_ids) + [user_id]
    other_suggestions = CustomUser.objects.exclude(id__in=exclude_ids).select_related('profile')[:5]
    
    suggested_chat_users = list(following_users) + list(other_suggestions)
    
    # Helper to serialize user info
    def serialize_chat_user(user):
        try:
            last_seen = cache.get(f'last_seen_{user.username}')
        except Exception:
            last_seen = None
        is_online = False
        if last_seen:
            is_online = (timezone.now() - last_seen).total_seconds() < 30

        last_msg = Message.objects.filter(
            Q(sender=request.user, receiver=user) | Q(sender=user, receiver=request.user)
        ).last()
        
        unread_count = Message.objects.filter(
            sender=user, receiver=request.user, is_read=False
        ).count()
        
        avatar_url = '/media/avatars/default.png'
        try:
            if hasattr(user, 'profile') and user.profile and user.profile.avatar:
                avatar_url = user.profile.avatar.url
        except Exception:
            pass
        
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar": avatar_url,
            "is_online": is_online,
            "last_message": last_msg.content if last_msg else ( "[Image]" if (last_msg and last_msg.image) else "" ),
            "last_message_time": last_msg.created_at if last_msg else None,
            "unread_count": unread_count
        }

    recent_chats = []
    for user in history_users:
        recent_chats.append(serialize_chat_user(user))
        
    suggested_users = []
    for user in suggested_chat_users:
        suggested_users.append(serialize_chat_user(user))
        
    # Sort recent chats by last message time using timezone-consistent defaults
    recent_chats.sort(
        key=lambda x: x['last_message_time'] if x['last_message_time'] else timezone.now() - timezone.timedelta(days=365*100),
        reverse=True
    )
    
    return Response({
        "recent_chats": recent_chats,
        "suggested_users": suggested_users
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def message_list_create_api(request, username):
    # Auto-delete messages older than 5 minutes (excluding snaps)
    Message.objects.filter(is_snap=False, created_at__lt=timezone.now() - timezone.timedelta(minutes=5)).delete()
    # Auto-delete expired snaps
    Message.objects.filter(is_snap=True, expires_at__lt=timezone.now()).delete()
    
    other_user = get_object_or_404(CustomUser, username=username)
    
    if request.method == 'GET':
        # Retrieve thread messages
        messages = Message.objects.filter(
            Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
        ).order_by('created_at')
        
        # Mark messages to me as read
        Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        content = request.data.get('content', '')
        image = request.FILES.get('image')
        is_snap = request.data.get('is_snap') == 'true'
        
        if not content and not image:
            return Response({"error": "Content or image is required"}, status=400)
            
        expires_at = None
        if is_snap:
            expires_at = timezone.now() + timezone.timedelta(hours=1)

        # Apply Python face tracking filter overlay using OpenCV and MediaPipe if available
        if is_snap and image:
            import json
            import tempfile
            from django.core.files import File
            from chat.filters_processor import process_video_filters
            
            filter_id = None
            try:
                config = json.loads(content)
                filter_id = config.get('propId') or config.get('filterId')
            except Exception:
                pass
                
            if filter_id and filter_id != 'none':
                # Create input temp file
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_in:
                    for chunk in image.chunks():
                        temp_in.write(chunk)
                    temp_in_path = temp_in.name
                
                # Create output temp file
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_out:
                    temp_out_path = temp_out.name
                
                # Process the filter on python backend
                processed = process_video_filters(temp_in_path, temp_out_path, filter_id)
                
                if processed and os.path.exists(temp_out_path) and os.path.getsize(temp_out_path) > 0:
                    with open(temp_out_path, 'rb') as f:
                        django_file = File(f, name=image.name)
                        message = Message.objects.create(
                            sender=request.user,
                            receiver=other_user,
                            content=content,
                            image=django_file,
                            is_snap=is_snap,
                            expires_at=expires_at
                        )
                    try:
                        os.unlink(temp_out_path)
                    except Exception:
                        pass
                else:
                    # Fallback to original
                    message = Message.objects.create(
                        sender=request.user,
                        receiver=other_user,
                        content=content,
                        image=image,
                        is_snap=is_snap,
                        expires_at=expires_at
                    )
                try:
                    os.unlink(temp_in_path)
                except Exception:
                    pass
            else:
                # No filter chosen
                message = Message.objects.create(
                    sender=request.user,
                    receiver=other_user,
                    content=content,
                    image=image,
                    is_snap=is_snap,
                    expires_at=expires_at
                )
        else:
            # Normal text/image message
            message = Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content,
                image=image,
                is_snap=is_snap,
                expires_at=expires_at
            )
        
        # Trigger Message Notification
        from notifications.models import Notification
        Notification.objects.create(
            recipient=other_user,
            sender=request.user,
            notification_type='message'
        )
        
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_thread_read(request, username):
    other_user = get_object_or_404(CustomUser, username=username)
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    return Response({"success": True})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_message_api(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    if message.sender != request.user and message.receiver != request.user:
        return Response({"error": "Unauthorized to delete this message"}, status=status.HTTP_401_UNAUTHORIZED)
    message.delete()
    return Response({"success": True})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_thread_api(request, username):
    other_user = get_object_or_404(CustomUser, username=username)
    Message.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).delete()
    return Response({"success": True})
