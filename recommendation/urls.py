from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserActivityViewSet, UserInterestViewSet, TrendingTopicsViewSet, RecommendationAnalyticsViewSet

router = DefaultRouter()
router.register(r'activities', UserActivityViewSet, basename='activity')
router.register(r'interests', UserInterestViewSet, basename='interest')
router.register(r'trending', TrendingTopicsViewSet, basename='trending')
router.register(r'analytics', RecommendationAnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
]
