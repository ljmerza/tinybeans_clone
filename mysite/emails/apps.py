from django.apps import AppConfig


class EmailingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emails'

    def ready(self):
        from .template_loader import load_email_templates

        load_email_templates()

        return super().ready()
