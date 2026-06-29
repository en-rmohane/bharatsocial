from django.urls import path
from . import views

urlpatterns = [
    # Rendered pages
    path('', views.feed_view, name='feed'),
    path('explore/', views.explore_view, name='explore'),
    path('post/create/', views.create_post_view, name='create_post'),
    path('post/<int:post_id>/', views.post_detail_view, name='post_detail'),
    
    # API endpoints
    path('api/posts/feed/', views.post_feed_api, name='api_post_feed'),
    path('api/posts/explore/', views.explore_posts_api, name='api_explore_posts'),
    path('api/posts/<int:post_id>/like/', views.toggle_like_post, name='api_toggle_like_post'),
    path('api/posts/<int:post_id>/save/', views.toggle_save_post, name='api_toggle_save_post'),
    path('api/posts/<int:post_id>/comments/', views.comments_api, name='api_post_comments'),
    path('api/comments/<int:comment_id>/delete/', views.delete_comment, name='api_delete_comment'),
    path('api/posts/<int:post_id>/delete/', views.delete_post, name='api_delete_post'),
    path('api/search/autocomplete/', views.search_autocomplete, name='api_search_autocomplete'),
    path('api/posts/ai-assist/', views.ai_assist_api, name='api_ai_assist'),
    path('api/ai/content-improver/', views.ai_content_improver_api, name='api_ai_content_improver'),
    path('api/ai/post-preview-score/', views.ai_post_preview_score_api, name='api_ai_post_preview_score'),
    path('api/ai/translation/', views.ai_translation_api, name='api_ai_translation'),
    path('api/ai/comment-suggester/', views.ai_comment_suggester_api, name='api_ai_comment_suggester'),
    path('api/ai/bio-generator/', views.ai_bio_generator_api, name='api_ai_bio_generator'),
    path('api/ai/trend-discovery/', views.ai_trend_discovery_api, name='api_ai_trend_discovery'),
    path('api/ai/safety-filter/', views.ai_safety_filter_api, name='api_ai_safety_filter'),
    path('api/posts/ai-assist/feedback/', views.ai_caption_feedback_api, name='api_ai_assist_feedback'),
]
