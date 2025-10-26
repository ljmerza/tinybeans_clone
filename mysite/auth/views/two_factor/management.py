"""Views for inspecting and managing existing 2FA configuration."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.auth.models import TwoFactorAuditLog, TwoFactorSettings
from mysite.auth.permissions import IsEmailVerified
from mysite.auth.serializers import (
    TwoFactorDisableSerializer,
    TwoFactorMethodRemoveSerializer,
    TwoFactorPreferredMethodSerializer,
    TwoFactorStatusSerializer,
)
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.notification_utils import (
    create_message,
    error_response,
    rate_limit_response,
    success_response,
)


class TwoFactorStatusView(APIView):
    """Get current 2FA settings"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(responses={200: TwoFactorStatusSerializer})
    def get(self, request):
        """Get 2FA status for current user"""
        try:
            settings_obj = request.user.twofa_settings
            serializer = TwoFactorStatusSerializer(settings_obj)
            return success_response(serializer.data)
        except TwoFactorSettings.DoesNotExist:
            return success_response({
                'is_enabled': False,
                'preferred_method': None,
                'phone_number': None,
                'backup_email': None,
                'email_address': request.user.email,
                'has_totp': False,
                'has_sms': False,
                'has_email': False,
                'sms_verified': False
            })

class TwoFactorPreferredMethodView(APIView):
    """Update preferred 2FA method"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        request=TwoFactorPreferredMethodSerializer,
        responses={200: dict},
    )
    def post(self, request):
        serializer = TwoFactorPreferredMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data['method']
        user = request.user

        try:
            settings_obj = user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_configured',
                [create_message('errors.twofa.not_configured')],
                status.HTTP_400_BAD_REQUEST,
            )

        if not settings_obj.is_enabled:
            return error_response(
                'enable_before_changing_method',
                [create_message('errors.twofa.enable_before_changing_method')],
                status.HTTP_400_BAD_REQUEST,
            )

        if method == 'totp':
            if not getattr(settings_obj, '_totp_secret_encrypted', None):
                return error_response(
                    'totp_not_configured',
                    [create_message('errors.twofa.totp_not_configured')],
                    status.HTTP_400_BAD_REQUEST,
                )
            if not settings_obj.totp_verified:
                return error_response(
                    'totp_not_verified',
                    [create_message('errors.twofa.totp_not_verified')],
                    status.HTTP_400_BAD_REQUEST,
                )

        if method == 'sms':
            if not settings_obj.phone_number:
                return error_response(
                    'sms_no_phone',
                    [create_message('errors.twofa.sms_no_phone')],
                    status.HTTP_400_BAD_REQUEST,
                )

            if not settings_obj.sms_verified:
                return error_response(
                    'sms_not_verified',
                    [create_message('errors.twofa.sms_not_verified')],
                    status.HTTP_400_BAD_REQUEST,
                )

        if method == 'email':
            if not settings_obj.email_verified:
                return error_response(
                    'email_not_verified',
                    [create_message('errors.twofa.email_not_verified')],
                    status.HTTP_400_BAD_REQUEST,
                )

        settings_obj.preferred_method = method
        settings_obj.save(update_fields=['preferred_method'])

        TwoFactorAuditLog.objects.create(
            user=user,
            action='2fa_preferred_method_updated',
            method=method,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
        )

        return success_response({
            'preferred_method': method,
        }, messages=[create_message('notifications.twofa.preferred_method_updated', {'method': method.upper()})])

class TwoFactorMethodRemoveView(APIView):
    """Remove a configured 2FA method"""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        responses={200: dict},
        parameters=[
            OpenApiParameter(
                name='method',
                location=OpenApiParameter.PATH,
                description='2FA method to remove',
                required=True,
                enum=['totp', 'sms', 'email'],
            )
        ],
    )
    def delete(self, request, method: str):
        validator = TwoFactorMethodRemoveSerializer(data={'method': (method or '').lower()})
        validator.is_valid(raise_exception=True)
        method = validator.validated_data['method']

        try:
            settings_obj = request.user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_configured',
                [create_message('errors.twofa.not_configured')],
                status.HTTP_400_BAD_REQUEST,
            )

        update_fields = set()
        previously_enabled = settings_obj.is_enabled
        previous_preferred = settings_obj.preferred_method

        if method == 'totp':
            if not getattr(settings_obj, '_totp_secret_encrypted', None):
                return error_response(
                    'method_not_configured',
                    [create_message('errors.twofa.method_not_configured', {'method': 'Authenticator app'})],
                    status.HTTP_400_BAD_REQUEST,
                )
            settings_obj.totp_secret = None
            settings_obj.totp_verified = False
            update_fields.update({'_totp_secret_encrypted', 'totp_verified'})

        elif method == 'sms':
            if not settings_obj.phone_number:
                return error_response(
                    'method_not_configured',
                    [create_message('errors.twofa.method_not_configured', {'method': 'SMS'})],
                    status.HTTP_400_BAD_REQUEST,
                )
            settings_obj.phone_number = None
            settings_obj.sms_verified = False
            update_fields.update({'phone_number', 'sms_verified'})

        elif method == 'email':
            if not settings_obj.email_verified:
                return error_response(
                    'method_not_configured',
                    [create_message('errors.twofa.method_not_configured', {'method': 'Email'})],
                    status.HTTP_400_BAD_REQUEST,
                )
            settings_obj.email_verified = False
            update_fields.add('email_verified')

        if settings_obj.preferred_method == method:
            fallback_preferred = None
            if method == 'totp':
                if settings_obj.phone_number and settings_obj.sms_verified:
                    fallback_preferred = 'sms'
                elif settings_obj.email_verified:
                    fallback_preferred = 'email'
            elif method == 'sms':
                if getattr(settings_obj, '_totp_secret_encrypted', None) and settings_obj.totp_verified:
                    fallback_preferred = 'totp'
                elif settings_obj.email_verified:
                    fallback_preferred = 'email'
            elif method == 'email':
                if getattr(settings_obj, '_totp_secret_encrypted', None) and settings_obj.totp_verified:
                    fallback_preferred = 'totp'
                elif settings_obj.phone_number and settings_obj.sms_verified:
                    fallback_preferred = 'sms'

            if fallback_preferred:
                settings_obj.preferred_method = fallback_preferred
                update_fields.add('preferred_method')
            elif settings_obj.is_enabled:
                settings_obj.is_enabled = False
                update_fields.add('is_enabled')

        if update_fields:
            settings_obj.save(update_fields=list(update_fields))
        else:
            settings_obj.save()

        became_disabled = previously_enabled and not settings_obj.is_enabled
        preferred_changed = settings_obj.preferred_method != previous_preferred

        TwoFactorAuditLog.objects.create(
            user=request.user,
            action='2fa_method_removed',
            method=method,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
        )

        status_payload = TwoFactorStatusSerializer(settings_obj).data

        messages = [create_message('notifications.twofa.method_removed', {'method': method.upper()})]
        if became_disabled:
            messages.append(create_message('notifications.twofa.method_removed_disabled'))
        elif preferred_changed:
            messages.append(create_message('notifications.twofa.method_removed_preferred_changed', {'preferred_method': settings_obj.preferred_method.upper()}))

        return success_response(
            {
                'method_removed': method,
                'preferred_method_changed': preferred_changed,
                'twofa_disabled': became_disabled,
                'status': status_payload,
            },
            messages=messages
        )

class TwoFactorDisableRequestView(APIView):
    """Request a code to disable 2FA"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
    @extend_schema(responses={200: dict})
    def post(self, request):
        """Send verification code for disabling 2FA"""
        user = request.user
        
        try:
            settings_obj = user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_enabled',
                [create_message('errors.twofa.not_enabled')],
                status.HTTP_400_BAD_REQUEST
            )
        
        if not settings_obj.is_enabled:
            return error_response(
                'already_disabled',
                [create_message('errors.twofa.already_disabled')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # For TOTP, no code needs to be sent
        if settings_obj.preferred_method == 'totp':
            return success_response({
                'method': 'totp',
            }, messages=[create_message('notifications.twofa.enter_authenticator_code')])
        
        # For email/SMS, check rate limiting
        if TwoFactorService.is_rate_limited(user):
            return rate_limit_response('errors.rate_limit_2fa')
        
        # Send OTP for disable purpose
        code_obj = TwoFactorService.send_otp(user, method=settings_obj.preferred_method, purpose='disable')
        
        return success_response({
            'method': settings_obj.preferred_method,
            'expires_in': 600,
        }, messages=[create_message('notifications.twofa.verification_code_sent', {'method': settings_obj.preferred_method})])

class TwoFactorDisableView(APIView):
    """Disable 2FA"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
    @extend_schema(
        request=TwoFactorDisableSerializer,
        responses={200: dict}
    )
    def post(self, request):
        """Disable 2FA after code verification"""
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        code = serializer.validated_data['code']
        
        try:
            settings_obj = user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_enabled',
                [create_message('errors.twofa.not_enabled')],
                status.HTTP_400_BAD_REQUEST
            )
        
        if not settings_obj.is_enabled:
            return error_response(
                'already_disabled',
                [create_message('errors.twofa.already_disabled')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Verify code
        verified = False
        if settings_obj.preferred_method == 'totp':
            verified = TwoFactorService.verify_totp(user, code)
        else:
            verified = TwoFactorService.verify_otp(user, code, purpose='disable')
        
        if not verified:
            # Try recovery code
            verified = TwoFactorService.verify_recovery_code(user, code)
        
        if not verified:
            return error_response(
                'invalid_verification_code',
                [create_message('errors.twofa.invalid_verification_code')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Disable 2FA and clear all verified methods
        settings_obj.is_enabled = False
        settings_obj.totp_secret = None
        settings_obj.totp_verified = False
        settings_obj.phone_number = None
        settings_obj.sms_verified = False
        settings_obj.email_verified = False
        settings_obj.save()
        
        # Log the action
        TwoFactorAuditLog.objects.create(
            user=user,
            action='2fa_disabled',
            method=settings_obj.preferred_method,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        # Send notification email
        from mysite.emails.mailers import TwoFactorMailer
        TwoFactorMailer.send_2fa_disabled_notification(user)
        
        return success_response({
            'enabled': False,
        }, messages=[create_message('notifications.twofa.disabled')])
