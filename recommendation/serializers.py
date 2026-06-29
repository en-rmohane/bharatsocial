from rest_framework import serializers
from .models import UserActivity, UserInterest, RecommendationAnalytics, CreatorScore, TrendingTopics

class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = '__all__'

class UserInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInterest
        fields = '__all__'

class CreatorScoreSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='creator.username', read_only=True)
    class Meta:
        model = CreatorScore
        fields = '__all__'

class TrendingTopicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrendingTopics
        fields = '__all__'

class RecommendationAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationAnalytics
        fields = '__all__'
