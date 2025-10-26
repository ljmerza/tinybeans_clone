"""Login-time verification for two-factor challenges."""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.auth.models import TwoFactorAuditLog, TwoFactorSettings
from mysite.auth.serializers import (
    TwoFactorVerifyLoginSerializer,
    TwoFactorVerifySerializer,
)
from mysite.auth.services.trusted_device_service import TrustedDeviceService
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.auth.token_utils import (
    get_tokens_for_user,
    set_refresh_cookie,
    verify_partial_token,
)
from mysite.notification_utils import (
    create_message,
    error_response,
    rate_limit_response,
    success_response,
)
from mysite.users.serializers import UserSerializer


class TwoFactorVerifyLoginView(APIView):
    """Verify 2FA code during login and complete authentication"""
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=TwoFactorVerifySerializer,
        responses={200: dict}
    )
    def post(self, request):
        """Complete login by verifying 2FA code"""
        serializer = TwoFactorVerifyLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        partial_token = serializer.validated_data['partial_token']
        remember_me = serializer.validated_data.get('remember_me', False)
        
        # Verify partial token with IP validation
        user = verify_partial_token(partial_token, request)
        if not user:
            return error_response(
                'partial_token_invalid',
                [create_message('errors.twofa.partial_token_invalid')],
                status.HTTP_400_BAD_REQUEST
            )
        
        try:
            settings_obj = user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_configured_for_account',
                [create_message('errors.twofa.not_configured_for_account')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Check if account is locked
        if settings_obj.is_locked():
            return rate_limit_response('errors.account_locked_2fa')
        
        # Verify 2FA code
        verified = False
        is_recovery_code = False
        
        if settings_obj.preferred_method == 'totp':
            verified = TwoFactorService.verify_totp(user, code)
        else:
            verified = TwoFactorService.verify_otp(user, code, purpose='login')
        
        # If regular code fails, try recovery code
        if not verified:
            # Check if it's a recovery code format (XXXX-XXXX-XXXX)
            if '-' in code and len(code) >= 14:
                verified = TwoFactorService.verify_recovery_code(user, code)
                is_recovery_code = verified
        
        if not verified:
            # Increment failed attempts
            settings_obj.increment_failed_attempts()
            
            # Log failed attempt
            TwoFactorAuditLog.objects.create(
                user=user,
                action='2fa_login_failed',
                method=settings_obj.preferred_method,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False
            )
            
            return error_response(
                'invalid_verification_code',
                [create_message('errors.twofa.invalid_verification_code')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Reset failed attempts on successful login
        settings_obj.reset_failed_attempts()
        
        # Log successful login
        TwoFactorAuditLog.objects.create(
            user=user,
            action='2fa_login_success',
            method='recovery_code' if is_recovery_code else settings_obj.preferred_method,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        # Create trusted device if remember_me is True
        device_token = None
        if remember_me and getattr(settings, 'TWOFA_TRUSTED_DEVICE_ENABLED', True):
            _, device_token, _ = TrustedDeviceService.add_trusted_device(user, request)
        
        # Generate full tokens
        tokens = get_tokens_for_user(user)
        
        response = success_response({
            'user': UserSerializer(user).data,
            'tokens': {'access': tokens['access']},
            'trusted_device': remember_me,
        })
        set_refresh_cookie(response, tokens['refresh'])
        
        # Set device_id cookie if remember_me
        if device_token:
            TrustedDeviceService.set_trusted_device_cookie(response, device_token)
        
        return response
