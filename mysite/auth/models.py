from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet
import hashlib

User = get_user_model()


class GoogleOAuthState(models.Model):
    """Secure OAuth state token tracking.
    
    Stores OAuth state tokens to prevent CSRF attacks and replay attacks.
    State tokens expire after 10 minutes and can only be used once.
    
    Attributes:
        state_token: Unique state token (128 chars)
        code_verifier: PKCE code verifier for authorization code exchange
        redirect_uri: The redirect URI the OAuth flow will return to
        nonce: Additional CSRF protection token
        created_at: When the state was created
        used_at: When the state was used (null if unused)
        ip_address: IP address that initiated the OAuth flow
        user_agent: User agent that initiated the OAuth flow
        expires_at: When the state expires (10 minutes from creation)
    """
    state_token = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Unique OAuth state token"
    )
    code_verifier = models.CharField(
        max_length=128,
        help_text="PKCE code verifier"
    )
    redirect_uri = models.URLField(
        help_text="OAuth redirect URI"
    )
    nonce = models.CharField(
        max_length=64,
        help_text="Additional CSRF protection nonce"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When state was created"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When state was used"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address that initiated OAuth"
    )
    user_agent = models.TextField(
        help_text="User agent that initiated OAuth"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="When state expires (10 min)"
    )
    
    class Meta:
        verbose_name = 'Google OAuth State'
        verbose_name_plural = 'Google OAuth States'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['state_token', 'used_at'], name='auth_oauth_state_idx'),
            models.Index(fields=['expires_at'], name='auth_oauth_expires_idx'),
        ]
    
    def __str__(self):
        return f"OAuth State {self.state_token[:8]}... - {'Used' if self.used_at else 'Unused'}"
    
    def is_valid(self):
        """Check if state is still valid for use."""
        return (
            not self.used_at and
            self.expires_at > timezone.now()
        )
    
    def is_used(self):
        """Check if state has been used."""
        return self.used_at is not None
    
    def is_expired(self):
        """Check if state has expired."""
        return self.expires_at <= timezone.now()
    
    def mark_as_used(self):
        """Mark state as used to prevent replay attacks."""
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class TwoFactorSettings(models.Model):
    """User's 2FA preferences and configuration"""
    
    METHOD_CHOICES = [
        ('totp', 'Authenticator App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='twofa_settings'
    )
    is_enabled = models.BooleanField(default=False)
    preferred_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='totp'
    )
    _totp_secret_encrypted = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_column='totp_secret'
    )
    totp_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    sms_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    backup_email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Account lockout fields
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Two-Factor Settings'
        verbose_name_plural = 'Two-Factor Settings'
    
    def __str__(self):
        return f"{self.user.email} - 2FA: {'Enabled' if self.is_enabled else 'Disabled'}"
    
    @property
    def totp_secret(self):
        """Decrypt and return TOTP secret"""
        if not self._totp_secret_encrypted:
            return None
        try:
            cipher = Fernet(settings.TWOFA_ENCRYPTION_KEY.encode())
            return cipher.decrypt(self._totp_secret_encrypted.encode()).decode()
        except Exception:
            return None
    
    @totp_secret.setter
    def totp_secret(self, value):
        """Encrypt and store TOTP secret"""
        if value:
            cipher = Fernet(settings.TWOFA_ENCRYPTION_KEY.encode())
            self._totp_secret_encrypted = cipher.encrypt(value.encode()).decode()
        else:
            self._totp_secret_encrypted = None
    
    def is_locked(self):
        """Check if account is locked due to failed 2FA attempts"""
        if not self.locked_until:
            return False
        if self.locked_until > timezone.now():
            return True
        # Expired lock - reset
        self.locked_until = None
        self.failed_attempts = 0
        self.save(update_fields=['locked_until', 'failed_attempts'])
        return False
    
    def increment_failed_attempts(self):
        """Increment failed attempts and lock if threshold reached"""
        from datetime import timedelta
        self.failed_attempts += 1
        
        lockout_threshold = getattr(settings, 'TWOFA_LOCKOUT_THRESHOLD', 5)
        lockout_duration = getattr(settings, 'TWOFA_LOCKOUT_DURATION_MINUTES', 30)
        
        if self.failed_attempts >= lockout_threshold:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_duration)
        
        self.save(update_fields=['failed_attempts', 'locked_until'])
    
    def reset_failed_attempts(self):
        """Reset failed attempts counter"""
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_attempts', 'locked_until'])


