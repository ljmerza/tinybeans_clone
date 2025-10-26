"""Cache and Redis configuration"""
import os


# Redis Configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

# Django Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

# Session Storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
