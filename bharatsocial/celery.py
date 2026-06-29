import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bharatsocial.settings')

app = Celery('bharatsocial')

# Configure Celery using settings.py values with namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks from all registered Django apps
app.autodiscover_tasks()
