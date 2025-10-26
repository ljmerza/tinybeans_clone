"""Views responsible for initiating and verifying 2FA setup."""

from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from mysite.auth.models import TwoFactorAuditLog, TwoFactorSettings
from mysite.auth.permissions import IsEmailVerified
from mysite.auth.serializers import (
    TwoFactorSetupSerializer,
    TwoFactorVerifySetupSerializer,
)
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.notification_utils import (
    create_message,
    error_response,
    rate_limit_response,
    success_response,
)


class TwoFactorSetupView(APIView):
    """Initiate 2FA setup"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
    @extend_schema(
        request=TwoFactorSetupSerializer,
        responses={200: dict}
    )
    def post(self, request):
        """Start 2FA setup process"""
        serializer = TwoFactorSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        method = serializer.validated_data['method']
        phone_number = serializer.validated_data.get('phone_number')
        
        # Get or create settings
        settings_obj, created = TwoFactorSettings.objects.get_or_create(
            user=user,
            defaults={'preferred_method': method}
        )

        # Update preferred method to reflect the user's selection
        settings_obj.preferred_method = method
        
        if method == 'totp':
            # Generate TOTP secret and QR code
            secret = TwoFactorService.generate_totp_secret()
            settings_obj.totp_secret = secret
            settings_obj.totp_verified = False  # Reset until verified
            settings_obj.save()
            
            qr_data = TwoFactorService.generate_totp_qr_code(user, secret)
            
            return success_response({
                'method': 'totp',
                'secret': secret,
                'qr_code': qr_data['uri'],
                'qr_code_image': qr_data['qr_code_image'],
            }, messages=[create_message('notifications.twofa.setup_initiated')])
        
        elif method in ['email', 'sms']:
            update_fields = ['preferred_method']

            if method == 'sms':
                if not phone_number:
                    return error_response(
                        'phone_number_required',
                        [create_message('errors.twofa.phone_number_required')],
                        status.HTTP_400_BAD_REQUEST
                    )
                settings_obj.phone_number = phone_number
                settings_obj.sms_verified = False
                update_fields.extend(['phone_number', 'sms_verified'])

            settings_obj.save(update_fields=update_fields)
            
            # Check rate limiting
            if TwoFactorService.is_rate_limited(user):
                return rate_limit_response('errors.rate_limit_2fa')
            
            # Send OTP
            code_obj = TwoFactorService.send_otp(user, method=method, purpose='setup')
            
            return success_response({
                'method': method,
                'expires_in': 600,
            }, messages=[create_message('notifications.twofa.verification_code_sent', {'method': method})])
        
        return error_response(
            'invalid_method',
            [create_message('errors.twofa.invalid_method')],
            status.HTTP_400_BAD_REQUEST
        )

class TwoFactorVerifySetupView(APIView):
    """Verify and complete 2FA setup"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
    @extend_schema(
        request=TwoFactorVerifySetupSerializer,
        responses={200: dict}
    )
    def post(self, request):
        """Complete 2FA setup by verifying code"""
        serializer = TwoFactorVerifySetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        code = serializer.validated_data['code']
        
        try:
            settings_obj = user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_initialized',
                [create_message('errors.twofa.not_initialized')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Verify code based on method
        verified = False
        if settings_obj.preferred_method == 'totp':
            verified = TwoFactorService.verify_totp(user, code)
        else:
            verified = TwoFactorService.verify_otp(user, code, purpose='setup')
        
        if not verified:
            return error_response(
                'invalid_verification_code',
                [create_message('errors.twofa.invalid_verification_code')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Enable 2FA and mark verification state
        update_fields = ['is_enabled']
        settings_obj.is_enabled = True
        if settings_obj.preferred_method == 'totp':
            settings_obj.totp_verified = True
            update_fields.append('totp_verified')
        elif settings_obj.preferred_method == 'sms':
            settings_obj.sms_verified = True
            update_fields.append('sms_verified')
        elif settings_obj.preferred_method == 'email':
            settings_obj.email_verified = True
            update_fields.append('email_verified')
        settings_obj.save(update_fields=update_fields)
        
        # Generate recovery codes (returns plain text codes)
        recovery_codes = TwoFactorService.generate_recovery_codes(user)
        
        # Log the action
        TwoFactorAuditLog.objects.create(
            user=user,
            action='2fa_enabled',
            method=settings_obj.preferred_method,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        # Send notification email
        from mysite.emails.mailers import TwoFactorMailer
        TwoFactorMailer.send_2fa_enabled_notification(user)
        
        return success_response({
            'enabled': True,
            'method': settings_obj.preferred_method,
            'recovery_codes': recovery_codes,
        }, messages=[create_message('notifications.twofa.setup_complete')])
