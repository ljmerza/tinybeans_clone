"""
Test settings for running tests with proper email stubbing and overrides.
"""

from .settings import *

# Override email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable Mailjet by default in tests
MAILJET_ENABLED = False
MAILJET_API_KEY = None
MAILJET_API_SECRET = None

# Use in-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Use faster password hashers for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests to reduce noise
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
        },
        'emailing': {
            'handlers': ['null'],
            'propagate': False,
        },
        'users': {
            'handlers': ['null'],
            'propagate': False,
        },
    }
}

# Ensure templates are loaded for tests
# This forces Django to import the emailing templates module
import emailing.templates.users  # This will register the email templates