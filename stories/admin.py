from django.contrib import admin
from .models import Story, StoryView, StoryReaction

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ['author', 'created_at']
    list_filter = ['created_at']

admin.site.register(StoryView)
admin.site.register(StoryReaction)
