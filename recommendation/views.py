from django.db.models import Avg
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import UserActivity, UserInterest, RecommendationAnalytics, CreatorScore, TrendingTopics
from .serializers import (
    UserActivitySerializer, 
    UserInterestSerializer, 
    CreatorScoreSerializer, 
    TrendingTopicsSerializer, 
    RecommendationAnalyticsSerializer
)
from .services import UserActivityLogger

class UserActivityViewSet(viewsets.ModelViewSet):
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        activity_type = request.data.get('activity_type')
        content_type = request.data.get('content_type')
        content_id = request.data.get('content_id')
        
        try:
            duration = float(request.data.get('duration', 0.0))
        except (ValueError, TypeError):
            duration = 0.0
            
        device = request.data.get('device', '')
        language = request.data.get('language', '')
        category = request.data.get('category', '')

        if not activity_type:
            return Response({'error': 'activity_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        activity = UserActivityLogger.log_activity(
            user=request.user,
            activity_type=activity_type,
            content_type=content_type,
            content_id=content_id,
            duration=duration,
            device=device,
            language=language,
            category=category
        )

        if activity:
            return Response(UserActivitySerializer(activity).data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Failed to log activity'}, status=status.HTTP_400_BAD_REQUEST)

class UserInterestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserInterest.objects.all()
    serializer_class = UserInterestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class TrendingTopicsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrendingTopics.objects.all()
    serializer_class = TrendingTopicsSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecommendationAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RecommendationAnalytics.objects.all()
    serializer_class = RecommendationAnalyticsSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        total_activities = UserActivity.objects.count()
        clicks = UserActivity.objects.filter(activity_type='like').count()
        comments = UserActivity.objects.filter(activity_type='comment').count()
        saves = UserActivity.objects.filter(activity_type='save').count()
        impressions = UserActivity.objects.filter(activity_type__in=['post_impression', 'reel_impression']).count()
        
        ctr = 0.0
        if impressions > 0:
            ctr = (clicks + comments + saves) / impressions * 100.0

        top_categories = list(UserInterest.objects.values('topic').annotate(avg_score=Avg('score')).order_by('-avg_score')[:5])

        return Response({
            'total_activities_logged': total_activities,
            'total_impressions': impressions,
            'total_engagements': clicks + comments + saves,
            'click_through_rate': ctr,
            'top_categories': top_categories
        })
