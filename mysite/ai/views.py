"""In-app AI settings for circle admins: turn milestone suggestions on or off, test the provider, scan now.

Mounted under ``/api/users/circles/<circle_id>/`` with the other per-circle
admin APIs. JWT only, and only real circle admins: superusers act through
Django admin. The operator's URL, key and model are never returned or
accepted. While the operator hasn't configured AI, GET answers
``{available: false}`` and everything else is a 404.
"""

from __future__ import annotations

import dataclasses
import logging
import time

from django.http import Http404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from mysite.albums import milestones
from mysite.albums.tasks import scan_milestones
from mysite.albums.views import is_circle_admin
from mysite.audit import AuditEvent, log_audit_event
from mysite.circles.models import CircleMembership
from mysite.notification_utils import create_message, error_response, rate_limit_response

from . import client, prompts, scan
from .models import CircleAiSettings
from .providers import provider_config
from .serializers import AiSettingsUpdateSerializer

logger = logging.getLogger(__name__)

TEST_RATE_PER_USER = "10/h"
SCAN_RATE_PER_USER = "3/h"
# The test runs inside the web request: give up well before gunicorn's 60s worker timeout and nginx's
# 60s proxy read timeout, so the admin gets a ``timeout`` code instead of a 502/504.
TEST_TIMEOUT_SECONDS = 30


def require_ai_admin(user, circle_id):
    """404 outside the circle, 403 for members who aren't its admins."""
    if not CircleMembership.objects.filter(circle_id=circle_id, user=user).exists():
        raise Http404
    if not is_circle_admin(user, circle_id):
        raise PermissionDenied("Only circle admins can change AI settings.")


def require_provider():
    config = provider_config()
    if config is None:
        raise Http404
    return config


def _ai_error(code: str, status_code: int) -> Response:
    return error_response(code, [create_message(code)], status_code)


def _audit(action: str, user, circle_id: int, **metadata):
    log_audit_event(
        AuditEvent(
            action=action,
            actor_type="user",
            actor_id=str(user.pk),
            target_type="circle",
            target_id=str(circle_id),
            metadata=metadata,
        )
    )


def settings_payload(circle_id: int) -> dict:
    ai_settings = CircleAiSettings.objects.filter(circle_id=circle_id).first() or CircleAiSettings(circle_id=circle_id)
    return {
        "available": True,
        "enabled": ai_settings.enabled,
        "acknowledged_at": ai_settings.acknowledged_at,
        "last_run_at": ai_settings.last_run_at,
        "last_success_at": ai_settings.last_success_at,
        "last_error": ai_settings.last_error,
        "pending_count": milestones.pending_suggestions(circle_id).count(),
    }


class CircleAiSettingsView(APIView):
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="In-app AI settings",
        description="Whether the circle sends captions to the server operator's AI model for milestone "
        "suggestions, and how its last scan went. `{available: false}` (and nothing else) while the operator "
        "hasn't set AI up. Never includes the provider's URL, key or model. `last_error` is a fixed code. "
        "Circle admins only.",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="`{available, enabled, acknowledged_at, last_run_at, last_success_at, last_error, "
                "pending_count}`",
            ),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not a member of the circle"),
        },
    )
    def get(self, request, circle_id):
        require_ai_admin(request.user, circle_id)
        if provider_config() is None:
            return Response({"available": False})
        return Response(settings_payload(circle_id))

    @extend_schema(
        summary="Turn in-app AI on or off",
        description="Turning it on needs `acknowledge_data_sharing: true`: the admin accepts that the circle's "
        "captions go to the AI service the operator set up. Turning it off is always allowed. Any other field "
        "(e.g. a URL or model) is refused. Circle admins only.",
        request=AiSettingsUpdateSerializer,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="The settings, as GET returns them"),
            400: OpenApiResponse(description="Invalid fields, or `ai.acknowledgement_required`"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not a member of the circle, or AI isn't set up"),
        },
    )
    def put(self, request, circle_id):
        require_ai_admin(request.user, circle_id)
        require_provider()
        serializer = AiSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enabled = serializer.validated_data["enabled"]

        ai_settings, _ = CircleAiSettings.objects.get_or_create(circle_id=circle_id)
        if enabled and not ai_settings.enabled:
            if not serializer.validated_data["acknowledge_data_sharing"]:
                return _ai_error("ai.acknowledgement_required", status.HTTP_400_BAD_REQUEST)
            ai_settings.acknowledged_by = request.user
            ai_settings.acknowledged_at = timezone.now()
        if enabled != ai_settings.enabled:
            ai_settings.enabled = enabled
            ai_settings.updated_by = request.user
            # Only these, so a running scan's status written since the load isn't overwritten.
            ai_settings.save(
                update_fields=["enabled", "acknowledged_by", "acknowledged_at", "updated_by", "updated_at"]
            )
            # Field names only, never values.
            _audit("circle.ai_settings.update", request.user, circle_id, fields=["enabled"])
        return Response(settings_payload(circle_id))


class CircleAiSettingsTestView(APIView):
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Test the AI connection",
        description="Sends one made-up caption (never a real post) to the operator's AI model, with the real "
        "response format, and says whether a usable answer came back. `code` is `ok` or a fixed error code. "
        "Circle admins only.",
        request=None,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{ok, code, latency_ms}`"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not a member of the circle, or AI isn't set up"),
            429: OpenApiResponse(description="Too many tests"),
        },
    )
    @method_decorator(ratelimit(key="user", rate=TEST_RATE_PER_USER, method="POST", block=False))
    def post(self, request, circle_id):
        if getattr(request, "limited", False):
            return rate_limit_response("errors.rate_limit_later")
        require_ai_admin(request.user, circle_id)
        config = require_provider()
        config = dataclasses.replace(config, timeout_seconds=min(config.timeout_seconds, TEST_TIMEOUT_SECONDS))

        started = time.monotonic()
        code = client.OK
        try:
            client.classify_post(config, *prompts.TEST_POST)
        except client.AiError as exc:
            code = exc.code
        except client.InvalidOutput:
            code = client.BAD_RESPONSE
        latency_ms = round((time.monotonic() - started) * 1000)
        _audit("circle.ai_settings.test", request.user, circle_id, code=code, latency_ms=latency_ms)
        return Response({"ok": code == client.OK, "code": code, "latency_ms": latency_ms})


class CircleMilestoneScanView(APIView):
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Scan for milestones now",
        description="Queues an AI milestone scan of this circle's new posts, as the nightly scan does. "
        "Circle admins only, with AI turned on for the circle.",
        request=None,
        responses={
            202: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{queued: true}`"),
            400: OpenApiResponse(description="`ai.not_enabled`: AI is off for this circle"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not a member of the circle, or AI isn't set up"),
            409: OpenApiResponse(description="`ai.scan_running`: a scan is already running"),
            429: OpenApiResponse(description="Too many scans"),
        },
    )
    @method_decorator(ratelimit(key="user", rate=SCAN_RATE_PER_USER, method="POST", block=False))
    def post(self, request, circle_id):
        if getattr(request, "limited", False):
            return rate_limit_response("errors.rate_limit_later")
        require_ai_admin(request.user, circle_id)
        require_provider()
        if not CircleAiSettings.objects.filter(circle_id=circle_id, enabled=True).exists():
            return _ai_error("ai.not_enabled", status.HTTP_400_BAD_REQUEST)
        if scan.scan_running():
            return _ai_error("ai.scan_running", status.HTTP_409_CONFLICT)
        scan_milestones.delay(circle_id=circle_id)
        return Response({"queued": True}, status=status.HTTP_202_ACCEPTED)
