"""Views handling 2FA recovery code generation and export."""

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.auth.models import TwoFactorAuditLog, TwoFactorSettings
from mysite.auth.permissions import IsEmailVerified
from mysite.auth.services.recovery_code_service import RecoveryCodeService
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.notification_utils import (
    create_message,
    error_response,
    success_response,
)


class RecoveryCodeGenerateView(APIView):
    """Generate new recovery codes"""
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
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
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    
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
