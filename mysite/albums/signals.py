"""Album signal handlers."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from mysite.circles.models import Circle

from .models import BirthdayAlbum


@receiver(post_delete, sender=BirthdayAlbum)
def turn_birthday_album_off(sender, instance, **kwargs):
    """Deleting a circle's Birthdays album turns the setting off, so the sync doesn't make it again."""
    Circle.objects.filter(pk=instance.circle_id).update(birthday_album_enabled=False)
