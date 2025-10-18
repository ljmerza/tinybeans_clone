from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mysite.users'

    def ready(self) -> None:
        from . import signals  # noqa: F401
