"""Django REST Framework configuration"""
import os


# DRF Throttle Rates
DRF_USER_THROTTLE_RATE = os.environ.get('DRF_USER_THROTTLE_RATE', '1000/hour')
DRF_ANON_THROTTLE_RATE = os.environ.get('DRF_ANON_THROTTLE_RATE', '100/hour')


def _get_rest_framework_config(debug: bool) -> dict:
    """Get REST Framework configuration with debug-dependent renderers"""
    config = {
        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticated',
            'mysite.auth.permissions.IsEmailVerified',
        ),
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ),
        'DEFAULT_RENDERER_CLASSES': [
            'rest_framework.renderers.JSONRenderer',
        ],
        'DEFAULT_THROTTLE_CLASSES': (
            'rest_framework.throttling.UserRateThrottle',
            'rest_framework.throttling.AnonRateThrottle',
        ),
        'DEFAULT_THROTTLE_RATES': {
            'user': DRF_USER_THROTTLE_RATE,
            'anon': DRF_ANON_THROTTLE_RATE,
        },
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
        'EXCEPTION_HANDLER': 'mysite.exception_handlers.custom_exception_handler',
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
        'PAGE_SIZE': int(os.environ.get('DRF_PAGE_SIZE', 50)),
    }

    if debug:
        config['DEFAULT_RENDERER_CLASSES'].append(
            'rest_framework.renderers.BrowsableAPIRenderer'
        )

    return config


# This will be set by base.py after DEBUG is available
# REST_FRAMEWORK = _get_rest_framework_config(DEBUG)


# drf-spectacular (OpenAPI schema) configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Circle Sharing API',
    'DESCRIPTION': 'OpenAPI schema for circle management, invitations, and media sharing.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}
