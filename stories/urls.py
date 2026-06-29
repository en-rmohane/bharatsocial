from django.urls import path
from . import views

urlpatterns = [
    path('api/stories/', views.stories_list_create_api, name='api_stories_list_create'),
    path('api/stories/<int:story_id>/view/', views.mark_story_viewed, name='api_mark_story_viewed'),
    path('api/stories/<int:story_id>/react/', views.react_to_story, name='api_react_to_story'),
]
