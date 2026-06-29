from django.core.files.storage import Storage
from django.core.files.base import ContentFile
import base64
import os

class DatabaseStorage(Storage):
    def _open(self, name, mode='rb'):
        from posts.models import BlobFile
        # Normalize the name path separator for Windows / Linux cross-compatibility
        normalized_name = name.replace('\\', '/')
        try:
            blob = BlobFile.objects.get(name=normalized_name)
            return ContentFile(base64.b64decode(blob.content.encode('utf-8')))
        except BlobFile.DoesNotExist:
            # Fallback to local files if it is a pre-existing asset in the git repo
            from django.conf import settings
            local_path = os.path.join(settings.BASE_DIR, 'media', normalized_name)
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    return ContentFile(f.read())
            raise FileNotFoundError(f"File {normalized_name} not found.")

    def _save(self, name, content):
        from posts.models import BlobFile
        from PIL import Image
        import io

        normalized_name = name.replace('\\', '/')
        content_bytes = content.read()

        # Try to compress if it is an image
        ext = os.path.splitext(normalized_name.lower())[1]
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            try:
                img = Image.open(io.BytesIO(content_bytes))
                
                # Convert RGBA/transparent to RGB with white background
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to Instagram standard 1080px max bounds while keeping ratio
                img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
                
                # Save as compressed JPEG
                out_io = io.BytesIO()
                img.save(out_io, format='JPEG', quality=70, optimize=True)
                content_bytes = out_io.getvalue()
                
                # Update filename extension to .jpg for correctly guessed content-type
                if ext != '.jpg':
                    normalized_name = os.path.splitext(normalized_name)[0] + '.jpg'
            except Exception as e:
                print(f"Image compression failed, saving original: {e}")

        # Convert to base64
        base64_str = base64.b64encode(content_bytes).decode('utf-8')
        
        # Save or update in database
        BlobFile.objects.update_or_create(
            name=normalized_name,
            defaults={'content': base64_str}
        )
        return normalized_name

    def exists(self, name):
        from posts.models import BlobFile
        from django.conf import settings
        normalized_name = name.replace('\\', '/')
        
        # Check database first
        if BlobFile.objects.filter(name=normalized_name).exists():
            return True
            
        # Check local git files next
        local_path = os.path.join(settings.BASE_DIR, 'media', normalized_name)
        return os.path.exists(local_path)

    def url(self, name):
        normalized_name = name.replace('\\', '/')
        return f"/media/{normalized_name}"

    def get_available_name(self, name, max_length=None):
        return name.replace('\\', '/')
