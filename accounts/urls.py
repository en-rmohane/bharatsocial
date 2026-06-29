from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password actions
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

    # Profile views
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    
    # API endpoints
    path('api/follow/<int:user_id>/', views.toggle_follow, name='api_toggle_follow'),
    path('api/block/<int:user_id>/', views.toggle_block, name='api_toggle_block'),
    path('api/report/', views.submit_report, name='api_submit_report'),
    path('api/suggestions/', views.get_user_suggestions, name='api_user_suggestions'),
    path('api/profile/<str:username>/followers/', views.get_user_followers, name='api_user_followers'),
    path('api/profile/<str:username>/following/', views.get_user_following, name='api_user_following'),

    # OTP & Google Verification routes
    path('api/check-username/', views.check_username_api, name='api_check_username'),
    path('signup/verify-otp/', views.signup_verify_otp_view, name='signup_verify_otp'),
    path('api/signup/resend-otp/', views.resend_signup_otp_api, name='api_resend_signup_otp'),
    path('google/login/', views.google_login_view, name='google_login'),
    path('google/callback/', views.google_callback_view, name='google_callback'),

    # Moderator routes
    path('moderator/dashboard/', views.moderator_dashboard_view, name='moderator_dashboard'),
    path('api/moderator/reports/<int:report_id>/', views.moderator_action_api, name='api_moderator_action'),
    path('api/moderator/users/<int:user_id>/toggle/', views.moderator_toggle_user_status, name='api_moderator_toggle_user'),
]
