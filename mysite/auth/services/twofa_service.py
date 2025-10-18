"""Two-Factor Authentication Service"""
import base64
import hmac
import hashlib
import io
import secrets
import string
from datetime import timedelta

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import TwoFactorSettings, TwoFactorCode, RecoveryCode, TwoFactorAuditLog

User = get_user_model()


class TwoFactorService:
    """Core 2FA business logic"""
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP code for email/SMS"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def _hash_otp(code: str) -> str:
        """Hash OTP code using HMAC-SHA256 with secret key."""
        key = getattr(settings, 'TWOFA_CODE_SIGNING_KEY', settings.SECRET_KEY)
        return hmac.new(
            key.encode('utf-8'),
            code.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def generate_totp_secret() -> str:
        """Generate TOTP secret key (base32 encoded)"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp_qr_code(user, secret: str) -> dict:
        """
        Generate QR code for TOTP setup
        Returns dict with URI and base64 image
        """
        totp = pyotp.TOTP(secret)
        issuer_name = getattr(settings, 'TWOFA_ISSUER_NAME', 'Tinybeans')
        uri = totp.provisioning_uri(
            name=user.email or user.username,
            issuer_name=issuer_name
        )
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'uri': uri,
            'qr_code_image': f'data:image/png;base64,{img_str}',
            'secret': secret
        }
    
    @staticmethod
    def verify_totp(user, code: str) -> bool:
        """Verify TOTP code from authenticator app"""
        try:
            settings_obj = user.twofa_settings
            if not settings_obj.totp_secret:
                return False
            
            totp = pyotp.TOTP(settings_obj.totp_secret)
            # Allow 1 time step (30s) drift in either direction
            return totp.verify(code, valid_window=1)
        except Exception:
            return False
    
    @staticmethod
    def send_otp(user, method='email', purpose='login') -> TwoFactorCode:
        """Generate and send OTP via email/SMS"""
        code = TwoFactorService.generate_otp()
        expiry_minutes = getattr(settings, 'TWOFA_CODE_EXPIRY_MINUTES', 10)
        
        # Invalidate any previous unused codes for the same method/purpose
        TwoFactorCode.objects.filter(
            user=user,
            method=method,
            purpose=purpose,
            is_used=False,
        ).update(is_used=True, expires_at=timezone.now())

        # Create new code record
        code_hash = TwoFactorService._hash_otp(code)
        code_obj = TwoFactorCode.objects.create(
            user=user,
            code_hash=code_hash,
            code_preview=code[-6:],
            method=method,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
        )
        
        # Send via appropriate method
        if method == 'email':
            from mysite.emails.mailers import TwoFactorMailer
            TwoFactorMailer.send_2fa_code(user, code)
        elif method == 'sms':
            from mysite.messaging.tasks import send_2fa_sms
            settings_obj = user.twofa_settings
            if settings_obj.phone_number:
                send_2fa_sms.delay(settings_obj.phone_number, code)
        
        return code_obj
    
    @staticmethod
    def verify_otp(user, code, purpose='login') -> bool:
        """Verify OTP code and mark as used"""
        try:
            code_hash = TwoFactorService._hash_otp(str(code))
            code_obj = TwoFactorCode.objects.filter(
                user=user,
                code_hash=code_hash,
                purpose=purpose,
                is_used=False
            ).first()
            
            if not code_obj:
                return False
            
            # Increment attempts
            code_obj.attempts += 1
            code_obj.save()
            
            # Check if valid
            if not code_obj.is_valid():
                return False
            
            # Mark as used
            code_obj.is_used = True
            code_obj.save()
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_recovery_codes(user, count=10) -> list:
        """Generate recovery codes for user and return plain text codes"""
        # Delete existing unused codes
        RecoveryCode.objects.filter(user=user, is_used=False).delete()
        
        plain_codes = []
        for _ in range(count):
            # Generate code in format XXXX-XXXX-XXXX
            code = '-'.join(
                ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
                for _ in range(3)
            )
            
            # Store hashed version
            RecoveryCode.create_recovery_code(user, code)
            plain_codes.append(code)
        
        return plain_codes
    
    @staticmethod
    def verify_recovery_code(user, code) -> bool:
        """Verify and consume recovery code"""
        try:
            # Use the model's verify_code method which handles hashing
            success = RecoveryCode.verify_code(user, code)
            
            if success:
                # Send alert email
                from mysite.emails.mailers import TwoFactorMailer
                TwoFactorMailer.send_recovery_code_used_alert(user)
            
            return success
        except Exception:
            return False
    
    @staticmethod
    def is_rate_limited(user) -> bool:
        """Check if user has exceeded attempt limits"""
        rate_limit_window = getattr(settings, 'TWOFA_RATE_LIMIT_WINDOW', 900)  # 15 minutes
        rate_limit_max = getattr(settings, 'TWOFA_RATE_LIMIT_MAX', 3)
        
        if rate_limit_max <= 0:
            return False

        if rate_limit_window <= 0:
            return False

        since = timezone.now() - timedelta(seconds=rate_limit_window)
        recent_codes = TwoFactorCode.objects.filter(
            user=user,
            created_at__gte=since
        ).count()

        return recent_codes >= rate_limit_max
