from django.apps import AppConfig


class AlbumsConfig(AppConfig):
    """Albums: named collections of a circle's keeps, e.g. "Beach trip 2026"."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mysite.albums"
    verbose_name = "Albums"
