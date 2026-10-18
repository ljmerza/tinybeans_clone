"""Token management for circle admins: list, create (with an emailed re-auth code) and revoke.

Mounted under ``/api/users/circles/<circle_id>/api-tokens/`` with the other
per-circle admin APIs. JWT only, and only real circle admins: superusers act
through Django admin.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from mysite.albums.views import is_circle_admin
from mysite.auth.services.reauth_service import verify_reauth
from mysite.notification_utils import create_message, error_response, rate_limit_response

from .. import services
from ..models import CircleApiToken
from ..serializers import ApiTokenCreateSerializer, ApiTokenSerializer

logger = logging.getLogger(__name__)

CREATE_RATE_PER_USER = "5/15m"
CREATE_RATE_PER_IP = "20/15m"


def require_token_admin(user, circle_id):
    if not is_circle_admin(user, circle_id):
        raise PermissionDenied("Only circle admins can manage API tokens.")


class CircleApiTokenListView(APIView):
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="API tokens",
        description="The circle's API tokens, newest first, including revoked and expired ones. Never includes a "
        "token's hash or plaintext. `agent_api_enabled` is false while the server operator has the agent API "
        "turned off. Circle admins only.",
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{agent_api_enabled, tokens: [...]}`"),
            403: OpenApiResponse(description="Not an admin of the circle"),
        },
    )
    def get(self, request, circle_id):
        require_token_admin(request.user, circle_id)
        tokens = CircleApiToken.objects.filter(circle_id=circle_id).select_related("created_by")
        return Response(
            {
                "agent_api_enabled": settings.AGENT_API_ENABLED,
                "tokens": ApiTokenSerializer(tokens, many=True).data,
            }
        )

    @extend_schema(
        summary="Create an API token",
        description="Creates a token that can read this circle through the agent API and, with `can_suggest`, "
        "propose milestones. Needs `code`, the re-authentication code emailed by `POST /api/auth/reauth/code/`. "
        "The response is the only time the plaintext token is shown. `expires_at` is null for no expiry, else at "
        "least an hour away. Name, `can_suggest` and expiry can't be changed later. Every admin of the circle "
        "is emailed. Circle admins only.",
        request=ApiTokenCreateSerializer,
        responses={
            201: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{token, plaintext}`"),
            400: OpenApiResponse(description="Invalid fields, wrong or missing code, or the circle's token limit"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            429: OpenApiResponse(description="Too many attempts"),
        },
    )
    @method_decorator(ratelimit(key="ip", rate=CREATE_RATE_PER_IP, method="POST", block=False))
    @method_decorator(ratelimit(key="user", rate=CREATE_RATE_PER_USER, method="POST", block=False))
    def post(self, request, circle_id):
        if getattr(request, "limited", False):
            logger.warning(
                "API token creation rate limited",
                extra={"event": "agent_api.token_create.rate_limited", "extra": {"user_id": request.user.id}},
            )
            return rate_limit_response("errors.rate_limit")
        require_token_admin(request.user, circle_id)

        # Validate first, so a typo doesn't use up the emailed code.
        serializer = ApiTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if services.at_token_limit(circle_id):
            return self._limit_response()
        if not verify_reauth(request.user, data["code"]):
            raise ValidationError({"code": {"i18n_key": "errors.reauth_invalid_code"}})

        try:
            token, plaintext = services.create_token(
                circle_id=circle_id,
                user=request.user,
                name=data["name"],
                can_suggest=data["can_suggest"],
                expires_at=data["expires_at"],
            )
        except services.TokenLimitReached:
            return self._limit_response()
        response = Response(
            {"token": ApiTokenSerializer(token).data, "plaintext": plaintext}, status=status.HTTP_201_CREATED
        )
        response["Cache-Control"] = "no-store"
        return response

    @staticmethod
    def _limit_response():
        return error_response(
            "api_token_limit",
            [create_message("errors.api_token_limit", {"max": settings.AGENT_API_MAX_TOKENS_PER_CIRCLE})],
            status.HTTP_400_BAD_REQUEST,
        )


class CircleApiTokenDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Revoke an API token",
        description="Revokes the token at once; revoking twice is a no-op. Any admin of the circle can revoke any "
        "of its tokens. Circle admins only.",
        responses={
            204: OpenApiResponse(description="Revoked"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="No such token in this circle"),
        },
    )
    def delete(self, request, circle_id, token_id):
        require_token_admin(request.user, circle_id)
        token = get_object_or_404(CircleApiToken, pk=token_id, circle_id=circle_id)
        services.revoke_token(token, by_user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
