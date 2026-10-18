"""Base view for the agent API: token-only auth, the kill switch, per-token throttling."""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import Http404
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView

from ..authentication import INVALID_TOKEN_MESSAGE, CircleApiTokenAuthentication
from ..models import CircleApiToken
from ..permissions import IsApiToken
from ..throttling import AgentReadThrottle

logger = logging.getLogger("mysite.agent_api")


class AgentAPIView(APIView):
    """Every agent endpoint. The circle comes only from ``request.auth.circle_id``.

    No view takes a circle id or slug, and none reads ``request.user`` (an
    ``ApiTokenPrincipal`` whose ``pk`` raises). Anything outside the token's
    circle is a 404.
    """

    authentication_classes = [CircleApiTokenAuthentication]
    permission_classes = [IsApiToken]
    throttle_classes = [AgentReadThrottle]

    def initial(self, request, *args, **kwargs):
        # Checked per request, before authentication, so turning it off costs no queries.
        if not settings.AGENT_API_ENABLED:
            raise Http404
        super().initial(request, *args, **kwargs)

    def permission_denied(self, request, message=None, code=None):
        # No (or a non-token) credential gets the same 401 body as a bad token.
        if request.authenticators and not request.successful_authenticator:
            raise AuthenticationFailed(INVALID_TOKEN_MESSAGE)
        super().permission_denied(request, message=message, code=code)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        # ``_auth`` rather than ``auth``: reading ``auth`` would run authentication when it hasn't run yet.
        token = getattr(request, "_auth", None)
        if isinstance(token, CircleApiToken):
            logger.info(
                "Agent API request",
                extra={
                    "event": "agent_api.access",
                    "extra": {
                        "token_id": str(token.id),
                        "circle_id": token.circle_id,
                        "view": type(self).__name__,
                        "status": response.status_code,
                    },
                },
            )
        return response
