"""Re-authentication code view."""

from __future__ import annotations

import logging

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.notification_utils import rate_limit_response, success_response

from ..permissions import IsEmailVerified
from ..services.reauth_service import send_reauth_code
from .constants import REAUTH_CODE_RATE

logger = logging.getLogger(__name__)


class ReauthCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        description=(
            "Email a one-time re-authentication code to the signed-in user's account email. Sensitive actions "
            "(such as creating an API token) take this code in their own request body. A new request replaces "
            "the previous code. The response never says where the code was sent."
        ),
        request=None,
        responses={
            202: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Code request accepted"),
            429: OpenApiResponse(description="Too many code requests"),
        },
    )
    @method_decorator(ratelimit(key="user", rate=REAUTH_CODE_RATE, method="POST", block=False))
    def post(self, request):
        if getattr(request, "limited", False):
            logger.warning(
                "Re-auth code request rate limited",
                extra={"event": "auth.reauth.rate_limited", "extra": {"user_id": request.user.id}},
            )
            return rate_limit_response("errors.reauth_rate_limited")

        send_reauth_code(request.user)
        return success_response({}, status_code=status.HTTP_202_ACCEPTED)
