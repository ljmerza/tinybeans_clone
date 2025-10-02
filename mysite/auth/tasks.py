"""Celery tasks for auth"""
from celery import shared_task
from .services.trusted_device_service import TrustedDeviceService


@shared_task
def cleanup_expired_trusted_devices():
    """
    Scheduled task to clean up expired trusted devices
    Run daily via celery beat
    """
    expired_count = TrustedDeviceService.cleanup_expired_devices()
    return f"Cleaned up {expired_count} expired trusted devices"
