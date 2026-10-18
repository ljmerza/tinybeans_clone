from django.apps import AppConfig


class AiConfig(AppConfig):
    """In-app AI: circle admins turn on milestone suggestions from the operator's model."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mysite.ai"
    verbose_name = "In-app AI"
