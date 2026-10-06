"""Password lifecycle views."""

from __future__ import annotations

import logging
import math
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from mysite import project_logging
from mysite.audit import AuditEvent, log_audit_event, log_security_event
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import PASSWORD_CHANGED_TEMPLATE, PASSWORD_RESET_TEMPLATE
from mysite.notification_utils import create_message, error_response, rate_limit_response, success_response
from mysite.users.models import User

from ..permissions import IsEmailVerified
from ..serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from ..token_utils import (
    TOKEN_TTL_SECONDS,
    get_client_ip,
    get_tokens_for_user,
    pop_token,
    revoke_refresh_tokens,
    set_refresh_cookie,
    store_token,
)
from .constants import PASSWORD_CHANGE_RATE, PASSWORD_RESET_CONFIRM_RATE, PASSWORD_RESET_RATE, body_field_key

logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        description="Initiate the password reset flow for a user by email.",
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Password reset email scheduled")},
    )
    @method_decorator(
        ratelimit(
            key="ip",
            rate=PASSWORD_RESET_RATE,
            method="POST",
            block=False,
        )
    )
    @method_decorator(
        ratelimit(
            key=body_field_key("email"),
            rate=PASSWORD_RESET_RATE,
            method="POST",
            block=False,
        )
    )
    def post(self, request):
        if getattr(request, "limited", False):
            logger.warning(
                "Password reset request rate limited",
                extra={"event": "auth.password_reset.rate_limited"},
            )
            return rate_limit_response("errors.rate_limit")
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if user:
            token = store_token(
                "password-reset",
                {"user_id": user.id, "issued_at": timezone.now().isoformat()},
                ttl=TOKEN_TTL_SECONDS,
            )
            base_url = (
                getattr(settings, "ACCOUNT_FRONTEND_BASE_URL", "http://localhost:3000") or "http://localhost:3000"
            ).rstrip("/")
            reset_link = f"{base_url}/password/reset/confirm?{urlencode({'token': token})}"
            expires_in_minutes = max(1, math.ceil(TOKEN_TTL_SECONDS / 60))
            send_email_task.delay(
                to_email=user.email,
                template_id=PASSWORD_RESET_TEMPLATE,
                context={
                    "token": token,
                    "email": user.email,
                    "full_name": user.display_name,
                    "reset_link": reset_link,
                    "expires_in_minutes": expires_in_minutes,
                },
            )
            with project_logging.log_context(user_id=user.id):
                logger.info(
                    "Password reset email scheduled",
                    extra={
                        "event": "auth.password_reset.requested",
                        "extra": {"user_id": user.id},
                    },
                )
                log_security_event(
                    "user.password_reset.requested",
                    actor_id=str(user.id),
                    status="pending",
                    severity="warning",
                )
        else:
            logger.info(
                "Password reset requested for unknown identifier",
                extra={"event": "auth.password_reset.unknown_user"},
            )
        return success_response(
            {}, messages=[create_message("notifications.auth.password_reset")], status_code=status.HTTP_202_ACCEPTED
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        description=(
            "Complete a password reset using a valid reset token. Runs the configured password validators "
            "(a rejected password leaves the token usable). On success every refresh token is revoked, "
            "password login is enabled (Google-linked accounts become `hybrid`) and a security notice is "
            "emailed. The user is not signed in; they log in with the new password."
        ),
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Password reset completed")},
    )
    @method_decorator(
        ratelimit(
            key="ip",
            rate=PASSWORD_RESET_CONFIRM_RATE,
            method="POST",
            block=False,
        )
    )
    @method_decorator(
        ratelimit(
            key=body_field_key("token"),
            rate=PASSWORD_RESET_CONFIRM_RATE,
            method="POST",
            block=False,
        )
    )
    def post(self, request):
        if getattr(request, "limited", False):
            logger.warning(
                "Password reset confirmation rate limited",
                extra={"event": "auth.password_reset_confirm.rate_limited"},
            )
            return rate_limit_response("errors.rate_limit")
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token("password-reset", serializer.validated_data["token"])
        if not payload:
            logger.warning(
                "Password reset token invalid or expired",
                extra={"event": "auth.password_reset.invalid_token"},
            )
            return error_response(
                "invalid_token", [create_message("errors.token_invalid_expired")], status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(id=payload["user_id"]).first()
        if not user:
            logger.warning(
                "Password reset target user missing",
                extra={
                    "event": "auth.password_reset.user_missing",
                    "extra": {"user_id": payload.get("user_id")},
                },
            )
            return error_response(
                "user_not_found", [create_message("errors.user_not_found")], status.HTTP_404_NOT_FOUND
            )
        with transaction.atomic():
            user.set_password(serializer.validated_data["password"])
            user.save(update_fields=["password", *_enable_password_login(user)])
            revoked = revoke_refresh_tokens(user)

        _send_password_changed_email(user, ip_address=get_client_ip(request), changed_at=timezone.now(), reset=True)

        with project_logging.log_context(user_id=user.id):
            logger.info(
                "Password reset completed",
                extra={
                    "event": "auth.password_reset.success",
                    "extra": {"user_id": user.id, "revoked_refresh_tokens": revoked},
                },
            )
            log_audit_event(
                AuditEvent(
                    action="user.password_reset",
                    actor_id=str(user.id),
                    target_id=str(user.id),
                    status="success",
                    severity="warning",
                    metadata={"revoked_refresh_tokens": revoked},
                )
            )
            log_security_event(
                "user.password_reset.success",
                actor_id=str(user.id),
                status="success",
                severity="warning",
            )
        return success_response({}, messages=[create_message("notifications.auth.password_updated")])


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        description=(
            "Change the authenticated user's password. Requires the current password and runs the "
            "configured password validators. Every existing refresh token is revoked (other devices are "
            "signed out once their access token expires); this device gets a new access token in the body "
            "and a new refresh token in the HTTP-only cookie. A security notice is emailed to the user. "
            "Accounts without a usable password get 400 `password_not_set` and should use the reset flow."
        ),
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, description="Password changed successfully with new tokens"
            ),
            400: OpenApiResponse(description="Validation failed, or the account has no password to change"),
            429: OpenApiResponse(description="Too many password change attempts"),
        },
    )
    @method_decorator(ratelimit(key="ip", rate=PASSWORD_CHANGE_RATE, method="POST", block=False))
    @method_decorator(ratelimit(key="user", rate=PASSWORD_CHANGE_RATE, method="POST", block=False))
    def post(self, request):
        user = request.user
        if getattr(request, "limited", False):
            logger.warning(
                "Password change rate limited",
                extra={"event": "auth.password_change.rate_limited", "extra": {"user_id": user.id}},
            )
            log_security_event(
                "user.password_change.rate_limited",
                actor_id=str(user.id),
                status="denied",
                severity="warning",
            )
            return rate_limit_response("errors.password_change_rate_limit")

        if not user.has_usable_password():
            # Google / magic-link / imported accounts. Setting a first password
            # without proof of the current one would let a stolen session mint a
            # permanent credential, so they go through the emailed reset link.
            return error_response(
                "password_not_set", [create_message("errors.auth.password_not_set")], status.HTTP_400_BAD_REQUEST
            )

        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            if "current_password" in serializer.errors:
                log_security_event(
                    "user.password_change.failed",
                    actor_id=str(user.id),
                    status="denied",
                    severity="warning",
                    metadata={"reason": "invalid_current_password"},
                )
            raise ValidationError(serializer.errors)

        with transaction.atomic():
            user.set_password(serializer.validated_data["password"])
            user.save(update_fields=["password"])
            revoked = revoke_refresh_tokens(user)
            tokens = get_tokens_for_user(user)

        changed_at = timezone.now()
        _send_password_changed_email(user, ip_address=get_client_ip(request), changed_at=changed_at)

        with project_logging.log_context(user_id=user.id):
            logger.info(
                "Password changed by authenticated user",
                extra={
                    "event": "auth.password_change.success",
                    "extra": {"user_id": user.id, "revoked_refresh_tokens": revoked},
                },
            )
            log_audit_event(
                AuditEvent(
                    action="user.password_change",
                    actor_id=str(user.id),
                    target_id=str(user.id),
                    status="success",
                    severity="info",
                    metadata={"revoked_refresh_tokens": revoked},
                )
            )
            log_security_event(
                "user.password_change.success",
                actor_id=str(user.id),
                status="success",
                severity="info",
            )

        data = {"tokens": {"access": tokens["access"]}}
        response = success_response(
            data, messages=[create_message("notifications.auth.password_updated")], status_code=status.HTTP_200_OK
        )
        set_refresh_cookie(response, tokens["refresh"])
        return response


