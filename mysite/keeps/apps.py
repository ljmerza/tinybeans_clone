from django.apps import AppConfig


class KeepsConfig(AppConfig):
    """Configuration for the keeps app.
    
    Handles family memories and moments within circles.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'keeps'
    verbose_name = 'Keeps (Family Memories)'
