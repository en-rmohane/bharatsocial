from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework import status
from .ai_helpers import AIPlatformConnector
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Post, PostMedia, Comment, Like, SavePost, SavedCollection, Hashtag, AICaptionFeedback
from .serializers import PostSerializer, CommentSerializer
from accounts.models import Follow, Block, CustomUser
from stories.models import Story

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 20

@login_required
def feed_view(request):
    # Retrieve active stories from followed users and current user
    following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    story_users_ids = list(following_ids) + [request.user.id]
    
    # Filter active stories (within 24 hours) grouped by author
    active_stories = Story.active_objects.filter(author_id__in=story_users_ids).select_related('author', 'author__profile')
    
    # Annotate if viewed by current user
    for story in active_stories:
        story.has_viewed = story.views.filter(viewer=request.user).exists()
        
    # Group stories by user for tray
    user_stories_map = {}
    for story in active_stories:
        if story.author not in user_stories_map:
            user_stories_map[story.author] = []
        user_stories_map[story.author].append(story)
        
    context = {
        'user_stories': user_stories_map,
    }
    return render(request, 'posts/feed.html', context)

@login_required
def explore_view(request):
    # Popular hashtags
    popular_hashtags = Hashtag.objects.annotate(posts_count=Count('posts')).order_by('-posts_count')[:6]
    
    # Suggested users
    following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    exclude_ids = list(following_ids) + list(blocking_ids) + list(blocked_by_ids) + [request.user.id]
    
    suggested_users = CustomUser.objects.exclude(id__in=exclude_ids).select_related('profile')[:4]
    
    context = {
        'popular_hashtags': popular_hashtags,
        'suggested_users': suggested_users,
    }
    return render(request, 'posts/explore.html', context)

@login_required
def create_post_view(request):
    if request.method == 'POST':
        caption = request.POST.get('caption', '')
        location = request.POST.get('location', '')
        media_files = request.FILES.getlist('media_files')

        if not media_files:
            messages.error(request, "Please upload at least one image or video.")
            return redirect('create_post')

        post = Post.objects.create(author=request.user, caption=caption, location=location)
        
        for i, file in enumerate(media_files):
            PostMedia.objects.create(post=post, file=file, order=i)

        messages.success(request, "Post shared successfully!")
        return redirect('feed')

    return render(request, 'posts/create_post.html')

@login_required
def post_detail_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'posts/post_detail.html', {'post': post})