def _enable_password_login(user: User) -> list[str]:
    """Let an account that now has a password sign in with it.

    Google and Apple sign-ups start with ``password_login_enabled=False``, which
    also blocks unlinking them. Returns the fields changed, for ``save()``.
    """
    changed = []
    if not user.password_login_enabled:
        user.password_login_enabled = True
        changed.append("password_login_enabled")
    if (user.google_id or user.apple_id) and user.auth_provider != "hybrid":
        user.auth_provider = "hybrid"
        changed.append("auth_provider")
    return changed


def _send_password_changed_email(user: User, *, ip_address: str, changed_at, reset: bool = False) -> None:
    """Queue the "your password was changed/reset" notice; never fail the request over it."""
    base_url = (
        getattr(settings, "ACCOUNT_FRONTEND_BASE_URL", "http://localhost:3000") or "http://localhost:3000"
    ).rstrip("/")
    try:
        send_email_task.delay(
            to_email=user.email,
            template_id=PASSWORD_CHANGED_TEMPLATE,
            context={
                "email": user.email,
                "full_name": user.display_name,
                "changed_at": changed_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "ip_address": ip_address,
                "reset_link": f"{base_url}/password/reset/request",
                "was_reset": reset,
            },
        )
    except Exception:
        logger.exception(
            "Failed to queue password changed email",
            extra={"event": "auth.password_change.email_failed", "extra": {"user_id": user.id}},
        )
