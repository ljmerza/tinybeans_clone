"""Tests for SMS messaging services."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.conf import settings
from django.test import override_settings
from messaging.services import SMSService
from messaging.providers.console import ConsoleSMSProvider
from messaging.providers.twilio import TwilioProvider


@pytest.mark.django_db
class TestSMSService:
    """Test SMSService class."""
    
    def test_get_console_provider(self):
        """Test getting console provider."""
        with override_settings(SMS_PROVIDER='console'):
            # Reset provider
            SMSService._provider = None
            provider = SMSService.get_provider()
            assert isinstance(provider, ConsoleSMSProvider)
    
    def test_get_twilio_provider(self):
        """Test getting Twilio provider."""
        with override_settings(
            SMS_PROVIDER='twilio',
            TWILIO_ACCOUNT_SID='test_sid',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_PHONE_NUMBER='+15555555555'
        ):
            # Reset provider
            SMSService._provider = None
            with patch('twilio.rest.Client'):
                provider = SMSService.get_provider()
                assert isinstance(provider, TwilioProvider)
    
    def test_invalid_provider_raises_error(self):
        """Test that invalid provider raises ValueError."""
        with override_settings(SMS_PROVIDER='invalid'):
            # Reset provider
            SMSService._provider = None
            with pytest.raises(ValueError, match="Unknown SMS provider"):
                SMSService.get_provider()
    
    def test_provider_singleton(self):
        """Test that provider is singleton."""
        with override_settings(SMS_PROVIDER='console'):
            SMSService._provider = None
            provider1 = SMSService.get_provider()
            provider2 = SMSService.get_provider()
            assert provider1 is provider2
    
    def test_send_2fa_code(self):
        """Test sending 2FA code."""
        mock_provider = Mock()
        mock_provider.send_sms.return_value = True
        SMSService._provider = mock_provider
        
        result = SMSService.send_2fa_code('+15555555555', '123456')
        
        assert result is True
        mock_provider.send_sms.assert_called_once()
        args = mock_provider.send_sms.call_args[0]
        assert args[0] == '+15555555555'
        assert '123456' in args[1]
        assert 'verification code' in args[1].lower()
    
    def test_send_2fa_code_handles_failure(self):
        """Test that send_2fa_code handles provider failures."""
        mock_provider = Mock()
        mock_provider.send_sms.side_effect = Exception('Provider error')
        SMSService._provider = mock_provider
        
        result = SMSService.send_2fa_code('+15555555555', '123456')
        
        assert result is False


@pytest.mark.django_db
class TestConsoleSMSProvider:
    """Test ConsoleSMSProvider."""
    
    def test_send_sms_success(self):
        """Test that console provider returns True."""
        provider = ConsoleSMSProvider()
        result = provider.send_sms('+15555555555', 'Test message')
        
        assert result is True
    
    def test_send_sms_with_different_numbers(self):
        """Test console provider with different phone numbers."""
        provider = ConsoleSMSProvider()
        
        result1 = provider.send_sms('+15555555555', 'Message 1')
        result2 = provider.send_sms('+447777777777', 'Message 2')
        
        assert result1 is True
        assert result2 is True


@pytest.mark.django_db
class TestTwilioProvider:
    """Test TwilioProvider."""
    
    def test_initialization_success(self):
        """Test successful Twilio client initialization."""
        with override_settings(
            TWILIO_ACCOUNT_SID='test_sid',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_PHONE_NUMBER='+15555555555'
        ):
            with patch('twilio.rest.Client') as mock_client:
                provider = TwilioProvider()
                
                assert provider.client is not None
                assert provider.from_number == '+15555555555'
                mock_client.assert_called_once_with('test_sid', 'test_token')
    
    def test_initialization_failure(self):
        """Test that initialization failure is handled gracefully."""
        with override_settings(
            TWILIO_ACCOUNT_SID='test_sid',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_PHONE_NUMBER='+15555555555'
        ):
            with patch('twilio.rest.Client', side_effect=Exception('Init error')):
                provider = TwilioProvider()
                assert provider.client is None
    
    def test_send_sms_success(self):
        """Test successful SMS sending via Twilio."""
        with override_settings(
            TWILIO_ACCOUNT_SID='test_sid',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_PHONE_NUMBER='+15555555555'
        ):
            mock_client = MagicMock()
            mock_message = Mock()
            mock_message.sid = 'SM123456'
            mock_client.messages.create.return_value = mock_message
            
            with patch('twilio.rest.Client', return_value=mock_client):
                provider = TwilioProvider()
                result = provider.send_sms('+15555555555', 'Test message')
                
                assert result is True
                mock_client.messages.create.assert_called_once_with(
                    body='Test message',
                    from_='+15555555555',
                    to='+15555555555'
                )
    
    def test_send_sms_without_client(self):
        """Test that send_sms fails gracefully without client."""
        provider = TwilioProvider.__new__(TwilioProvider)
        provider.client = None
        
        result = provider.send_sms('+15555555555', 'Test message')
        assert result is False
    
    def test_send_sms_handles_twilio_error(self):
        """Test that Twilio errors are handled."""
        with override_settings(
            TWILIO_ACCOUNT_SID='test_sid',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_PHONE_NUMBER='+15555555555'
        ):
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception('Twilio error')
            
            with patch('twilio.rest.Client', return_value=mock_client):
                provider = TwilioProvider()
                result = provider.send_sms('+15555555555', 'Test message')
                
                assert result is False


class TestSMSProviderBase:
    """Test base SMS provider class."""
    
    def test_base_provider_interface(self):
        """Test that base provider defines the interface."""
        from messaging.providers.base import BaseSMSProvider
        
        # Create a concrete implementation
        class TestProvider(BaseSMSProvider):
            def send_sms(self, phone_number: str, message: str) -> bool:
                raise NotImplementedError("Test")
        
        provider = TestProvider()
        
        with pytest.raises(NotImplementedError):
            provider.send_sms('+15555555555', 'Test')


@pytest.mark.django_db
class TestSMSIntegration:
    """Integration tests for SMS functionality."""
    
    def test_end_to_end_console_flow(self):
        """Test complete flow with console provider."""
        with override_settings(SMS_PROVIDER='console'):
            SMSService._provider = None
            
            result = SMSService.send_2fa_code('+15555555555', '123456')
            
            assert result is True
    
    @patch('twilio.rest.Client')
    def test_end_to_end_twilio_flow(self, mock_client_class):
        """Test complete flow with Twilio provider."""
        mock_client = MagicMock()
        mock_message = Mock()
        mock_message.sid = 'SM123456'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        with override_settings(
            SMS_PROVIDER='twilio',
            TWILIO_ACCOUNT_SID='test_sid',
            TWILIO_AUTH_TOKEN='test_token',
            TWILIO_PHONE_NUMBER='+15555555555'
        ):
            SMSService._provider = None
            
            result = SMSService.send_2fa_code('+15555555556', '654321')
            
            assert result is True
            mock_client.messages.create.assert_called_once()
