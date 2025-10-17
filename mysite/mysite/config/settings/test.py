"""Test settings for running unit tests."""
import os

os.environ.setdefault('DJANGO_DEBUG', '0')
os.environ.setdefault('DJANGO_ENVIRONMENT', 'test')
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key')
os.environ.setdefault('TWOFA_ENCRYPTION_KEY', '5pK6Bm8rEICTnaRJvv0eQilwcmHeuTU1dRYrI-4VvEc=')
os.environ.setdefault('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:3000')
os.environ.setdefault('DJANGO_SECURE_SSL_REDIRECT', '0')

from .base import *  # noqa: F401,F403

from mysite.logging import get_logging_config

# Override email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

TEST_RUNNER = 'mysite.test_runner.ProjectDiscoverRunner'

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
LOGGING = get_logging_config(
    environment='test',
    log_level='WARNING',
    enable_console=False,
    enable_audit_console=False,
)

# Disable rate limiting and account lockouts during tests
RATELIMIT_ENABLE = False
TWOFA_RATE_LIMIT_WINDOW = 0
TWOFA_RATE_LIMIT_MAX = 0
# Force frontend base URL in tests to the expected value asserted by tests
ACCOUNT_FRONTEND_BASE_URL = 'http://localhost:3000'

TWOFA_LOCKOUT_THRESHOLD = 999999

# Google OAuth test settings
GOOGLE_OAUTH_CLIENT_ID = 'test-client-id.apps.googleusercontent.com'
GOOGLE_OAUTH_CLIENT_SECRET = 'test-client-secret'
GOOGLE_OAUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
OAUTH_ALLOWED_REDIRECT_URIS = [
    'http://localhost:3000/auth/google/callback',
    'http://localhost:3000/settings/account/google/callback',
]
OAUTH_STATE_EXPIRATION = 600  # 10 minutes in seconds

# Ensure template metadata is available during tests
import emails.templates  # noqa: F401  (exposes EMAIL_TEMPLATE_FILES for loader)
