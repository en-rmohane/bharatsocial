import os
import django
from django.core.files import File
from django.utils import timezone
from datetime import timedelta
from PIL import Image
import io

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bharatsocial.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Profile, Follow, Block
from posts.models import Post, PostMedia, Comment, Like
from reels.models import Reel
from stories.models import Story
from chat.models import Message

User = get_user_model()

def generate_mock_image(color=(255, 48, 79), size=(400, 400)):
    img = Image.new('RGB', size, color=color)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    return img_byte_arr

def create_mock_file(name, color=(255, 48, 79)):
    os.makedirs('media/temp', exist_ok=True)
    path = os.path.join('media/temp', name)
    img_data = generate_mock_image(color)
    with open(path, 'wb') as f:
        f.write(img_data.read())
    return path

def seed_database():
    print("Seeding database...")
    
    # 1. Create Superuser / Admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@bharatsocial.com', 'admin123')
        admin.first_name = 'BharatSocial'
        admin.last_name = 'Admin'
        admin.save()
        print("Admin user created (User: admin, Pass: admin123)")
    else:
        admin = User.objects.get(username='admin')

    # 2. Create Test Users
    users_data = [
        {'username': 'raj', 'first': 'Raj', 'last': 'Sharma', 'color': (33, 150, 243)},
        {'username': 'priya', 'first': 'Priya', 'last': 'Patel', 'color': (233, 30, 99)},
        {'username': 'amit', 'first': 'Amit', 'last': 'Singh', 'color': (76, 175, 80)},
    ]
    
    users = {}
    for u in users_data:
        if not User.objects.filter(username=u['username']).exists():
            user = User.objects.create_user(u['username'], f"{u['username']}@example.com", 'testpass123')
            user.first_name = u['first']
            user.last_name = u['last']
            user.email_verified = True
            user.save()
            
            # Generate avatar
            avatar_path = create_mock_file(f"avatar_{u['username']}.jpg", u['color'])
            with open(avatar_path, 'rb') as f:
                user.profile.avatar.save(f"avatar_{u['username']}.jpg", File(f))
            user.profile.bio = f"Proud Indian 🇮🇳 | {u['first']}'s official space. Stay tuned!"
            user.profile.website = "https://bharatsocial.com"
            user.profile.save()
            print(f"User {u['username']} created (Pass: testpass123)")
        else:
            user = User.objects.get(username=u['username'])
        users[u['username']] = user

    # 3. Followings
    # Raj follows Priya & Amit
    Follow.objects.get_or_create(follower=users['raj'], following=users['priya'])
    Follow.objects.get_or_create(follower=users['raj'], following=users['amit'])
    # Priya follows Raj & Admin
    Follow.objects.get_or_create(follower=users['priya'], following=users['raj'])
    Follow.objects.get_or_create(follower=users['priya'], following=admin)
    print("Follows populated.")

    # 4. Posts
    # Raj post
    if not Post.objects.filter(author=users['raj']).exists():
        post_img1 = create_mock_file("post_raj_1.jpg", (33, 150, 243))
        post_img2 = create_mock_file("post_raj_2.jpg", (100, 100, 255))
        
        post = Post.objects.create(author=users['raj'], caption="Explored the beautiful sunset today! #nature #sunset #india", location="Mumbai, India")
        with open(post_img1, 'rb') as f:
            PostMedia.objects.create(post=post, file=File(f), order=0)
        with open(post_img2, 'rb') as f:
            PostMedia.objects.create(post=post, file=File(f), order=1)
            
        # Priya Likes and Comments
        Like.objects.create(user=users['priya'], post=post)
        Comment.objects.create(post=post, author=users['priya'], content="Incredible capture, Raj! 😍")
        print("Raj's post created.")

    # Priya post
    if not Post.objects.filter(author=users['priya']).exists():
        post_img = create_mock_file("post_priya.jpg", (233, 30, 99))
        post = Post.objects.create(author=users['priya'], caption="Chai time is the best time! ☕️ #chai #evening #india", location="Taj Mahal Palace, Mumbai")
        with open(post_img, 'rb') as f:
            PostMedia.objects.create(post=post, file=File(f), order=0)
        
        # Raj Likes and Comments
        Like.objects.create(user=users['raj'], post=post)
        Comment.objects.create(post=post, author=users['raj'], content="Indeed, nothing beats evening chai!")
        print("Priya's post created.")

    # 5. Reels
    # Create simple vertical format image and save it as reel file reference
    if not Reel.objects.filter(author=users['amit']).exists():
        reel_file_path = create_mock_file("reel_amit.jpg", (76, 175, 80))
        reel = Reel(author=users['amit'], caption="A walk in the green fields of Punjab 🌾 #reels #village #india")
        with open(reel_file_path, 'rb') as f:
            reel.video_file.save("reel_amit.mp4", File(f))
        reel.save()
        print("Amit's reel created.")

    # 6. Stories
    if not Story.objects.filter(author=users['priya']).exists():
        story_file_path = create_mock_file("story_priya.jpg", (255, 200, 200))
        story = Story(author=users['priya'])
        with open(story_file_path, 'rb') as f:
            story.media_file.save("story_priya.jpg", File(f))
        story.save()
        print("Priya's story created.")

    # 7. Messages
    # Priya to Raj
    Message.objects.get_or_create(
        sender=users['priya'],
        receiver=users['raj'],
        content="Hey Raj! Did you see the new update?",
        created_at=timezone.now() - timedelta(minutes=10)
    )
    Message.objects.get_or_create(
        sender=users['raj'],
        receiver=users['priya'],
        content="Yes Priya, just checked it out. Looks great!",
        created_at=timezone.now() - timedelta(minutes=5)
    )
    print("Messages seeded.")

    # Clean up temp files
    import shutil
    if os.path.exists('media/temp'):
        shutil.rmtree('media/temp')
    
    print("Seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
