"""Security settings: CORS, CSRF, SSL/HTTPS, and cookies"""
import os
from django.core.exceptions import ImproperlyConfigured


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name: str, default=None):
    value = os.environ.get(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


# Development frontend origins
_DEV_FRONTEND_ORIGINS = [
    "http://localhost:3053",
    "http://127.0.0.1:3053",
    "http://localhost:3053",
]


def _get_cors_config(debug: bool) -> dict:
    """Get CORS configuration based on DEBUG setting"""
    _default_cors_origins = _DEV_FRONTEND_ORIGINS if debug else []
    cors_allowed_origins = _env_list('CORS_ALLOWED_ORIGINS', default=_default_cors_origins)

    config = {
        'CORS_ALLOWED_ORIGINS': cors_allowed_origins,
    }

    if cors_allowed_origins:
        config['CORS_ALLOW_CREDENTIALS'] = _env_flag('CORS_ALLOW_CREDENTIALS', default=True)
        config['CORS_ALLOW_HEADERS'] = [
            'accept',
            'accept-encoding',
            'authorization',
            'content-type',
            'dnt',
            'origin',
            'user-agent',
            'x-csrftoken',
            'x-requested-with',
        ]
    else:
        config['CORS_ALLOW_CREDENTIALS'] = False

    return config


# This will be set by base.py after DEBUG is available
# CORS_ALLOWED_ORIGINS = ...
# CORS_ALLOW_CREDENTIALS = ...
# CORS_ALLOW_HEADERS = ...


def _get_csrf_config(debug: bool):
    """Get CSRF configuration based on DEBUG setting"""
    _default_csrf_origins = _DEV_FRONTEND_ORIGINS if debug else None
    csrf_trusted_origins = _env_list('DJANGO_CSRF_TRUSTED_ORIGINS', default=_default_csrf_origins)

    if not debug and not csrf_trusted_origins:
        raise ImproperlyConfigured('DJANGO_CSRF_TRUSTED_ORIGINS must be set when DEBUG is False')

    return {
        'CSRF_TRUSTED_ORIGINS': csrf_trusted_origins,
        'CSRF_COOKIE_SECURE': _env_flag('DJANGO_CSRF_COOKIE_SECURE', default=not debug),
        'CSRF_COOKIE_HTTPONLY': _env_flag('DJANGO_CSRF_COOKIE_HTTPONLY', default=False),
        'CSRF_COOKIE_SAMESITE': os.environ.get('DJANGO_CSRF_COOKIE_SAMESITE', 'Strict'),
    }


# HTTPS & SSL Configuration
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True


def _get_ssl_redirect(debug: bool) -> bool:
    return _env_flag('DJANGO_SECURE_SSL_REDIRECT', default=not debug)

# This will be set by base.py after DEBUG is available
# SECURE_SSL_REDIRECT = _get_ssl_redirect(DEBUG)


def _get_hsts_config(debug: bool) -> dict:
    """Get HSTS configuration based on DEBUG setting"""
    if debug:
        return {
            'SECURE_HSTS_SECONDS': 0,
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': False,
            'SECURE_HSTS_PRELOAD': False,
        }
    else:
        return {
            'SECURE_HSTS_SECONDS': int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000')),
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': _env_flag('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True),
            'SECURE_HSTS_PRELOAD': _env_flag('DJANGO_SECURE_HSTS_PRELOAD', default=True),
        }


# This will be set by base.py after DEBUG is available
# SECURE_HSTS_SECONDS = ...
# SECURE_HSTS_INCLUDE_SUBDOMAINS = ...
# SECURE_HSTS_PRELOAD = ...


# Other Security Headers
SECURE_REFERRER_POLICY = os.environ.get('DJANGO_SECURE_REFERRER_POLICY', 'same-origin')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = os.environ.get('DJANGO_SECURE_COOP', 'same-origin')


# Session Cookie Configuration
def _get_session_cookie_config(debug: bool) -> dict:
    return {
        'SESSION_COOKIE_SECURE': _env_flag('DJANGO_SESSION_COOKIE_SECURE', default=not debug),
        'SESSION_COOKIE_SAMESITE': os.environ.get('DJANGO_SESSION_COOKIE_SAMESITE', 'Lax'),
    }


# This will be set by base.py after DEBUG is available
# SESSION_COOKIE_SECURE = ...
# SESSION_COOKIE_SAMESITE = ...
