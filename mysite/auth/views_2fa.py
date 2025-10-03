"""Two-Factor Authentication Views"""
from django.http import HttpResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django_ratelimit.decorators import ratelimit

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
from .response_utils import rate_limit_response


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
            
            return Response({
                'method': 'totp',
                'secret': secret,
                'qr_code': qr_data['uri'],
                'qr_code_image': qr_data['qr_code_image'],
                'message': 'Scan QR code with your authenticator app',
            })
        
        elif method in ['email', 'sms']:
            update_fields = ['preferred_method']

            if method == 'sms':
                if not phone_number:
                    return Response(
                        {'error': 'Phone number required for SMS method'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                settings_obj.phone_number = phone_number
                settings_obj.sms_verified = False
                update_fields.extend(['phone_number', 'sms_verified'])

            settings_obj.save(update_fields=update_fields)
            
            # Check rate limiting
            if TwoFactorService.is_rate_limited(user):
                return rate_limit_response()
            
            # Send OTP
            code_obj = TwoFactorService.send_otp(user, method=method, purpose='setup')
            
            return Response({
                'method': method,
                'message': f'Verification code sent to your {method}',
                'expires_in': 600,
            })
        
        return Response(
            {'error': 'Invalid method'},
            status=status.HTTP_400_BAD_REQUEST
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
            return Response(
                {'error': '2FA not initialized. Start setup first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify code based on method
        verified = False
        if settings_obj.preferred_method == 'totp':
            verified = TwoFactorService.verify_totp(user, code)
        else:
            verified = TwoFactorService.verify_otp(user, code, purpose='setup')
        
        if not verified:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
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
        from emails.mailers import TwoFactorMailer
        TwoFactorMailer.send_2fa_enabled_notification(user)
        
        return Response({
            'enabled': True,
            'method': settings_obj.preferred_method,
            'recovery_codes': recovery_codes,  # Already plain text codes
            'message': '2FA enabled successfully. Save your recovery codes!'
        })


class TwoFactorStatusView(APIView):
    """Get current 2FA settings"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: TwoFactorStatusSerializer})
    def get(self, request):
        """Get 2FA status for current user"""
        try:
            settings_obj = request.user.twofa_settings
            serializer = TwoFactorStatusSerializer(settings_obj)
            return Response(serializer.data)
        except TwoFactorSettings.DoesNotExist:
            return Response({
                'is_enabled': False,
                'preferred_method': None,
                'phone_number': None,
                'backup_email': None,
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
            return Response(
                {'error': '2FA not configured'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not settings_obj.is_enabled:
            return Response(
                {'error': 'Enable 2FA before changing the default method'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if method == 'totp':
            if not getattr(settings_obj, '_totp_secret_encrypted', None):
                return Response(
                    {
                        'error': 'Authenticator app not configured yet. Set up the authenticator app from the 2FA setup page first.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not settings_obj.totp_verified:
                return Response(
                    {'error': 'Verify your authenticator app via TOTP setup before choosing it as default'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if method == 'sms':
            if not settings_obj.phone_number:
                return Response(
                    {'error': 'Add a phone number via SMS setup before using SMS as default'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not settings_obj.sms_verified:
                return Response(
                    {'error': 'Verify your phone number via SMS setup before choosing it as default'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if method == 'email':
            if not settings_obj.email_verified:
                return Response(
                    {'error': 'Verify email via Email setup before choosing it as default'},
                    status=status.HTTP_400_BAD_REQUEST,
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

        return Response({
            'preferred_method': method,
            'message': f'Default 2FA method updated to {method.upper()}',
        })


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
            return Response(
                {'error': '2FA not configured'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if method == 'email':
            return Response(
                {
                    'error': 'Email-based 2FA cannot be removed. Choose another preferred method or disable 2FA.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_fields = set()
        previously_enabled = settings_obj.is_enabled
        previous_preferred = settings_obj.preferred_method

        if method == 'totp':
            if not getattr(settings_obj, '_totp_secret_encrypted', None):
                return Response(
                    {'error': 'Authenticator app 2FA is not configured'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            settings_obj.totp_secret = None
            settings_obj.totp_verified = False
            update_fields.update({'_totp_secret_encrypted', 'totp_verified'})

        elif method == 'sms':
            if not settings_obj.phone_number:
                return Response(
                    {'error': 'SMS 2FA is not configured'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            settings_obj.phone_number = None
            settings_obj.sms_verified = False
            update_fields.update({'phone_number', 'sms_verified'})

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

        message = f"{method.upper()} 2FA method removed."
        if became_disabled:
            message += ' Two-factor authentication has been disabled because no other verified methods are available.'
        elif preferred_changed:
            message += f" Preferred method updated to {settings_obj.preferred_method.upper()}."

        return Response(
            {
                'message': message,
                'method_removed': method,
                'preferred_method_changed': preferred_changed,
                'twofa_disabled': became_disabled,
                'status': status_payload,
            }
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
            return Response(
                {'error': '2FA not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not settings_obj.is_enabled:
            return Response(
                {'error': '2FA is already disabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For TOTP, no code needs to be sent
        if settings_obj.preferred_method == 'totp':
            return Response({
                'method': 'totp',
                'message': 'Enter your authenticator code to disable 2FA',
            })
        
        # For email/SMS, check rate limiting
        if TwoFactorService.is_rate_limited(user):
            return rate_limit_response()
        
        # Send OTP for disable purpose
        code_obj = TwoFactorService.send_otp(user, method=settings_obj.preferred_method, purpose='disable')
        
        return Response({
            'method': settings_obj.preferred_method,
            'message': f'Verification code sent to your {settings_obj.preferred_method}',
            'expires_in': 600,
        })


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
            return Response(
                {'error': '2FA not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not settings_obj.is_enabled:
            return Response(
                {'error': '2FA is already disabled'},
                status=status.HTTP_400_BAD_REQUEST
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
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
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
        from emails.mailers import TwoFactorMailer
        TwoFactorMailer.send_2fa_disabled_notification(user)
        
        return Response({
            'enabled': False,
            'message': '2FA disabled successfully'
        })


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
                return Response(
                    {'error': '2FA must be enabled to generate recovery codes'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except TwoFactorSettings.DoesNotExist:
            return Response(
                {'error': '2FA not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new codes (returns plain text codes now)
        recovery_codes = TwoFactorService.generate_recovery_codes(user)
        
        return Response({
            'recovery_codes': recovery_codes,  # Already plain text codes
            'message': 'New recovery codes generated. Old codes have been invalidated.'
        })


class RecoveryCodeDownloadView(APIView):
    """Download recovery codes"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: dict})
    def get(self, request):
        """Download recovery codes in TXT or PDF format
        
        NOTE: Since codes are hashed for security, they can only be downloaded
        immediately after generation. This endpoint requires codes to be passed
        as query parameters from the generation response.
        """
        format_type = request.query_params.get('format', 'txt')
        user = request.user
        
        # Get codes from query params (passed from frontend after generation)
        codes_param = request.query_params.get('codes')
        if not codes_param:
            return Response(
                {'error': 'Recovery codes must be provided. Codes can only be downloaded immediately after generation.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse codes (comma-separated)
        recovery_codes = codes_param.split(',')
        
        if not recovery_codes or len(recovery_codes) == 0:
            return Response(
                {'error': 'No recovery codes provided'},
                status=status.HTTP_400_BAD_REQUEST
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
        return Response({'devices': serializer.data})
    
    @extend_schema(
        request={'device_id': 'string'},
        responses={200: dict}
    )
    def delete(self, request):
        """Remove a trusted device"""
        device_id = request.data.get('device_id')
        
        if not device_id:
            return Response(
                {'error': 'device_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return Response({'message': 'Device removed successfully'})
        else:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TrustedDeviceRemoveView(APIView):
    """Remove specific trusted device"""
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: dict})
    def delete(self, request, device_id):
        """Remove specific trusted device by ID"""
        removed = TrustedDeviceService.remove_trusted_device(request.user, device_id)
        
        if removed:
            return Response({'message': 'Device removed successfully'})
        else:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
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
        from users.serializers import UserSerializer
        
        serializer = TwoFactorVerifyLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        partial_token = serializer.validated_data['partial_token']
        remember_me = serializer.validated_data.get('remember_me', False)
        
        # Verify partial token with IP validation
        user = verify_partial_token(partial_token, request)
        if not user:
            return Response(
                {'error': 'Invalid or expired partial token. Please login again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            settings_obj = user.twofa_settings
        except TwoFactorSettings.DoesNotExist:
            return Response(
                {'error': '2FA not configured for this account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if account is locked
        if settings_obj.is_locked():
            return rate_limit_response(
                'Account temporarily locked due to too many failed 2FA attempts. Please try again later.'
            )
        
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
            
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
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
        device_id = None
        if remember_me and getattr(settings, 'TWOFA_TRUSTED_DEVICE_ENABLED', True):
            trusted_device = TrustedDeviceService.add_trusted_device(user, request)
            device_id = trusted_device.device_id
        
        # Generate full tokens
        tokens = get_tokens_for_user(user)
        data = {
            'user': UserSerializer(user).data,
            'tokens': {'access': tokens['access']},
            'trusted_device': remember_me,
        }
        
        response = Response(data)
        set_refresh_cookie(response, tokens['refresh'])
        
        # Set device_id cookie if remember_me
        if device_id:
            secure = not settings.DEBUG
            response.set_cookie(
                key='device_id',
                value=device_id,
                max_age=30 * 24 * 60 * 60,  # 30 days
                httponly=True,
                secure=secure,
                samesite='Strict' if secure else 'Lax',
            )
        
        return response
