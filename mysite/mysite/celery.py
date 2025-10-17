import os

from celery import Celery

from mysite.logging import bind_celery_signals

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    env = os.environ.get('DJANGO_ENVIRONMENT', 'local').lower()
    settings_map = {
        'local': 'mysite.config.settings.local',
        'staging': 'mysite.config.settings.staging',
        'production': 'mysite.config.settings.production',
        'test': 'mysite.config.settings.test',
    }
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_map.get(env, 'mysite.config.settings.local'))

app = Celery('mysite')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
bind_celery_signals(app)


@app.task(bind=True)
def debug_task(self):
    # Handy no-op to confirm Celery wiring during development
    print(f'Request: {self.request!r}')
