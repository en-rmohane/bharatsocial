from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile, Follow, Block, Report

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'email_verified', 'is_private', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('email_verified', 'is_private')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'email_verified', 'is_private')}),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'website', 'followers_count', 'following_count']
    search_fields = ['user__username', 'bio', 'website']

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at']
    list_filter = ['created_at']

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ['blocker', 'blocked', 'created_at']

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['reporter', 'reported_user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['reporter__username', 'reason']

admin.site.register(CustomUser, CustomUserAdmin)
