"""Permissions for the agent API."""

from rest_framework.permissions import BasePermission

from .models import CircleApiToken
from .principal import ApiTokenPrincipal


class IsApiToken(BasePermission):
    """The request was authenticated by an API token (never a user session)."""

    def has_permission(self, request, view):
        return isinstance(request.auth, CircleApiToken) and isinstance(request.user, ApiTokenPrincipal)


class CanSuggest(BasePermission):
    """The token was created with permission to propose milestones."""

    message = "This API token can't suggest milestones."

    def has_permission(self, request, view):
        return isinstance(request.auth, CircleApiToken) and request.auth.can_suggest
