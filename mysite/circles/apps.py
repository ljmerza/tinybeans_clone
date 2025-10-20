from django.apps import AppConfig


class CirclesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mysite.circles'
    verbose_name = 'Circles'

    def ready(self):
        # Signals will be wired up once circle logic migrates to this app.
        from . import signals  # noqa: F401

