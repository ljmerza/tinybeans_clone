"""Celery tasks for SMS"""
from celery import shared_task
from .services import SMSService
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_sms_async(phone_number: str, message: str):
    """
    Async task to send SMS
    
    Args:
        phone_number: E.164 format phone number
        message: Message content
        
    Returns:
        bool: True if sent successfully
    """
    try:
        provider = SMSService.get_provider()
        result = provider.send_sms(phone_number, message)
        return result
    except Exception as e:
        logger.error(f"Failed to send SMS async: {e}")
        return False


@shared_task
def send_2fa_sms(phone_number: str, code: str):
    """
    Async task to send 2FA code via SMS
    
    Args:
        phone_number: E.164 format phone number
        code: 6-digit 2FA code
        
    Returns:
        bool: True if sent successfully
    """
    return SMSService.send_2fa_code(phone_number, code)
