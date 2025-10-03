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

# Use SQLite for tests (no PostgreSQL needed)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use in-memory cache for tests (instead of Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Configure Celery to run tasks synchronously in tests (no Redis needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

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

# Disable rate limiting and account lockouts during tests
RATELIMIT_ENABLE = False
TWOFA_RATE_LIMIT_WINDOW = 0
TWOFA_RATE_LIMIT_MAX = 0
# Force frontend base URL in tests to the expected value asserted by tests
ACCOUNT_FRONTEND_BASE_URL = 'http://localhost:3000'

TWOFA_LOCKOUT_THRESHOLD = 999999

# Ensure template metadata is available during tests
import emails.templates  # noqa: F401  (exposes EMAIL_TEMPLATE_FILES for loader)
