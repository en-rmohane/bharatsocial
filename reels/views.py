from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Reel, ReelComment, ReelLike
from .serializers import ReelSerializer, ReelCommentSerializer
from accounts.models import Block

@login_required
def reels_feed_view(request):
    return render(request, 'reels/reels_feed.html')

@login_required
def create_reel_view(request):
    if request.method == 'POST':
        video_file = request.FILES.get('video_file')
        caption = request.POST.get('caption', '')

        if not video_file:
            messages.error(request, "Please select a video file.")
            return redirect('create_reel')

        reel = Reel.objects.create(author=request.user, video_file=video_file, caption=caption)
        messages.success(request, "Reel posted successfully!")
        return redirect('reels_feed')

    return render(request, 'reels/create_reel.html')

# --- API Endpoints ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reels_list_api(request):
    # Exclude blocked user content
    blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    exclude_user_ids = list(blocking_ids) + list(blocked_by_ids)

    from recommendation.cache import RedisCacheManager
    from recommendation.models import FeedCache
    from recommendation.algorithms import ScoringEngine
    from recommendation.services import UserActivityLogger
    from django.db.models import Case, When

    # Try to load recommended reels from cache
    recommended_ids = RedisCacheManager.get_feed_cache(request.user.id, 'reel')
    if not recommended_ids:
        feed_cache = FeedCache.objects.filter(user=request.user, feed_type='reel').first()
        if feed_cache:
            recommended_ids = feed_cache.content_ids
        else:
            recommended_ids = ScoringEngine.get_recommended_feed(request.user, feed_type='reel', limit=50)

    if recommended_ids:
        # Preserve recommendation ordering using Case/When
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(recommended_ids)])
        reels = Reel.objects.filter(id__in=recommended_ids).exclude(author_id__in=exclude_user_ids).order_by(preserved_order).select_related('author', 'author__profile')
    else:
        reels = Reel.objects.exclude(author_id__in=exclude_user_ids).select_related('author', 'author__profile')
    
    # Log reel impression activities for this batch
    for r in reels:
        UserActivityLogger.log_activity(
            user=request.user,
            activity_type='reel_impression',
            content_type='reel',
            content_id=r.id
        )

    serializer = ReelSerializer(reels, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_like_reel(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    like_query = ReelLike.objects.filter(user=request.user, reel=reel)

    if like_query.exists():
        like_query.delete()
        liked = False
    else:
        ReelLike.objects.create(user=request.user, reel=reel)
        liked = True

        # Trigger Notification
        if reel.author != request.user:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=reel.author,
                sender=request.user,
                notification_type='reel_like',
                reel=reel
            )

    return Response({
        "liked": liked,
        "likes_count": reel.likes.count()
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def reel_comments_api(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)

    if request.method == 'GET':
        comments = ReelComment.objects.filter(reel=reel).select_related('author', 'author__profile')
        serializer = ReelCommentSerializer(comments, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        content = request.data.get('content')
        if not content:
            return Response({"error": "Content is required"}, status=400)

        comment = ReelComment.objects.create(
            reel=reel,
            author=request.user,
            content=content
        )

        # Trigger Notification
        if reel.author != request.user:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=reel.author,
                sender=request.user,
                notification_type='reel_comment',
                reel=reel,
                comment=None # Notifications can optionally point to Post comment, not Reel comment, so we handle it gracefully
            )

        serializer = ReelCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_reel(request, reel_id):
    reel = get_object_or_404(Reel, id=reel_id)
    if reel.author != request.user:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

    reel.delete()
    return Response({"success": True})
