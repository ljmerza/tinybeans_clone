"""Console SMS provider for development"""
import logging
from .base import BaseSMSProvider

logger = logging.getLogger(__name__)


class ConsoleSMSProvider(BaseSMSProvider):
    """Logs SMS messages instead of sending them"""

    def send_sms(self, phone_number: str, message: str) -> bool:
        logger.info("[ConsoleSMS] To %s: %s", phone_number, message)
        return True
