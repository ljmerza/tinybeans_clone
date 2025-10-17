"""SMS service"""
import logging

from django.conf import settings

from mysite import logging as project_logging
from mysite.audit import log_security_event

from .providers.base import BaseSMSProvider
from .providers.console import ConsoleSMSProvider
from .providers.twilio import TwilioProvider

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service with provider abstraction"""
    
    _provider = None
    
    @classmethod
    def get_provider(cls) -> BaseSMSProvider:
        """Get configured SMS provider"""
        if cls._provider is None:
            provider_name = getattr(settings, 'SMS_PROVIDER', 'console')
            
            if provider_name == 'twilio':
                cls._provider = TwilioProvider()
            elif provider_name == 'console':
                cls._provider = ConsoleSMSProvider()
            else:
                logger.error(
                    'Unknown SMS provider configured',
                    extra={'event': 'messaging.sms.provider_unknown', 'extra': {'provider': provider_name}},
                )
                raise ValueError(f"Unknown SMS provider: {provider_name}")

            with project_logging.log_context(sms_provider=provider_name):
                logger.info(
                    'SMS provider initialized',
                    extra={
                        'event': 'messaging.sms.provider_initialized',
                        'extra': {'provider': provider_name},
                    },
                )
        
        return cls._provider
    
    @classmethod
    def send_2fa_code(cls, phone_number: str, code: str) -> bool:
        """
        Send 2FA code via SMS
        
        Args:
            phone_number: E.164 format phone number
            code: 6-digit 2FA code
            
        Returns:
            bool: True if sent successfully
        """
        message = f"Your Tinybeans verification code is: {code}\n\nThis code expires in 10 minutes."
        phone_suffix = phone_number[-4:] if phone_number else None

        with project_logging.log_context(phone_last4=phone_suffix):
            try:
                provider = cls.get_provider()
            except Exception:  # noqa: BLE001 - log and re-raise result as failure
                logger.exception(
                    'Failed to resolve SMS provider for 2FA dispatch',
                    extra={'event': 'messaging.sms.provider_resolution_failed'},
                )
                log_security_event(
                    'twofa.sms.failure',
                    status='error',
                    severity='error',
                    metadata={'phone_last4': phone_suffix, 'reason': 'provider_resolution_failed'},
                )
                return False

            try:
                result = provider.send_sms(phone_number, message)
                if result:
                    logger.info(
                        '2FA SMS dispatched',
                        extra={
                            'event': 'messaging.sms.2fa_sent',
                            'extra': {
                                'provider': provider.__class__.__name__,
                                'phone_last4': phone_suffix,
                            },
                        },
                    )
                    log_security_event(
                        'twofa.sms.sent',
                        status='success',
                        severity='info',
                        metadata={
                            'provider': provider.__class__.__name__,
                            'phone_last4': phone_suffix,
                        },
                    )
                else:
                    logger.warning(
                        'SMS provider reported failure sending 2FA code',
                        extra={
                            'event': 'messaging.sms.2fa_provider_failure',
                            'extra': {
                                'provider': provider.__class__.__name__,
                                'phone_last4': phone_suffix,
                            },
                        },
                    )
                    log_security_event(
                        'twofa.sms.failure',
                        status='error',
                        severity='warning',
                        metadata={
                            'provider': provider.__class__.__name__,
                            'phone_last4': phone_suffix,
                            'reason': 'provider_false',
                        },
                    )
                return result
            except Exception:
                logger.exception(
                    'Failed to send 2FA SMS',
                    extra={
                        'event': 'messaging.sms.2fa_send_exception',
                        'extra': {
                            'provider': provider.__class__.__name__,
                            'phone_last4': phone_suffix,
                        },
                    },
                )
                log_security_event(
                    'twofa.sms.failure',
                    status='error',
                    severity='error',
                    metadata={
                        'provider': provider.__class__.__name__,
                        'phone_last4': phone_suffix,
                        'reason': 'exception',
                    },
                )
                return False
