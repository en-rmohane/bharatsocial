from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
import random
import urllib.parse
import requests
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail

from .models import CustomUser, Profile, Follow, Block, Report
from .forms import CustomUserCreationForm, ProfileEditForm
from .serializers import UserSerializer, ProfileSerializer

@api_view(['GET'])
def check_username_api(request):
    username = request.GET.get('username', '').strip().lower()
    if not username:
        return Response({"available": False, "error": "Username cannot be empty"})
    taken = CustomUser.objects.filter(username__iexact=username).exists()
    return Response({"available": not taken})

def send_signup_otp_email(email, first_name, otp):
    try:
        subject = 'Your BharatSocial Verification OTP (सत्यापन कोड)'
        message = (
            f"Hi {first_name},\n\n"
            f"Thank you for registering at BharatSocial!\n"
            f"Your 6-digit One-Time Password (OTP) for email verification is:\n"
            f"👉 {otp} 👈\n\n"
            f"This code will expire in 10 minutes.\n\n"
            f"Warm regards,\n"
            f"BharatSocial Team"
        )
        send_mail(
            subject,
            message,
            'ravikumarmohane@gmail.com',
            [email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"[send_signup_otp_email] Error: {e}")

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            signup_data = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password1']
            }
            
            otp = f"{random.randint(100000, 999999)}"
            request.session['signup_data'] = signup_data
            request.session['signup_otp'] = otp
            request.session['signup_otp_time'] = now().isoformat()
            
            send_signup_otp_email(signup_data['email'], signup_data['first_name'], otp)
            
            messages.success(request, "An OTP has been sent to your email address. (ओटीपी आपके ईमेल पते पर भेजा गया है।)")
            return redirect('signup_verify_otp')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    profile = get_object_or_404(Profile, user=profile_user)
    
    # Check if blocked
    is_blocked_by_me = Block.objects.filter(blocker=request.user, blocked=profile_user).exists()
    have_i_been_blocked = Block.objects.filter(blocker=profile_user, blocked=request.user).exists()
    
    if have_i_been_blocked:
        return render(request, 'accounts/blocked_profile.html', {'profile_user': profile_user})

    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
    
    # Get user's posts and reels
    user_posts = profile_user.posts.all().prefetch_related('media')
    user_reels = profile_user.reels.all()
    
    # Saved posts (only if current user is viewing their own profile)
    saved_posts = []
    if request.user == profile_user:
        saved_posts = [sp.post for sp in request.user.saved_posts.all().select_related('post')]
    
    context = {
        'profile_user': profile_user,
        'profile': profile,
        'is_following': is_following,
        'is_blocked_by_me': is_blocked_by_me,
        'posts': user_posts,
        'reels': user_reels,
        'saved_posts': saved_posts,
        'posts_count': user_posts.count(),
        'reels_count': user_reels.count(),
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Handle username change & privacy settings from request
            username = request.POST.get('username')
            is_private = request.POST.get('is_private') == 'on'
            
            user = request.user
            if username and username != user.username:
                if not CustomUser.objects.filter(username=username).exists():
                    user.username = username
                else:
                    messages.error(request, "Username already taken.")
            
            user.is_private = is_private
            user.save()
            
            messages.success(request, "Profile updated successfully.")
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileEditForm(instance=profile)
    return render(request, 'accounts/edit_profile.html', {'form': form})

# API for Follow / Unfollow
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_follow(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)
    if target_user == request.user:
        return Response({"error": "You cannot follow yourself."}, status=400)
    
    follow_relation = Follow.objects.filter(follower=request.user, following=target_user)
    if follow_relation.exists():
        follow_relation.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, following=target_user)
        is_following = True
        
        # Trigger Notification
        from notifications.models import Notification
        Notification.objects.create(
            recipient=target_user,
            sender=request.user,
            notification_type='follow'
        )
        
    return Response({
        "is_following": is_following,
        "followers_count": target_user.followers.count(),
        "following_count": target_user.following.count()
    })

# API for Block / Unblock
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_block(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)
    if target_user == request.user:
        return Response({"error": "You cannot block yourself."}, status=400)
        
    block_relation = Block.objects.filter(blocker=request.user, blocked=target_user)
    if block_relation.exists():
        block_relation.delete()
        is_blocked = False
    else:
        block_relation = Block.objects.create(blocker=request.user, blocked=target_user)
        # Unfollow when blocking
        Follow.objects.filter(follower=request.user, following=target_user).delete()
        Follow.objects.filter(follower=target_user, following=request.user).delete()
        is_blocked = True
        
    return Response({"is_blocked": is_blocked})

