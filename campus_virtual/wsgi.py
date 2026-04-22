"""
WSGI config for Campus Virtual project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_virtual.settings')

application = get_wsgi_application()