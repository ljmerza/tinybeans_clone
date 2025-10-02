"""Twilio SMS provider implementation"""
from .base import BaseSMSProvider
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TwilioProvider(BaseSMSProvider):
    """Twilio SMS provider"""
    
    def __init__(self):
        try:
            from twilio.rest import Client
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_number = settings.TWILIO_PHONE_NUMBER
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via Twilio"""
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )
            logger.info(f"SMS sent successfully. SID: {message_obj.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {e}")
            return False
