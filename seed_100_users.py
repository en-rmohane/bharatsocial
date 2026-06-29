import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bharatsocial.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Profile, Follow

User = get_user_model()

def create_users_and_follows():
    print("Creating 100 users...")
    created_users = []
    
    # Create 100 users
    for i in range(1, 101):
        username = f"user_{i}"
        email = f"{username}@bharatsocial.com"
        password = "testpass123"
        
        user, created = User.objects.get_or_create(username=username, email=email)
        if created:
            user.set_password(password)
            user.first_name = f"User"
            user.last_name = f"Number {i}"
            user.save()
            
            # Update profile details
            profile = user.profile
            profile.bio = f"I am User {i} on BharatSocial! Proud Indian 🇮🇳."
            profile.website = f"https://bharatsocial.com/user_{i}"
            profile.save()
            
        created_users.append(user)
    
    print("Successfully ensured 100 users exist.")
    
    # Get all users (including existing ones like raj, priya, amit, admin) to inter-follow
    all_users = list(User.objects.all())
    print(f"Total users in DB: {len(all_users)}")
    
    print("Establishing mutual follow relationships...")
    
    existing_follows = set(
        Follow.objects.values_list('follower_id', 'following_id')
    )
    
    new_follows = []
    for follower in all_users:
        for following in all_users:
            if follower != following:
                if (follower.id, following.id) not in existing_follows:
                    new_follows.append(Follow(follower=follower, following=following))
                    
    if new_follows:
        Follow.objects.bulk_create(new_follows, ignore_conflicts=True)
        print(f"Created {len(new_follows)} follow relations.")
    else:
        print("All follow relations already exist.")
        
    print("Database seeding of 100 users completed successfully!")

if __name__ == '__main__':
    create_users_and_follows()
