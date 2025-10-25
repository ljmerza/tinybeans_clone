"""Public interface for the users.serializers package."""
from __future__ import annotations

from typing import Any, Set

from .children import (
    ChildProfileSerializer,
    ChildProfileUpgradeConfirmSerializer,
    ChildProfileUpgradeRequestSerializer,
)
from .core import CircleSerializer, PublicUserSerializer, UserSerializer
from .pets import PetProfileSerializer, PetProfileCreateSerializer
from .profile import EmailPreferencesSerializer, UserProfileSerializer

_CIRCLE_EXPORTS: Set[str] = {
    'CircleCreateSerializer',
    'CircleInvitationFinalizeSerializer',
    'CircleInvitationOnboardingStartSerializer',
    'CircleInvitationCreateSerializer',
    'CircleInvitationResponseSerializer',
    'CircleInvitationSerializer',
    'CircleMemberAddSerializer',
    'CircleMemberSerializer',
    'CircleMembershipSerializer',
}


def __getattr__(name: str) -> Any:
    if name in _CIRCLE_EXPORTS:
        # Import lazily to avoid a circular dependency with mysite.circles.serializers.
        from mysite.circles import serializers as circle_serializers

        attr = getattr(circle_serializers, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _CIRCLE_EXPORTS)

__all__ = [
    'ChildProfileSerializer',
    'ChildProfileUpgradeConfirmSerializer',
    'ChildProfileUpgradeRequestSerializer',
    'CircleCreateSerializer',
    'CircleInvitationOnboardingStartSerializer',
    'CircleInvitationFinalizeSerializer',
    'CircleInvitationCreateSerializer',
    'CircleInvitationResponseSerializer',
    'CircleInvitationSerializer',
    'CircleMemberAddSerializer',
    'CircleMemberSerializer',
    'CircleMembershipSerializer',
    'CircleSerializer',
    'PublicUserSerializer',
    'UserSerializer',
    'PetProfileSerializer',
    'PetProfileCreateSerializer',
    'EmailPreferencesSerializer',
    'UserProfileSerializer',
]