# --- Django REST Framework Endpoints ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def post_feed_api(request):
    # Exclude blocked/blocking content
    blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    exclude_user_ids = list(blocking_ids) + list(blocked_by_ids)

    from recommendation.cache import RedisCacheManager
    from recommendation.models import FeedCache
    from recommendation.algorithms import ScoringEngine
    from recommendation.services import UserActivityLogger
    from django.db.models import Case, When

    # Try to load recommended posts from cache
    recommended_ids = RedisCacheManager.get_feed_cache(request.user.id, 'post')
    if not recommended_ids:
        feed_cache = FeedCache.objects.filter(user=request.user, feed_type='post').first()
        if feed_cache:
            recommended_ids = feed_cache.content_ids
        else:
            recommended_ids = ScoringEngine.get_recommended_feed(request.user, feed_type='post', limit=100)

    if recommended_ids:
        # Preserve recommendation ordering using Case/When
        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(recommended_ids)])
        posts = Post.objects.filter(id__in=recommended_ids).exclude(author_id__in=exclude_user_ids).order_by(preserved_order).prefetch_related('media', 'hashtags').select_related('author', 'author__profile')
    else:
        # Feed should contain posts from followed users + own posts
        following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        feed_user_ids = list(following_ids) + [request.user.id]
        
        posts = Post.objects.filter(author_id__in=feed_user_ids).exclude(author_id__in=exclude_user_ids).prefetch_related('media', 'hashtags').select_related('author', 'author__profile')
        
        # Fallback to explore posts if feed is empty
        if not posts.exists():
            posts = Post.objects.exclude(author_id__in=exclude_user_ids).prefetch_related('media', 'hashtags').select_related('author', 'author__profile')

    paginator = StandardResultsSetPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    # Log post impression activities for this paginated batch
    for p in paginated_posts:
        UserActivityLogger.log_activity(
            user=request.user,
            activity_type='post_impression',
            content_type='post',
            content_id=p.id
        )

    serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def explore_posts_api(request):
    # Exclude blocked/blocking content
    blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    exclude_user_ids = list(blocking_ids) + list(blocked_by_ids)

    # Search / hashtags filtering
    query = request.GET.get('q', '')
    hashtag = request.GET.get('hashtag', '')
    
    posts = Post.objects.exclude(author_id__in=exclude_user_ids).prefetch_related('media', 'hashtags').select_related('author', 'author__profile')
    
    if hashtag:
        posts = posts.filter(hashtags__name=hashtag.lower())
    elif query:
        posts = posts.filter(
            Q(caption__icontains=query) |
            Q(location__icontains=query) |
            Q(author__username__icontains=query)
        )
        
    paginator = StandardResultsSetPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like_query = Like.objects.filter(user=request.user, post=post)
    
    if like_query.exists():
        like_query.delete()
        liked = False
    else:
        Like.objects.create(user=request.user, post=post)
        liked = True
        
        # Trigger Notification
        if post.author != request.user:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='like',
                post=post
            )
            
    return Response({
        "liked": liked,
        "likes_count": post.likes.count()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_save_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    save_query = SavePost.objects.filter(user=request.user, post=post)
    
    if save_query.exists():
        save_query.delete()
        saved = False
    else:
        SavePost.objects.create(user=request.user, post=post)
        saved = True
        
    return Response({"saved": saved})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comments_api(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'GET':
        # Get parent comments only (nested replies are nested inside parent serializer)
        comments = Comment.objects.filter(post=post, parent=None).select_related('author', 'author__profile').prefetch_related('replies', 'replies__author', 'replies__author__profile')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
        
    if request.method == 'POST':
        content = request.data.get('content')
        parent_id = request.data.get('parent_id') # For nested reply support
        
        if not content:
            return Response({"error": "Content is required"}, status=400)
            
        parent_comment = None
        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)

        comment = Comment.objects.create(
            post=post,
            author=request.user,
            content=content,
            parent=parent_comment
        )
        
        # Trigger Notification
        if post.author != request.user:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='comment',
                post=post,
                comment=comment
            )
            
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.author != request.user and comment.post.author != request.user:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        
    comment.delete()
    return Response({"success": True})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    
    post.delete()
    return Response({"success": True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_autocomplete(request):
    query = request.GET.get('q', '')
    if len(query) < 1:
        return Response({"users": [], "hashtags": []})
        
    users = CustomUser.objects.filter(username__icontains=query).select_related('profile')[:5]
    hashtags = Hashtag.objects.filter(name__icontains=query)[:5]
    
    user_data = [{"username": u.username, "avatar": u.profile.avatar.url} for u in users]
    hashtag_data = [{"name": h.name} for h in hashtags]
    
    return Response({
        "users": user_data,
        "hashtags": hashtag_data
    })

import random
from django.utils import timezone

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_assist_api(request):
    category = request.data.get('category', 'General')
    keywords = request.data.get('keywords', '').strip()
    length = request.data.get('length', 'Medium')
    language = request.data.get('language', 'en')
    
    # 1. Best posting time
    peak_times = [
        "Today, 6:30 PM - 9:00 PM (IST)",
        "Today, 9:15 PM - 11:00 PM (IST)",
        "Tomorrow, 12:30 PM - 2:30 PM (IST)",
        "Tomorrow, 7:00 PM - 9:30 PM (IST)"
    ]
    best_time = random.choice(peak_times)
    
    # 2. Generate Caption using helper (checking session history to prevent repeats)
    history = request.session.get('generated_captions_history', [])
    caption = ""
    # Try up to 15 times to generate a unique, non-repeating caption
    for _ in range(15):
        cand = AIPlatformConnector.generate_captions(category, keywords, length, language)
        if cand not in history:
            caption = cand
            break
            
    if not caption:
        # If all candidates are somehow repeats, generate one anyway
        caption = AIPlatformConnector.generate_captions(category, keywords, length, language)
        
    history.append(caption)
    if len(history) > 50:
        history.pop(0)
    request.session['generated_captions_history'] = history
    
    # 3. Generate Hashtags
    hashtags = AIPlatformConnector.generate_hashtags(caption, category, keywords)
    
    # 4. Generate preview scores
    scores = AIPlatformConnector.calculate_preview_score(caption, hashtags)
    
    # 5. Run safety filter
    safety = AIPlatformConnector.safety_filter(caption)
    
    return Response({
        "caption": caption,
        "hashtags": hashtags,
        "best_time": best_time,
        "scores": scores,
        "safety": safety
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_content_improver_api(request):
    caption = request.data.get('caption', '')
    improved_caption = AIPlatformConnector.improve_content(caption)
    return Response({"improved_caption": improved_caption})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_post_preview_score_api(request):
    caption = request.data.get('caption', '')
    hashtags = request.data.get('hashtags', [])
    scores = AIPlatformConnector.calculate_preview_score(caption, hashtags)
    return Response(scores)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_translation_api(request):
    caption = request.data.get('caption', '')
    target_lang = request.data.get('target_lang', 'hi')
    result = AIPlatformConnector.translate_caption(caption, target_lang)
    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_comment_suggester_api(request):
    caption = request.data.get('caption', '')
    tone = request.data.get('tone', 'Friendly')
    suggestions = AIPlatformConnector.suggest_comments(caption, tone)
    return Response({"suggestions": suggestions})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_bio_generator_api(request):
    interests = request.data.get('interests', '')
    style = request.data.get('style', 'Creator')
    bio = AIPlatformConnector.generate_bio(interests, style)
    return Response({"bio": bio})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_trend_discovery_api(request):
    niche = request.data.get('niche', 'General')
    trends = AIPlatformConnector.get_trend_discovery(niche)
    hashtag_trends = AIPlatformConnector.get_trending_suggestions()
    return Response({
        "ideas": trends,
        "hashtag_trends": hashtag_trends
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_safety_filter_api(request):
    text = request.data.get('text', '')
    result = AIPlatformConnector.safety_filter(text)
    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_caption_feedback_api(request):
    category = request.data.get('category', 'General')
    keywords = request.data.get('keywords', '').strip()
    caption = request.data.get('caption', '').strip()
    rating = int(request.data.get('rating', 1))
    
    if not caption:
        return Response({"error": "Caption content is required."}, status=400)
        
    feedback = AICaptionFeedback.objects.create(
        user=request.user,
        category=category,
        keywords=keywords,
        generated_caption=caption,
        rating=rating
    )
    return Response({"success": True, "feedback_id": feedback.id})

