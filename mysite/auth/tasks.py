"""Celery tasks for auth"""
from celery import shared_task
from django.db import models
from .services.trusted_device_service import TrustedDeviceService


@shared_task
def cleanup_expired_trusted_devices():
    """
    Scheduled task to clean up expired trusted devices
    Run daily via celery beat
    """
    expired_count = TrustedDeviceService.cleanup_expired_devices()
    return f"Cleaned up {expired_count} expired trusted devices"


@shared_task
def cleanup_expired_magic_login_tokens():
    """
    Scheduled task to clean up expired and used magic login tokens
    Run daily via celery beat
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import MagicLoginToken
    
    # Delete expired or used tokens older than 7 days
    cutoff_date = timezone.now() - timedelta(days=7)
    deleted_count, _ = MagicLoginToken.objects.filter(
        created_at__lt=cutoff_date
    ).filter(
        models.Q(is_used=True) | models.Q(expires_at__lt=timezone.now())
    ).delete()
    
    return f"Cleaned up {deleted_count} expired/used magic login tokens"


