"""Two-Factor Authentication Views"""
import logging

from django.http import HttpResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django_ratelimit.decorators import ratelimit

from mysite.notification_utils import create_message, success_response, error_response, rate_limit_response
from .models import TwoFactorSettings, TwoFactorAuditLog
from .serializers_2fa import (
    TwoFactorSetupSerializer,
    TwoFactorVerifySetupSerializer,
    TwoFactorVerifySerializer,
    TwoFactorStatusSerializer,
    RecoveryCodeSerializer,
    TrustedDeviceSerializer,
    TwoFactorDisableSerializer,
    TwoFactorPreferredMethodSerializer,
    TwoFactorMethodRemoveSerializer,
)
from .services.twofa_service import TwoFactorService
from .services.trusted_device_service import TrustedDeviceService
from .services.recovery_code_service import RecoveryCodeService


logger = logging.getLogger(__name__)


class TwoFactorSetupView(APIView):
    """Initiate 2FA setup"""
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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


class TwoFactorStatusView(APIView):
    """Get current 2FA settings"""
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

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

    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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


class RecoveryCodeGenerateView(APIView):
    """Generate new recovery codes"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: dict})
    @method_decorator(ratelimit(key='user', rate='1/d', method='POST', block=True))
    def post(self, request):
        """Generate new recovery codes (invalidates old ones)
        
        Rate limited to once per day to prevent abuse and confusion.
        """
        user = request.user
        
        try:
            settings_obj = user.twofa_settings
            if not settings_obj.is_enabled:
                return error_response(
                    'must_be_enabled_for_recovery',
                    [create_message('errors.twofa.must_be_enabled_for_recovery')],
                    status.HTTP_400_BAD_REQUEST
                )
        except TwoFactorSettings.DoesNotExist:
            return error_response(
                'not_configured',
                [create_message('errors.twofa.not_configured')],
                status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new codes (returns plain text codes now)
        recovery_codes = TwoFactorService.generate_recovery_codes(user)
        
        return success_response({
            'recovery_codes': recovery_codes,
        }, messages=[create_message('notifications.twofa.recovery_codes_generated')])


class RecoveryCodeDownloadView(APIView):
    """Download recovery codes"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request={
            'type': 'object',
            'properties': {
                'format': {'type': 'string', 'enum': ['txt', 'pdf']},
                'codes': {'type': 'array', 'items': {'type': 'string'}}
            }
        },
        responses={200: dict}
    )
    def post(self, request):
        """Download recovery codes in TXT or PDF format
        
        NOTE: Since codes are hashed for security, they can only be downloaded
        immediately after generation. This endpoint requires codes to be passed
        in the request body from the generation response.
        """
        format_type = request.data.get('format', 'txt')
        user = request.user
        
        # Get codes from request body (more secure than query params)
        recovery_codes = request.data.get('codes', [])
        
        if not recovery_codes or not isinstance(recovery_codes, list):
            return error_response(
                'recovery_codes_required',
                [create_message('errors.twofa.recovery_codes_required')],
                status.HTTP_400_BAD_REQUEST
            )
        
        if len(recovery_codes) == 0:
            return error_response(
                'no_recovery_codes',
                [create_message('errors.twofa.no_recovery_codes')],
                status.HTTP_400_BAD_REQUEST
            )
        
        if format_type == 'pdf':
            pdf_bytes = RecoveryCodeService.export_as_pdf(user, recovery_codes)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="tinybeans-recovery-codes.pdf"'
        else:
            txt_content = RecoveryCodeService.export_as_txt(user, recovery_codes)
            response = HttpResponse(txt_content, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="tinybeans-recovery-codes.txt"'
        
        # Log the download
        TwoFactorAuditLog.objects.create(
            user=user,
            action='recovery_codes_downloaded',
            method=format_type,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True
        )
        
        return response


class TrustedDevicesListView(APIView):
    """List and manage trusted devices"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: TrustedDeviceSerializer(many=True)})
    def get(self, request):
        """Get all trusted devices"""
        devices = TrustedDeviceService.get_trusted_devices(request.user)
        serializer = TrustedDeviceSerializer(devices, many=True)
        return success_response({'devices': serializer.data})
    
    @extend_schema(
        request={'device_id': 'string'},
        responses={200: dict}
    )
    def delete(self, request):
        """Remove a trusted device"""
        device_id = request.data.get('device_id')
        
        if not device_id:
            return error_response(
                'device_id_required',
                [create_message('errors.twofa.device_id_required')],
                status.HTTP_400_BAD_REQUEST
            )
        
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return success_response({}, messages=[create_message('notifications.twofa.device_removed')])
        else:
            return error_response(
                'device_not_found',
                [create_message('errors.twofa.device_not_found')],
                status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        responses={201: TrustedDeviceSerializer}
    )
    def post(self, request):
        """Add current device as a trusted device"""
        try:
            trusted_device, token, created = TrustedDeviceService.add_trusted_device(request.user, request)
        except Exception:
            logger.exception("Failed to add trusted device for user %s", request.user.pk)
            return error_response(
                'device_add_failed',
                [create_message('errors.twofa.device_add_failed')],
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        serializer = TrustedDeviceSerializer(trusted_device)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        message_key = (
            'notifications.twofa.device_added'
            if created
            else 'notifications.twofa.device_already_trusted'
        )
        response = success_response(
            {'device': serializer.data, 'created': created},
            messages=[
                create_message(
                    message_key,
                    {'device_name': trusted_device.device_name}
                )
            ],
            status_code=status_code
        )
        TrustedDeviceService.set_trusted_device_cookie(response, token)
        return response


class TrustedDeviceRemoveView(APIView):
    """Remove specific trusted device"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: dict})
    def delete(self, request, device_id):
        """Remove specific trusted device by ID"""
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return success_response({}, messages=[create_message('notifications.twofa.device_removed')])
        else:
            return error_response(
                'device_not_found',
                [create_message('errors.twofa.device_not_found')],
                status.HTTP_404_NOT_FOUND
            )


class TwoFactorVerifyLoginView(APIView):
    """Verify 2FA code during login and complete authentication"""
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=TwoFactorVerifySerializer,
        responses={200: dict}
    )
    def post(self, request):
        """Complete login by verifying 2FA code"""
        from .serializers_2fa import TwoFactorVerifyLoginSerializer
        from .token_utils import verify_partial_token, get_tokens_for_user, set_refresh_cookie
        from mysite.users.serializers import UserSerializer
        
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
