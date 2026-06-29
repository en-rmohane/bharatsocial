from django.contrib import admin
from .models import Post, PostMedia, Hashtag, Comment, Like, SavePost, SavedCollection

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'caption_short', 'location', 'created_at']
    list_filter = ['created_at']
    search_fields = ['author__username', 'caption', 'location']
    inlines = [PostMediaInline]

    def caption_short(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_short.short_description = 'Caption'

@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'parent', 'content_short', 'created_at']
    list_filter = ['created_at']
    search_fields = ['author__username', 'content']

    def content_short(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Content'

admin.site.register(Like)
admin.site.register(SavePost)
admin.site.register(SavedCollection)
