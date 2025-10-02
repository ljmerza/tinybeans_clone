"""Two-Factor Authentication Views"""
from django.http import HttpResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
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
)
from .services.twofa_service import TwoFactorService
from .services.trusted_device_service import TrustedDeviceService
from .services.recovery_code_service import RecoveryCodeService


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
        
        if method == 'totp':
            # Generate TOTP secret and QR code
            secret = TwoFactorService.generate_totp_secret()
            settings_obj.totp_secret = secret
            settings_obj.save()
            
            qr_data = TwoFactorService.generate_totp_qr_code(user, secret)
            
            return Response({
                'method': 'totp',
                'secret': secret,
                'qr_code': qr_data['uri'],
                'qr_code_image': qr_data['qr_code_image'],
                'message': 'Scan QR code with your authenticator app'
            })
        
        elif method in ['email', 'sms']:
            if method == 'sms':
                if not phone_number:
                    return Response(
                        {'error': 'Phone number required for SMS method'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                settings_obj.phone_number = phone_number
                settings_obj.save()
            
            # Check rate limiting
            if TwoFactorService.is_rate_limited(user):
                return Response(
                    {'error': 'Too many requests. Please try again later.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            # Send OTP
            code_obj = TwoFactorService.send_otp(user, method=method, purpose='setup')
            
            return Response({
                'method': method,
                'message': f'Verification code sent to your {method}',
                'expires_in': 600
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
        
        # Enable 2FA
        settings_obj.is_enabled = True
        settings_obj.save()
        
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
                'message': '2FA not configured'
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
        
        # Disable 2FA
        settings_obj.is_enabled = False
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
            return Response(
                {'error': 'Account temporarily locked due to too many failed 2FA attempts. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
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
