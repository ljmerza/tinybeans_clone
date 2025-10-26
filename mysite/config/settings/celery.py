"""Celery configuration for async task processing"""
import os
from celery.schedules import crontab
from kombu import Queue


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


# Celery Broker and Backend
# Will use REDIS_URL from cache.py
def _get_celery_broker_url(redis_url: str) -> str:
    return os.environ.get('CELERY_BROKER_URL', redis_url)

def _get_celery_result_backend(redis_url: str) -> str:
    return os.environ.get('CELERY_RESULT_BACKEND', redis_url)

# These will be set by base.py after REDIS_URL is available
# CELERY_BROKER_URL = _get_celery_broker_url(REDIS_URL)
# CELERY_RESULT_BACKEND = _get_celery_result_backend(REDIS_URL)

# Celery Task Serialization
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Celery Timezone (will use TIME_ZONE from base settings)
# CELERY_TIMEZONE = TIME_ZONE

# Celery Queues
CELERY_TASK_DEFAULT_QUEUE = 'maintenance'
CELERY_TASK_QUEUES = (
    Queue('email'),
    Queue('sms'),
    Queue('media'),
    Queue('maintenance'),
)

# Task Routing
CELERY_TASK_ROUTES = {
    'mysite.emails.tasks.send_email_task': {'queue': 'email'},
    'mysite.messaging.tasks.send_sms_async': {'queue': 'sms'},
    'mysite.messaging.tasks.send_2fa_sms': {'queue': 'sms'},
    'mysite.keeps.tasks.process_media_upload': {'queue': 'media'},
    'mysite.keeps.tasks.generate_image_sizes': {'queue': 'media'},
    'mysite.keeps.tasks.cleanup_failed_uploads': {'queue': 'media'},
    'mysite.keeps.tasks.validate_media_file': {'queue': 'media'},
    'mysite.auth.tasks.cleanup_expired_trusted_devices': {'queue': 'maintenance'},
    'mysite.auth.tasks.cleanup_expired_oauth_states': {'queue': 'maintenance'},
    'mysite.auth.tasks.cleanup_expired_magic_login_tokens': {'queue': 'maintenance'},
    'mysite.celery.debug_task': {'queue': 'maintenance'},
}

# Worker Configuration
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ALWAYS_EAGER = _env_flag('CELERY_TASK_ALWAYS_EAGER')
CELERY_TASK_EAGER_PROPAGATES = _env_flag('CELERY_TASK_EAGER_PROPAGATES', default=True)
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get('CELERY_TASK_SOFT_TIME_LIMIT', 30))
CELERY_TASK_TIME_LIMIT = int(os.environ.get('CELERY_TASK_TIME_LIMIT', 40))

# Celery Beat Schedule (Periodic Tasks)
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-oauth-states': {
        'task': 'mysite.auth.tasks.cleanup_expired_oauth_states',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-expired-trusted-devices': {
        'task': 'mysite.auth.tasks.cleanup_expired_trusted_devices',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'cleanup-expired-magic-login-tokens': {
        'task': 'mysite.auth.tasks.cleanup_expired_magic_login_tokens',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'send-circle-invitation-reminders': {
        'task': 'mysite.circles.tasks.send_circle_invitation_reminders',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}
