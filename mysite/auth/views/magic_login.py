"""Magic link login views."""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.emails.tasks import send_email_task
from mysite.notification_utils import create_message, error_response, rate_limit_response, success_response
from mysite.users.serializers import UserSerializer

from ..serializers import MagicLoginRequestSerializer, MagicLoginVerifySerializer
from ..token_utils import (
    generate_partial_token,
    get_tokens_for_user,
    hash_magic_login_token,
    set_refresh_cookie,
)

logger = logging.getLogger(__name__)


class MagicLoginRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MagicLoginRequestSerializer

    @extend_schema(
        description='Request a magic login link to be sent via email.',
        request=MagicLoginRequestSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Magic login link email scheduled')},
    )
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def post(self, request):
        serializer = MagicLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get('user')

        if user:
            from ..models import MagicLoginToken
            from ..token_utils import get_client_ip

            token = uuid.uuid4().hex
            token_hash = hash_magic_login_token(token)

            MagicLoginToken.objects.create(
                user=user,
                token_hash=token_hash,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                expires_at=timezone.now() + timedelta(minutes=15)
            )

            base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
            magic_link = f"{base_url}/magic-login?{urlencode({'token': token})}"

            send_email_task.delay(
                to_email=user.email,
                template_id='users.magic.login',
                context={
                    'token': token,
                    'email': user.email,
                    'full_name': user.display_name,
                    'magic_link': magic_link,
                    'expires_in_minutes': 15,
                },
            )

        return success_response(
            {},
            messages=[create_message('notifications.auth.magic_link_sent')],
            status_code=status.HTTP_202_ACCEPTED
        )


class MagicLoginVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MagicLoginVerifySerializer

    @extend_schema(
        description='Verify a magic login token and authenticate the user.',
        request=MagicLoginVerifySerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Login successful with JWT tokens')},
    )
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def post(self, request):
        serializer = MagicLoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from ..models import MagicLoginToken, TwoFactorSettings
        from ..services.trusted_device_service import TrustedDeviceService
        from ..services.twofa_service import TwoFactorService

        token_value = serializer.validated_data['token']
        token_hash = hash_magic_login_token(token_value)

        try:
            magic_token = MagicLoginToken.objects.select_related('user').get(token_hash=token_hash)

            if not magic_token.is_valid():
                return error_response(
                    'magic_link_expired',
                    [create_message('errors.magic_link_expired')],
                    status.HTTP_400_BAD_REQUEST
                )

            magic_token.mark_as_used()
            user = magic_token.user

            if not user.is_active:
                return error_response(
                    'account_inactive',
                    [create_message('errors.account_inactive')],
                    status.HTTP_403_FORBIDDEN
                )

            try:
                twofa_settings = user.twofa_settings

                if twofa_settings.is_enabled:
                    if twofa_settings.is_locked():
                        return rate_limit_response('errors.account_locked_2fa')

                    device_token = TrustedDeviceService.get_device_id_from_request(request)
                    is_trusted, rotated_token = TrustedDeviceService.is_trusted_device(
                        user,
                        device_token,
                        request,
                    ) if device_token else (False, None)

                    if is_trusted:
                        tokens = get_tokens_for_user(user)
                        data = {
                            'user': UserSerializer(user).data,
                            'tokens': {'access': tokens['access']},
                            'trusted_device': True,
                        }
                        response = success_response(
                            data,
                            messages=[create_message('notifications.auth.magic_login_success')],
                            status_code=status.HTTP_200_OK
                        )
                        set_refresh_cookie(response, tokens['refresh'])
                        if rotated_token:
                            TrustedDeviceService.set_trusted_device_cookie(response, rotated_token)
                        return response

                    if TwoFactorService.is_rate_limited(user):
                        return rate_limit_response('errors.rate_limit_2fa')

                    if twofa_settings.preferred_method in ['email', 'sms']:
                        TwoFactorService.send_otp(
                            user,
                            method=twofa_settings.preferred_method,
                            purpose='login'
                        )

                    partial_token = generate_partial_token(user, request)
                    message_key = 'notifications.twofa.code_sent' if twofa_settings.preferred_method != 'totp' else 'notifications.twofa.enter_authenticator_code'
                    return success_response(
                        {
                            'requires_2fa': True,
                            'method': twofa_settings.preferred_method,
                            'partial_token': partial_token,
                        },
                        messages=[create_message(message_key, {'method': twofa_settings.preferred_method})]
                    )

            except TwoFactorSettings.DoesNotExist:
                pass

            tokens = get_tokens_for_user(user)
            data = {
                'user': UserSerializer(user).data,
                'tokens': {'access': tokens['access']},
            }
            response = success_response(
                data,
                messages=[create_message('notifications.auth.magic_login_success')],
                status_code=status.HTTP_200_OK
            )
            set_refresh_cookie(response, tokens['refresh'])
            return response

        except MagicLoginToken.DoesNotExist:
            return error_response(
                'magic_link_invalid',
                [create_message('errors.magic_link_invalid')],
                status.HTTP_400_BAD_REQUEST
            )
