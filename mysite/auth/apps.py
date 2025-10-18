from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mysite.auth'
    label = 'auth_app'  # Use a different label to avoid conflict with django.contrib.auth
