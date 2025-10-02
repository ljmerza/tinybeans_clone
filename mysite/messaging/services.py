"""SMS service"""
from django.conf import settings
from .providers.base import BaseSMSProvider
from .providers.twilio import TwilioProvider
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """SMS service with provider abstraction"""
    
    _provider = None
    
    @classmethod
    def get_provider(cls) -> BaseSMSProvider:
        """Get configured SMS provider"""
        if cls._provider is None:
            provider_name = getattr(settings, 'SMS_PROVIDER', 'twilio')
            
            if provider_name == 'twilio':
                cls._provider = TwilioProvider()
            else:
                raise ValueError(f"Unknown SMS provider: {provider_name}")
        
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
        
        try:
            provider = cls.get_provider()
            return provider.send_sms(phone_number, message)
        except Exception as e:
            logger.error(f"Failed to send 2FA code: {e}")
            return False
