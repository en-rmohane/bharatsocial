"""
WSGI config for bharatsocial project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bharatsocial.settings')

import django
django.setup()

# Run migrations automatically on server startup
try:
    from django.core.management import call_command
    print("Running database migrations...")
    call_command('migrate', interactive=False)
except Exception as e:
    print(f"Error running database migrations: {e}")

application = get_wsgi_application()
app = application
