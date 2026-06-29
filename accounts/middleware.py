import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import F
from django.contrib import messages

logger = logging.getLogger(__name__)

class DailyLoginStreakMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Ensure the user has a profile
                profile = request.user.profile
                today = timezone.localdate()
                last_login = profile.last_login_date
                
                if last_login is None:
                    # First time daily login reward tracking
                    profile.login_streak = 1
                    profile.last_login_date = today
                    profile.points = F('points') + 5
                    profile.save()
                    profile.refresh_from_db()
                    try:
                        messages.success(request, f"Daily login reward! +5 points awarded. Current streak: 1 day.")
                    except Exception:
                        pass
                elif last_login == today:
                    # Already logged in today, do nothing
                    pass
                elif last_login == today - timedelta(days=1):
                    # Consecutive login!
                    profile.login_streak += 1
                    points_to_award = 5
                    milestone_msg = ""
                    
                    if profile.login_streak == 7:
                        points_to_award += 50
                        milestone_msg = " 🎉 7-Day Streak Bonus! +50 points!"
                    elif profile.login_streak == 30:
                        points_to_award += 500
                        milestone_msg = " 🎉 30-Day Streak Bonus! +500 points!"
                        
                    profile.last_login_date = today
                    profile.points = F('points') + points_to_award
                    profile.save()
                    profile.refresh_from_db()
                    
                    try:
                        messages.success(request, f"Daily login reward! +{points_to_award} points awarded.{milestone_msg} Current streak: {profile.login_streak} days.")
                    except Exception:
                        pass
                else:
                    # Streak broken (last login was more than 1 day ago)
                    profile.login_streak = 1
                    profile.last_login_date = today
                    profile.points = F('points') + 5
                    profile.save()
                    profile.refresh_from_db()
                    
                    try:
                        messages.info(request, f"Daily login reward! +5 points awarded. Your streak has been reset to 1 day.")
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Error in DailyLoginStreakMiddleware: {e}", exc_info=True)

        response = self.get_response(request)
        return response

from django.shortcuts import redirect
from django.urls import reverse

class EmailVerificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.email_verified:
            resolver_match = request.resolver_match
            if resolver_match:
                url_name = resolver_match.url_name
                if url_name in ['verify_email_prompt', 'verify_email', 'api_resend_verification_email', 'logout']:
                    return self.get_response(request)
            
            path = request.path
            if path.startswith('/static/') or path.startswith('/media/'):
                return self.get_response(request)
                
            return redirect('verify_email_prompt')

        response = self.get_response(request)
        return response
