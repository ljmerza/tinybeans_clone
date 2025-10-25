"""Views for first-circle onboarding workflows."""
from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from mysite.notification_utils import create_message, success_response
from mysite.auth.permissions import IsEmailVerified

from ..models import CircleMembership, CircleOnboardingStatus


def _serialize_onboarding_payload(user) -> dict[str, object]:
    memberships_count = CircleMembership.objects.filter(user=user).count()
    updated_at = user.circle_onboarding_updated_at
    return {
        "status": user.circle_onboarding_status,
        "needs_circle_onboarding": user.needs_circle_onboarding,
        "memberships_count": memberships_count,
        "email_verified": user.email_verified,
        "email": user.email,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


class CircleOnboardingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        description="Retrieve the current onboarding status for the authenticated user.",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Current onboarding status and metadata.",
            )
        },
    )
    def get(self, request):
        return success_response(_serialize_onboarding_payload(request.user))


class CircleOnboardingSkipView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        description="Dismiss the circle onboarding flow for the current user.",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Updated onboarding state after dismissal.",
            )
        },
    )
    def post(self, request):
        user = request.user
        status_changed = False
        if user.circle_onboarding_status != CircleOnboardingStatus.COMPLETED:
            status_changed = user.set_circle_onboarding_status(
                CircleOnboardingStatus.DISMISSED,
                save=True,
            )
            # Ensure updated_at always reflects the latest review even if status unchanged
            if not status_changed:
                user.circle_onboarding_updated_at = timezone.now()
                user.save(update_fields=["circle_onboarding_updated_at"])

        payload = _serialize_onboarding_payload(user)
        messages = None
        if status_changed:
            messages = [create_message("notifications.circle.onboarding_skipped")]
        return success_response(payload, messages=messages)
