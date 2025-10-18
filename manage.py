#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        env = os.environ.get('DJANGO_ENVIRONMENT', 'local').lower()
        settings_map = {
            'local': 'mysite.config.settings.local',
            'staging': 'mysite.config.settings.staging',
            'production': 'mysite.config.settings.production',
            'test': 'mysite.config.settings.test',
        }
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_map.get(env, 'mysite.config.settings.local'))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
