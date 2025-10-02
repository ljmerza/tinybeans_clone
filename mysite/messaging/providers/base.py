"""Base SMS provider interface"""
from abc import ABC, abstractmethod


class BaseSMSProvider(ABC):
    """Abstract base class for SMS providers"""
    
    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Send SMS to phone number
        
        Args:
            phone_number: E.164 format phone number (e.g., +1234567890)
            message: Message content
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        pass
