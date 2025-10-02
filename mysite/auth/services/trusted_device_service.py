"""Trusted Device Service for Remember Me functionality"""
import hashlib
import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from ..models import TrustedDevice, TwoFactorAuditLog

logger = logging.getLogger(__name__)


class TrustedDeviceService:
    """Handle trusted device management"""
    
    @staticmethod
    def generate_device_id(request) -> str:
        """Generate unique device identifier from browser fingerprint"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        # Create fingerprint
        fingerprint = f"{user_agent}|{accept_language}|{accept_encoding}"
        
        # Add random salt for uniqueness
        salt = secrets.token_urlsafe(16)
        combined = f"{fingerprint}|{salt}"
        
        # Hash to create device_id
        device_id = hashlib.sha256(combined.encode()).hexdigest()
        
        return device_id
    
    @staticmethod
    def get_device_name(request) -> str:
        """Extract readable device name from user agent"""
        try:
            from user_agents import parse
            user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
            ua = parse(user_agent)
            
            browser = f"{ua.browser.family} {ua.browser.version_string}"
            os = f"{ua.os.family} {ua.os.version_string}"
            device = ua.device.family
            
            if device == 'Other':
                return f"{browser} on {os}"
            return f"{browser} on {device} ({os})"
        except Exception as e:
            # SECURITY: Log user agent parsing errors for debugging
            user_agent = request.META.get('HTTP_USER_AGENT', 'N/A')
            logger.warning(
                f"Failed to parse user agent: {str(e)}. "
                f"User-Agent string: {user_agent[:100]}"  # Limit length to avoid log spam
            )
            return "Unknown Device"
    
    @staticmethod
    def add_trusted_device(user, request, days=None):
        """Add current device to trusted devices list"""
        if days is None:
            days = getattr(settings, 'TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS', 30)
        
        device_id = TrustedDeviceService.generate_device_id(request)
        device_name = TrustedDeviceService.get_device_name(request)
        ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check if user has too many trusted devices
        max_devices = getattr(settings, 'TWOFA_TRUSTED_DEVICE_MAX_COUNT', 5)
        existing_count = TrustedDevice.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).count()
        
        if existing_count >= max_devices:
            # Remove oldest device
            oldest = TrustedDevice.objects.filter(
                user=user,
                expires_at__gt=timezone.now()
            ).order_by('created_at').first()
            if oldest:
                oldest.delete()
        
        # Create or update trusted device
        trusted_device, created = TrustedDevice.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults={
                'device_name': device_name,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'expires_at': timezone.now() + timedelta(days=days),
            }
        )
        
        # Send notification email
        if created:
            try:
                from emails.mailers import TwoFactorMailer
                TwoFactorMailer.send_trusted_device_added(user, trusted_device)
            except Exception:
                pass
        
        # Log the action
        TwoFactorAuditLog.objects.create(
            user=user,
            action='trusted_device_added',
            method='device_trust',
            ip_address=ip_address,
            user_agent=user_agent,
            device_id=device_id,
            success=True
        )
        
        return trusted_device
    
    @staticmethod
    def is_trusted_device(user, device_id) -> bool:
        """Check if device is trusted and not expired"""
        try:
            device = TrustedDevice.objects.get(
                user=user,
                device_id=device_id,
                expires_at__gt=timezone.now()
            )
            # Update last_used_at
            device.last_used_at = timezone.now()
            device.save(update_fields=['last_used_at'])
            return True
        except TrustedDevice.DoesNotExist:
            return False
    
    @staticmethod
    def get_device_id_from_request(request) -> str:
        """Extract device_id from request (cookie or header)"""
        # Try cookie first
        device_id = request.COOKIES.get('device_id')
        if device_id:
            return device_id
        
        # Try header
        device_id = request.META.get('HTTP_X_DEVICE_ID')
        return device_id
    
    @staticmethod
    def remove_trusted_device(user, device_id) -> bool:
        """Remove device from trusted list"""
        try:
            device = TrustedDevice.objects.get(user=user, device_id=device_id)
            device.delete()
            
            # Log the removal
            TwoFactorAuditLog.objects.create(
                user=user,
                action='trusted_device_removed',
                method='device_trust',
                device_id=device_id,
                success=True
            )
            
            return True
        except TrustedDevice.DoesNotExist:
            return False
    
    @staticmethod
    def get_trusted_devices(user):
        """Get all active trusted devices for user"""
        return TrustedDevice.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).order_by('-last_used_at')
    
    @staticmethod
    def cleanup_expired_devices():
        """Clean up expired trusted devices (run as scheduled task)"""
        expired_count = TrustedDevice.objects.filter(
            expires_at__lte=timezone.now()
        ).delete()[0]
        
        return expired_count