# API for Reporting
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_report(request):
    reason = request.data.get('reason')
    reported_user_id = request.data.get('user_id')
    reported_post_id = request.data.get('post_id')
    reported_reel_id = request.data.get('reel_id')
    
    if not reason:
        return Response({"error": "Reason is required."}, status=400)
        
    report = Report(reporter=request.user, reason=reason)
    if reported_user_id:
        report.reported_user_id = reported_user_id
    if reported_post_id:
        report.reported_post_id = reported_post_id
    if reported_reel_id:
        report.reported_reel_id = reported_reel_id
        
    report.save()
    return Response({"success": True, "message": "Thank you. Your report has been recorded."})

# Suggestions View API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_suggestions(request):
    # Get users I'm already following or blocking/blocked by
    following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    blocking_ids = Block.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked=request.user).values_list('blocker_id', flat=True)
    
    exclude_ids = list(following_ids) + list(blocking_ids) + list(blocked_by_ids) + [request.user.id]
    
    suggestions = CustomUser.objects.exclude(id__in=exclude_ids).select_related('profile')[:5]
    serializer = UserSerializer(suggestions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_followers(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    follows = Follow.objects.filter(following=profile_user).select_related('follower', 'follower__profile')
    
    follower_list = []
    for f in follows:
        follower_user = f.follower
        # Check if the logged-in user is following this follower
        is_following = Follow.objects.filter(follower=request.user, following=follower_user).exists()
        follower_list.append({
            "id": follower_user.id,
            "username": follower_user.username,
            "first_name": follower_user.first_name,
            "last_name": follower_user.last_name,
            "avatar": follower_user.profile.avatar.url if follower_user.profile.avatar else '/media/avatars/default.png',
            "is_following": is_following
        })
    return Response(follower_list)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_following(request, username):
    profile_user = get_object_or_404(CustomUser, username=username)
    follows = Follow.objects.filter(follower=profile_user).select_related('following', 'following__profile')
    
    following_list = []
    for f in follows:
        following_user = f.following
        # Check if the logged-in user is following this following_user
        is_following = Follow.objects.filter(follower=request.user, following=following_user).exists()
        following_list.append({
            "id": following_user.id,
            "username": following_user.username,
            "first_name": following_user.first_name,
            "last_name": following_user.last_name,
            "avatar": following_user.profile.avatar.url if following_user.profile.avatar else '/media/avatars/default.png',
            "is_following": is_following
        })
    return Response(following_list)

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def moderator_dashboard_view(request):
    # Fetch metrics
    total_users = CustomUser.objects.count()
    from posts.models import Post
    from reels.models import Reel
    total_posts = Post.objects.count()
    total_reels = Reel.objects.count()
    total_reports = Report.objects.count()

    reports = Report.objects.filter(status='pending').order_by('-created_at').select_related(
        'reporter', 'reported_user', 'reported_post', 'reported_reel'
    )
    users = CustomUser.objects.all().order_by('-date_joined')

    context = {
        'total_users': total_users,
        'total_posts': total_posts,
        'total_reels': total_reels,
        'total_reports': total_reports,
        'reports': reports,
        'users': users,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def moderator_action_api(request, report_id):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    report = get_object_or_404(Report, id=report_id)
    action = request.data.get('action') # 'resolve', 'ignore', 'delete_post', 'suspend_user'
    
    if action == 'resolve':
        report.status = 'resolved'
        report.save()
    elif action == 'ignore':
        report.status = 'ignored'
        report.save()
    elif action == 'delete_post':
        if report.reported_post:
            report.reported_post.delete()
        elif report.reported_reel:
            report.reported_reel.delete()
        report.status = 'resolved'
        report.save()
    elif action == 'suspend_user':
        target_user = report.reported_user
        if not target_user and report.reported_post:
            target_user = report.reported_post.author
        elif not target_user and report.reported_reel:
            target_user = report.reported_reel.author
            
        if target_user and not target_user.is_staff:
            target_user.is_active = False
            target_user.save()
        report.status = 'resolved'
        report.save()
        
    return Response({"success": True})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def moderator_toggle_user_status(request, user_id):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    user = get_object_or_404(CustomUser, id=user_id)
    if user.is_staff:
        return Response({"error": "Cannot suspend staff members"}, status=400)
        
    user.is_active = not user.is_active
    user.save()
    return Response({"success": True, "is_active": user.is_active})

def signup_verify_otp_view(request):
    signup_data = request.session.get('signup_data')
    signup_otp = request.session.get('signup_otp')
    otp_time_str = request.session.get('signup_otp_time')
    
    if not signup_data or not signup_otp or not otp_time_str:
        messages.error(request, "No signup session found. Please register first.")
        return redirect('signup')
        
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        
        # Check expiry (10 minutes)
        import datetime
        otp_time = now().fromisoformat(otp_time_str)
        if now() - otp_time > datetime.timedelta(minutes=10):
            messages.error(request, "OTP has expired. Please request a new code.")
            return render(request, 'accounts/signup_verify_otp.html')
            
        if entered_otp == signup_otp:
            try:
                # Double-check username uniqueness in DB
                if CustomUser.objects.filter(username__iexact=signup_data['username']).exists():
                    messages.error(request, "This username has been taken. Please choose another username.")
                    return redirect('signup')
                    
                user = CustomUser.objects.create_user(
                    username=signup_data['username'],
                    email=signup_data['email'],
                    password=signup_data['password']
                )
                user.first_name = signup_data['first_name']
                user.last_name = signup_data['last_name']
                user.email_verified = True
                user.save()
                
                login(request, user)
                
                # Clear session
                request.session.pop('signup_data', None)
                request.session.pop('signup_otp', None)
                request.session.pop('signup_otp_time', None)
                
                messages.success(request, "Registration successful! Welcome to BharatSocial.")
                return redirect('feed')
            except Exception as e:
                messages.error(request, f"Error creating profile: {e}")
                return render(request, 'accounts/signup_verify_otp.html')
        else:
            messages.error(request, "Invalid OTP. Please enter the correct 6-digit code. (अमान्य ओटीपी। कृपया सही 6 अंकों का कोड दर्ज करें।)")
            
    return render(request, 'accounts/signup_verify_otp.html')

@api_view(['POST'])
def resend_signup_otp_api(request):
    signup_data = request.session.get('signup_data')
    if not signup_data:
        return Response({"error": "No registration data found. Please sign up again."}, status=400)
        
    otp = f"{random.randint(100000, 999999)}"
    request.session['signup_otp'] = otp
    request.session['signup_otp_time'] = now().isoformat()
    
    send_signup_otp_email(signup_data['email'], signup_data['first_name'], otp)
    return Response({"success": True, "message": "Verification code resent."})

def google_login_view(request):
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', 'MOCK_CLIENT_ID')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', 'MOCK_CLIENT_SECRET')
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    
    if client_id == 'MOCK_CLIENT_ID' or client_secret == 'MOCK_CLIENT_SECRET':
        # Bypass for local dev / mock login
        return redirect(f"{redirect_uri}?code=mock_dev_google_code")
        
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'email profile openid',
        'prompt': 'select_account'
    }
    url = f"{google_auth_url}?{urllib.parse.urlencode(params)}"
    return redirect(url)

def google_callback_view(request):
    code = request.GET.get('code')
    if not code:
        messages.error(request, "Authorization code not provided by Google.")
        return redirect('login')
        
    email = None
    first_name = ""
    last_name = ""
    
    if code == 'mock_dev_google_code':
        email = "google_test_user@gmail.com"
        first_name = "Google"
        last_name = "User"
    else:
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', 'MOCK_CLIENT_ID')
        client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', 'MOCK_CLIENT_SECRET')
        redirect_uri = request.build_absolute_uri(reverse('google_callback'))
        
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        try:
            token_response = requests.post(token_url, data=token_data).json()
            access_token = token_response.get('access_token')
            if not access_token:
                messages.error(request, "Failed to retrieve access token from Google.")
                return redirect('login')
                
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info = requests.get(userinfo_url, headers=headers).json()
            
            email = user_info.get('email')
            first_name = user_info.get('given_name', '')
            last_name = user_info.get('family_name', '')
        except Exception as e:
            messages.error(request, f"Error communicating with Google: {e}")
            return redirect('login')
            
    if not email:
        messages.error(request, "Google login failed: email not retrieved.")
        return redirect('login')
        
    user = CustomUser.objects.filter(email__iexact=email).first()
    if not user:
        # Create user
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while CustomUser.objects.filter(username__iexact=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        import uuid
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=str(uuid.uuid4())
        )
        user.first_name = first_name
        user.last_name = last_name
        user.email_verified = True
        user.save()
        messages.success(request, f"Welcome to BharatSocial, {first_name}! Registered via Google.")
    else:
        if not user.email_verified:
            user.email_verified = True
            user.save()
        messages.success(request, f"Logged in successfully via Google as {user.username}!")
        
    login(request, user)
    return redirect('feed')

