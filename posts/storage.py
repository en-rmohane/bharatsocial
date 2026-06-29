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
        normalized_name = name.replace('\\', '/')
        # Read the content and convert to base64
        content_bytes = content.read()
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
