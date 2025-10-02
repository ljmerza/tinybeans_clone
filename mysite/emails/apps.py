from django.apps import AppConfig


class EmailingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emails'

    def ready(self):
        from . import templates  # noqa: F401 -- ensure templates register on startup

        return super().ready()
