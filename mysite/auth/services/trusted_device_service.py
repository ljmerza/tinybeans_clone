"""Trusted Device Service for Remember Me functionality"""
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.core import signing
from django.utils import timezone

from ..models import TrustedDevice, TwoFactorAuditLog
from ..token_utils import get_client_ip

logger = logging.getLogger(__name__)

DEVICE_COOKIE_NAME = 'device_id'


@dataclass
class TrustedDeviceToken:
    """Represents a signed trusted device cookie."""
    device_id: str
    signed_value: str


class TrustedDeviceService:
    """Handle trusted device management"""
    
    @staticmethod
    def _hash_value(value: str) -> str:
        """Generate SHA-256 hash for a value."""
        return hashlib.sha256(value.encode('utf-8')).hexdigest()
    
    @staticmethod
    def _sign_device_id(device_id: str) -> str:
        """Return a signed value for the device identifier."""
        signer = signing.TimestampSigner(
            key=getattr(settings, 'TWOFA_TRUSTED_DEVICE_SIGNING_KEY', settings.SECRET_KEY)
        )
        return signer.sign(device_id)
    
    @staticmethod
    def _unsign_device_id(value: str) -> Optional[str]:
        """Validate and unsign a device identifier."""
        signer = signing.TimestampSigner(
            key=getattr(settings, 'TWOFA_TRUSTED_DEVICE_SIGNING_KEY', settings.SECRET_KEY)
        )
        max_age = getattr(settings, 'TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS', 30) * 24 * 60 * 60
        try:
            return signer.unsign(value, max_age=max_age)
        except signing.BadSignature:
            logger.warning("Rejected trusted device cookie due to bad signature.")
            return None
        except signing.SignatureExpired:
            logger.info("Trusted device cookie signature expired.")
            return None
    
    @staticmethod
    def _generate_device_id() -> str:
        """Generate a random device identifier."""
        return secrets.token_hex(32)
    
    @staticmethod
    def _fingerprint(request) -> Tuple[str, str]:
        """Generate hashed fingerprint (UA/IP) for binding."""
        user_agent = (request.META.get('HTTP_USER_AGENT') or '').strip()
        ip_address = get_client_ip(request) or ''
        return (
            TrustedDeviceService._hash_value(user_agent),
            TrustedDeviceService._hash_value(ip_address),
        )
    
    @staticmethod
    def _rotation_threshold():
        days = getattr(settings, 'TWOFA_TRUSTED_DEVICE_ROTATION_DAYS', 15)
        return timedelta(days=days) if days and days > 0 else None
    
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
        
        device_id = TrustedDeviceService._generate_device_id()
        device_name = TrustedDeviceService.get_device_name(request)
        ip_address = get_client_ip(request) or request.META.get('REMOTE_ADDR', '0.0.0.0')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ua_hash, ip_hash = TrustedDeviceService._fingerprint(request)
        
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
        
        expires_at = timezone.now() + timedelta(days=days)
        
        trusted_device = TrustedDevice.objects.create(
            user=user,
            device_id=device_id,
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            expires_at=expires_at,
        )
        
        # Send notification email
        try:
            from emails.mailers import TwoFactorMailer
            TwoFactorMailer.send_trusted_device_added(user, trusted_device)
        except Exception:
            logger.exception(
                "Failed to send trusted device notification email for user %s (device %s)",
                user.pk,
                device_id,
            )
        
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
        
        return trusted_device, TrustedDeviceService._build_token(trusted_device)
    
    @staticmethod
    def _build_token(device: TrustedDevice) -> TrustedDeviceToken:
        """Build a signed token payload for a trusted device."""
        signed = TrustedDeviceService._sign_device_id(device.device_id)
        return TrustedDeviceToken(device_id=device.device_id, signed_value=signed)
    
    @staticmethod
    def _rotate_device(device: TrustedDevice, request) -> TrustedDevice:
        """Rotate device identifier and fingerprint."""
        new_device_id = TrustedDeviceService._generate_device_id()
        ua_hash, ip_hash = TrustedDeviceService._fingerprint(request)
        max_age_days = getattr(settings, 'TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS', 30)
        device.device_id = new_device_id
        device.ua_hash = ua_hash
        device.ip_hash = ip_hash
        device.expires_at = timezone.now() + timedelta(days=max_age_days)
        device.user_agent = request.META.get('HTTP_USER_AGENT', '')
        device.ip_address = get_client_ip(request) or request.META.get('REMOTE_ADDR', '0.0.0.0')
        device.save(update_fields=['device_id', 'ua_hash', 'ip_hash', 'expires_at', 'user_agent', 'ip_address', 'last_used_at'])
        logger.info("Rotated trusted device identifier for user %s.", device.user.username)
        return device
    
    @staticmethod
    def is_trusted_device(user, token: TrustedDeviceToken, request) -> Tuple[bool, Optional[TrustedDeviceToken]]:
        """Check if device token is trusted, optionally rotating the identifier."""
        if not token:
            return False, None
        
        now = timezone.now()
        try:
            device = TrustedDevice.objects.get(
                user=user,
                device_id=token.device_id,
                expires_at__gt=now
            )
        except TrustedDevice.DoesNotExist:
            return False, None
        
        ua_hash, ip_hash = TrustedDeviceService._fingerprint(request)
        if not secrets.compare_digest(device.ua_hash or '', ua_hash):
            logger.warning(
                "Trusted device fingerprint mismatch (UA) for user %s. Rejecting device.",
                user.username,
            )
            return False, None
        if not secrets.compare_digest(device.ip_hash or '', ip_hash):
            logger.warning(
                "Trusted device fingerprint mismatch (IP) for user %s. Rejecting device.",
                user.username,
            )
            return False, None
        
        # Update last used timestamp
        device.last_used_at = now
        device.save(update_fields=['last_used_at'])
        
        rotated_token = None
        rotation_threshold = TrustedDeviceService._rotation_threshold()
        if rotation_threshold and device.created_at + rotation_threshold <= now:
            device = TrustedDeviceService._rotate_device(device, request)
            rotated_token = TrustedDeviceService._build_token(device)
        return True, rotated_token
    
    @staticmethod
    def get_device_id_from_request(request) -> Optional[TrustedDeviceToken]:
        """Extract and validate signed device token from request."""
        # Try cookie first
        signed_value = request.COOKIES.get(DEVICE_COOKIE_NAME)
        if not signed_value:
            signed_value = request.META.get('HTTP_X_DEVICE_ID')
        
        if not signed_value:
            return None
        
        device_id = TrustedDeviceService._unsign_device_id(signed_value)
        if not device_id:
            return None
        
        return TrustedDeviceToken(device_id=device_id, signed_value=signed_value)
    
    @staticmethod
    def set_trusted_device_cookie(response, token: TrustedDeviceToken, days=None):
        """Attach trusted device cookie to response."""
        if not token:
            return
        
        if days is None:
            days = getattr(settings, 'TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS', 30)
        max_age = days * 24 * 60 * 60
        secure = not settings.DEBUG
        response.set_cookie(
            key=DEVICE_COOKIE_NAME,
            value=token.signed_value,
            max_age=max_age,
            httponly=True,
            secure=secure,
            samesite='Strict' if secure else 'Lax',
        )
    
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
