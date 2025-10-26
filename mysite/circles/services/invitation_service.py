"""Shared business logic for circle invitations."""
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from mysite.auth.token_utils import TOKEN_TTL_SECONDS, store_token
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import CIRCLE_INVITATION_TEMPLATE
from mysite.users.models import UserRole
from ..models import Circle, CircleMembership


def check_admin_permission(user, circle: Circle) -> None:
    """
    Check if user is an admin of the given circle.
    Raises PermissionDenied if not.
    """
    membership = CircleMembership.objects.filter(circle=circle, user=user).first()
    if not membership or membership.role != UserRole.CIRCLE_ADMIN:
        raise PermissionDenied(_('Only circle admins can manage invitations'))


def build_invitation_link(token: str) -> str:
    """Build the frontend invitation acceptance link with the given token."""
    base_url = getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000'
    base_url = base_url.rstrip('/')
    return f"{base_url}/invitations/accept?token={token}"


def create_invitation_token(invitation, existing_user: bool = None) -> str:
    """
    Create and store a token for the given invitation.
    Returns the token string.
    """
    if existing_user is None:
        existing_user = bool(invitation.invited_user_id)

    token = store_token(
        'circle-invite',
        {
            'invitation_id': str(invitation.id),
            'circle_id': invitation.circle_id,
            'email': invitation.email,
            'role': invitation.role,
            'issued_at': timezone.now().isoformat(),
            'existing_user': existing_user,
            'invited_user_id': invitation.invited_user_id,
        },
        ttl=TOKEN_TTL_SECONDS,
    )
    return token


def send_invitation_email(invitation, invited_by_name: str, token: str = None) -> str:
    """
    Send invitation email to the invitee.
    If token is not provided, a new one will be created.
    Returns the token that was used.
    """
    if token is None:
        token = create_invitation_token(invitation)

    invitation_link = build_invitation_link(token)

    send_email_task.delay(
        to_email=invitation.email,
        template_id=CIRCLE_INVITATION_TEMPLATE,
        context={
            'token': token,
            'email': invitation.email,
            'circle_name': invitation.circle.name,
            'invited_by': invited_by_name,
            'invitation_link': invitation_link,
        },
    )
    return token
