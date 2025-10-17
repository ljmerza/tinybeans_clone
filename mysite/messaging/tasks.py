"""Celery tasks for SMS"""
import logging

from celery import shared_task

from mysite import logging as project_logging

from .services import SMSService

logger = logging.getLogger(__name__)


@shared_task(queue='sms')
def send_sms_async(phone_number: str, message: str):
    """
    Async task to send SMS
    
    Args:
        phone_number: E.164 format phone number
        message: Message content
        
    Returns:
        bool: True if sent successfully
    """
    phone_suffix = phone_number[-4:] if phone_number else None
    with project_logging.log_context(task='messaging.send_sms_async', phone_last4=phone_suffix):
        try:
            provider = SMSService.get_provider()
            result = provider.send_sms(phone_number, message)
            logger.info(
                'SMS dispatch attempted',
                extra={
                    'event': 'messaging.sms.send_async',
                    'extra': {
                        'provider': provider.__class__.__name__,
                        'phone_last4': phone_suffix,
                        'message_length': len(message or ''),
                        'result': bool(result),
                    },
                },
            )
            return result
        except Exception:
            logger.exception(
                'Failed to send SMS async',
                extra={
                    'event': 'messaging.sms.send_async_exception',
                    'extra': {'phone_last4': phone_suffix},
                },
            )
            return False


@shared_task(queue='sms')
def send_2fa_sms(phone_number: str, code: str):
    """
    Async task to send 2FA code via SMS
    
    Args:
        phone_number: E.164 format phone number
        code: 6-digit 2FA code
        
    Returns:
        bool: True if sent successfully
    """
    phone_suffix = phone_number[-4:] if phone_number else None
    with project_logging.log_context(task='messaging.send_2fa_sms', phone_last4=phone_suffix):
        result = SMSService.send_2fa_code(phone_number, code)
        logger.info(
            '2FA SMS task executed',
            extra={
                'event': 'messaging.sms.2fa_task',
                'extra': {'phone_last4': phone_suffix, 'result': bool(result)},
            },
        )
        return result
