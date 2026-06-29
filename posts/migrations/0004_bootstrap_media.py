from django.db import migrations
import os
import base64

def bootstrap_media_files(apps, schema_editor):
    BlobFile = apps.get_model('posts', 'BlobFile')
    from django.conf import settings
    
    media_dir = os.path.join(settings.BASE_DIR, 'media')
    if not os.path.exists(media_dir):
        return
        
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, media_dir).replace('\\', '/')
            
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
                
            base64_str = base64.b64encode(content_bytes).decode('utf-8')
            
            BlobFile.objects.update_or_create(
                name=rel_path,
                defaults={'content': base64_str}
            )

def rollback_media_files(apps, schema_editor):
    BlobFile = apps.get_model('posts', 'BlobFile')
    BlobFile.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0003_blobfile'),
    ]

    operations = [
        migrations.RunPython(bootstrap_media_files, rollback_media_files),
    ]
