"""Notification delivery setup: which channels exist, the SMS phone, and push devices."""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite import project_logging
from mysite.auth.permissions import IsEmailVerified
from mysite.messaging.tasks import send_sms_async
from mysite.notification_utils import create_message, error_response, rate_limit_response, success_response

from ..models import NotificationPhone, PushSubscription, UserNotificationPreferences
from ..serializers.notification_channels import (
    NotificationPhoneSerializer,
    NotificationPhoneVerifySerializer,
    PushSubscriptionSerializer,
    PushUnsubscribeSerializer,
)

logger = logging.getLogger(__name__)


def _phone_code_rate(group, request):
    return settings.NOTIFICATION_PHONE_CODE_RATELIMIT


def channels_payload(user) -> dict:
    """What the notification settings page needs to offer each channel."""
    phone = NotificationPhone.objects.filter(user=user).first()
    push_available = settings.NOTIFICATIONS_PUSH_ENABLED
    return {
        "sms_available": settings.NOTIFICATIONS_SMS_ENABLED,
        "phone_number": phone.phone_number if phone else None,
        "phone_verified": bool(phone and phone.is_verified),
        "phone_verification_pending": bool(phone and not phone.is_verified and phone.is_pending),
        "push_available": push_available,
        "vapid_public_key": settings.VAPID_PUBLIC_KEY if push_available else "",
        "push_device_count": PushSubscription.objects.filter(user=user).count(),
    }


def _sms_unavailable_response():
    return error_response(
        "notification_channel_unavailable",
        [create_message("errors.notification_channel_unavailable")],
        status.HTTP_400_BAD_REQUEST,
    )


class NotificationChannelsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        description="Which notification channels the server offers, the user's SMS phone status, "
        "the VAPID public key for web push, and how many devices are subscribed.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def get(self, request):
        return success_response(channels_payload(request.user))


class NotificationPhoneView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = NotificationPhoneSerializer

    @extend_schema(
        description="Save the phone number notification texts go to and text it a 6-digit code. "
        "The number gets no notifications until the code is confirmed.",
        request=NotificationPhoneSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    @method_decorator(ratelimit(key="user", rate=_phone_code_rate, method="POST", block=False))
    def post(self, request):
        if not settings.NOTIFICATIONS_SMS_ENABLED:
            return _sms_unavailable_response()
        if getattr(request, "limited", False):
            return rate_limit_response("errors.rate_limit")
        serializer = NotificationPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        number = serializer.validated_data["phone_number"]

        phone, created = NotificationPhone.objects.get_or_create(user=request.user, defaults={"phone_number": number})
        if not created and phone.is_verified and phone.phone_number == number:
            # Already confirmed; don't pay for another text.
            return success_response(channels_payload(request.user))
        if phone.phone_number != number:
            phone.phone_number = number
            phone.verified_at = None
        code = phone.issue_code()
        phone.save()
        send_sms_async.delay(number, f"Your Circles code for notification texts is {code}. It expires in 10 minutes.")
        with project_logging.log_context(user_id=request.user.id):
            logger.info(
                "Notification phone verification code sent",
                extra={"event": "users.notification_phone.code_sent", "extra": {"phone_last4": number[-4:]}},
            )
        return success_response(
            channels_payload(request.user),
            messages=[create_message("notifications.notification_phone.code_sent")],
        )

    @extend_schema(
        description="Remove the notification phone and stop texting notifications.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def delete(self, request):
        NotificationPhone.objects.filter(user=request.user).delete()
        # No number left to text, so don't leave the switch looking on.
        UserNotificationPreferences.objects.filter(user=request.user).update(sms_enabled=False)
        return success_response(
            channels_payload(request.user),
            messages=[create_message("notifications.notification_phone.removed")],
        )


class NotificationPhoneVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = NotificationPhoneVerifySerializer

    @extend_schema(
        description="Confirm the notification phone with the texted code.",
        request=NotificationPhoneVerifySerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def post(self, request):
        if not settings.NOTIFICATIONS_SMS_ENABLED:
            return _sms_unavailable_response()
        serializer = NotificationPhoneVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = NotificationPhone.objects.filter(user=request.user).first()
        if phone is None or not phone.check_code(serializer.validated_data["code"]):
            return error_response(
                "invalid_verification_code",
                [create_message("errors.notification_phone_code_invalid")],
                status.HTTP_400_BAD_REQUEST,
            )
        with project_logging.log_context(user_id=request.user.id):
            logger.info("Notification phone verified", extra={"event": "users.notification_phone.verified"})
        return success_response(
            channels_payload(request.user),
            messages=[create_message("notifications.notification_phone.verified")],
        )


class PushSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = PushSubscriptionSerializer

    @extend_schema(
        description="Save this browser's push subscription (the browser's PushSubscription.toJSON()). "
        "A subscription already saved for another account moves to this one.",
        request=PushSubscriptionSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not settings.NOTIFICATIONS_PUSH_ENABLED:
            return error_response(
                "notification_channel_unavailable",
                [create_message("errors.notification_channel_unavailable")],
                status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "user": request.user,
                "p256dh": data["keys"]["p256dh"],
                "auth": data["keys"]["auth"],
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )
        with project_logging.log_context(user_id=request.user.id):
            logger.info("Push subscription saved", extra={"event": "users.push_subscription.saved"})
        return success_response(channels_payload(request.user))

    @extend_schema(
        description="Remove this browser's push subscription.",
        request=PushUnsubscribeSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def delete(self, request):
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.filter(user=request.user, endpoint=serializer.validated_data["endpoint"]).delete()
        return success_response(channels_payload(request.user))
