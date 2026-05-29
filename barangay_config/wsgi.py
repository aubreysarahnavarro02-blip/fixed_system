"""
WSGI config for Barangay Official Attendance Registry.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barangay_config.settings')
application = get_wsgi_application()
