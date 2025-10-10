"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    env = os.environ.get('DJANGO_ENVIRONMENT', 'local').lower()
    settings_map = {
        'local': 'mysite.config.settings.local',
        'staging': 'mysite.config.settings.staging',
        'production': 'mysite.config.settings.production',
        'test': 'mysite.config.settings.test',
    }
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_map.get(env, 'mysite.config.settings.local'))

application = get_asgi_application()
