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


@shared_task
def cleanup_expired_oauth_states():
    """
    Scheduled task to clean up expired OAuth state tokens.
    
    Runs every 15 minutes via Celery Beat to prevent database growth.
    Deletes OAuth state tokens older than 1 hour (including expired and used ones).
    
    Returns:
        str: Success message with count of deleted states
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import GoogleOAuthState
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Delete states older than 1 hour
    cutoff_time = timezone.now() - timedelta(hours=1)
    deleted_count, _ = GoogleOAuthState.objects.filter(
        created_at__lt=cutoff_time
    ).delete()
    
    logger.info(f"OAuth state cleanup: deleted {deleted_count} expired states")
    
    # Alert if there are too many expired states (indicates cleanup lag)
    remaining_expired = GoogleOAuthState.objects.filter(
        expires_at__lt=timezone.now()
    ).count()
    
    if remaining_expired > 10000:
        logger.warning(
            f"OAuth state cleanup lag detected: {remaining_expired} expired states remaining"
        )
    
    return f"Cleaned up {deleted_count} expired OAuth states"

