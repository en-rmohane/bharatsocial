"""
URL configuration for bharatsocial project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.static import serve
import base64
import mimetypes
import os

def serve_media_custom(request, path):
    normalized_path = path.replace('\\', '/')
    
    # Try database storage first
    from posts.models import BlobFile
    try:
        blob = BlobFile.objects.get(name=normalized_path)
        content_bytes = base64.b64decode(blob.content.encode('utf-8'))
        content_type, _ = mimetypes.guess_type(normalized_path)
        return HttpResponse(content_bytes, content_type=content_type or 'application/octet-stream')
    except BlobFile.DoesNotExist:
        pass
        
    # Try local project media next
    local_dir = os.path.join(settings.BASE_DIR, 'media')
    local_file_path = os.path.join(local_dir, normalized_path)
    if os.path.exists(local_file_path):
        return serve(request, normalized_path, document_root=local_dir)
        
    raise Http404("Media file not found")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('media/<path:path>', serve_media_custom, name='serve_media_custom'),
    path('', include('accounts.urls')),
    path('', include('posts.urls')),
    path('', include('reels.urls')),
    path('', include('stories.urls')),
    path('', include('chat.urls')),
    path('', include('notifications.urls')),
    path('api/recommendation/', include('recommendation.urls')),
]

