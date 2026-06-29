from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return self.username

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png', blank=True)
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    points = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    login_streak = models.IntegerField(default=0)

    @property
    def followers_count(self):
        return Follow.objects.filter(following=self.user).count()

    @property
    def following_count(self):
        return Follow.objects.filter(follower=self.user).count()

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocking')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

class Report(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    )
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_submitted')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_received', null=True, blank=True)
    
    # Using content types or string refs to avoid import cycles
    reported_post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reported_reel = models.ForeignKey('reels.Reel', on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report {self.id} by {self.reporter.username} ({self.status})"

# Signals to automatically create profile
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        Profile.objects.get_or_create(user=instance)

# --- Gamified Points Rewards Signals ---

@receiver(post_save, sender='posts.Post')
@receiver(post_save, sender='reels.Reel')
def add_points_on_post_creation(sender, instance, created, **kwargs):
    if created and instance.author:
        Profile.objects.filter(user=instance.author).update(points=F('points') + 10)

@receiver(post_delete, sender='posts.Post')
@receiver(post_delete, sender='reels.Reel')
def deduct_points_on_post_deletion(sender, instance, **kwargs):
    if instance.author:
        Profile.objects.filter(user=instance.author).update(points=F('points') - 10)

@receiver(post_save, sender='posts.Comment')
@receiver(post_save, sender='reels.ReelComment')
def add_points_on_comment_creation(sender, instance, created, **kwargs):
    if created and instance.author:
        Profile.objects.filter(user=instance.author).update(points=F('points') + 5)

@receiver(post_delete, sender='posts.Comment')
@receiver(post_delete, sender='reels.ReelComment')
def deduct_points_on_comment_deletion(sender, instance, **kwargs):
    if instance.author:
        Profile.objects.filter(user=instance.author).update(points=F('points') - 5)

@receiver(post_save, sender='posts.Like')
@receiver(post_save, sender='reels.ReelLike')
def add_points_on_like_creation(sender, instance, created, **kwargs):
    if created and instance.user:
        Profile.objects.filter(user=instance.user).update(points=F('points') + 2)

@receiver(post_delete, sender='posts.Like')
@receiver(post_delete, sender='reels.ReelLike')
def deduct_points_on_like_deletion(sender, instance, **kwargs):
    if instance.user:
        Profile.objects.filter(user=instance.user).update(points=F('points') - 2)

@receiver(post_save, sender=Follow)
def add_points_on_follow_creation(sender, instance, created, **kwargs):
    if created and instance.follower:
        Profile.objects.filter(user=instance.follower).update(points=F('points') + 5)

@receiver(post_delete, sender=Follow)
def deduct_points_on_follow_deletion(sender, instance, **kwargs):
    if instance.follower:
        Profile.objects.filter(user=instance.follower).update(points=F('points') - 5)


