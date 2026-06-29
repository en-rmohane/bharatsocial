from django.urls import path
from . import views

urlpatterns = [
    # Rendered pages
    path('reels/', views.reels_feed_view, name='reels_feed'),
    path('reels/create/', views.create_reel_view, name='create_reel'),
    
    # API endpoints
    path('api/reels/', views.reels_list_api, name='api_reels_list'),
    path('api/reels/<int:reel_id>/like/', views.toggle_like_reel, name='api_toggle_like_reel'),
    path('api/reels/<int:reel_id>/comments/', views.reel_comments_api, name='api_reel_comments'),
    path('api/reels/<int:reel_id>/delete/', views.delete_reel, name='api_delete_reel'),
]
