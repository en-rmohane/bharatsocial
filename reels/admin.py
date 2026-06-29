from django.contrib import admin
from .models import Reel, ReelComment, ReelLike

@admin.register(Reel)
class ReelAdmin(admin.ModelAdmin):
    list_display = ['author', 'caption_short', 'created_at']
    search_fields = ['author__username', 'caption']
    list_filter = ['created_at']

    def caption_short(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_short.short_description = 'Caption'

admin.site.register(ReelComment)
admin.site.register(ReelLike)