class TwoFactorCode(models.Model):
    """Temporary OTP codes for verification"""
    
    PURPOSE_CHOICES = [
        ('login', 'Login Verification'),
        ('setup', 'Setup Verification'),
        ('disable', 'Disable 2FA'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64, default='')
    code_preview = models.CharField(max_length=6, blank=True, default='')
    method = models.CharField(max_length=20)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'code_hash', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Two-Factor Code'
        verbose_name_plural = 'Two-Factor Codes'
    
    def __str__(self):
        preview = self.code_preview or '******'
        return f"{self.user.email} - {preview} ({self.purpose})"
    
    def is_valid(self):
        """Check if code is still valid"""
        return not self.is_used and self.attempts < self.max_attempts and self.expires_at > timezone.now()


class RecoveryCode(models.Model):
    """Recovery codes for account access when 2FA is unavailable"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_codes')
    code_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Recovery Code'
        verbose_name_plural = 'Recovery Codes'
    
    def __str__(self):
        return f"{self.user.email} - Recovery Code ({'Used' if self.is_used else 'Available'})"
    
    @classmethod
    def create_recovery_code(cls, user, plain_code):
        """Create recovery code with hashed value"""
        code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
        return cls.objects.create(user=user, code_hash=code_hash)
    
    @classmethod
    def verify_code(cls, user, plain_code):
        """Verify recovery code and mark as used"""
        code_hash = hashlib.sha256(plain_code.upper().encode()).hexdigest()
        try:
            recovery_code = cls.objects.get(
                user=user,
                code_hash=code_hash,
                is_used=False
            )
            recovery_code.is_used = True
            recovery_code.used_at = timezone.now()
            recovery_code.save()
            return True
        except cls.DoesNotExist:
            return False


class TrustedDevice(models.Model):
    """Trusted devices for 2FA skip (Remember Me feature)"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trusted_devices')
    device_id = models.CharField(max_length=64, unique=True)
    device_name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    ip_hash = models.CharField(max_length=64, blank=True, default='')
    ua_hash = models.CharField(max_length=64, blank=True, default='')
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'device_id']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = [['user', 'device_id']]
        verbose_name = 'Trusted Device'
        verbose_name_plural = 'Trusted Devices'
    
    def __str__(self):
        return f"{self.user.email} - {self.device_name}"
    
    def is_valid(self):
        """Check if device trust is still valid"""
        return self.expires_at > timezone.now()


class TwoFactorAuditLog(models.Model):
    """Audit log for 2FA events"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    method = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    device_id = models.CharField(max_length=64, blank=True)
    success = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Two-Factor Audit Log'
        verbose_name_plural = 'Two-Factor Audit Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {'Success' if self.success else 'Failed'}"


class MagicLoginToken(models.Model):
    """Magic login link tokens for passwordless authentication."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='magic_login_tokens')
    token = models.CharField(max_length=64, blank=True, default='')
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Magic Login Token'
        verbose_name_plural = 'Magic Login Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token_hash', 'is_used'], name='auth_app_ma_tokenhash_idx'),
            models.Index(fields=['user', 'expires_at'], name='auth_app_ma_user_id_f5d5d3_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {'Used' if self.is_used else 'Unused'} - {self.created_at}"
    
    def is_valid(self):
        """Check if token is still valid."""
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
