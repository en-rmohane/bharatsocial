from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Story, StoryView, StoryReaction
from .serializers import StorySerializer
from accounts.models import Follow, Block

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def stories_list_create_api(request):
    if request.method == 'GET':
        # Retrieve active stories from followed users and current user
        following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        story_users_ids = list(following_ids) + [request.user.id]
        
        # Exclude content from blocked users
        blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
        blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
        exclude_user_ids = list(blocking_ids) + list(blocked_by_ids)

        # Retrieve active stories (within last 24h)
        stories = Story.active_objects.filter(author_id__in=story_users_ids).exclude(author_id__in=exclude_user_ids).select_related('author', 'author__profile')
        
        # Order by read status and timestamp (unread first)
        serializer = StorySerializer(stories, many=True, context={'request': request})
        return Response(serializer.data)

    if request.method == 'POST':
        media_file = request.FILES.get('media_file')
        if not media_file:
            return Response({"error": "Media file is required"}, status=400)
            
        story = Story.objects.create(author=request.user, media_file=media_file)
        serializer = StorySerializer(story, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_story_viewed(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    # View logs
    view, created = StoryView.objects.get_or_create(story=story, viewer=request.user)
    return Response({"success": True, "created": created})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def react_to_story(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    reaction_type = request.data.get('reaction_type', '❤️')
    
    reaction = StoryReaction.objects.create(
        story=story,
        user=request.user,
        reaction_type=reaction_type
    )
    return Response({"success": True, "reaction": reaction_type})
