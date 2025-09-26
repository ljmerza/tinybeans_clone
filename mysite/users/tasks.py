from __future__ import annotations

import logging
from typing import Any, Callable

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_TEMPLATE = 'users.email.verification'
PASSWORD_RESET_TEMPLATE = 'users.password.reset'
CIRCLE_INVITATION_TEMPLATE = 'users.circle.invitation'
CHILD_UPGRADE_TEMPLATE = 'users.child.upgrade'


def _verification_email(context: dict[str, Any]) -> tuple[str, str]:
    token = context['token']
    subject = 'Verify your Tinybeans-inspired account'
    body_lines = [
        f"Hi {context.get('username') or 'there'},",
        'Thanks for signing up! Please use the code below to verify your email address:',
        '',
        token,
        '',
        'Enter this code in the app to activate your account. If you did not create an account, you can ignore this email.',
    ]
    if context.get('verification_link'):
        body_lines.insert(3, f"Verification link: {context['verification_link']}")
    return subject, '\n'.join(body_lines)


def _password_reset_email(context: dict[str, Any]) -> tuple[str, str]:
    token = context['token']
    subject = 'Password reset instructions'
    body_lines = [
        'We received a request to reset your password.',
        'Use the token below to set a new password:',
        '',
        token,
        '',
        'If you did not request a password reset, you can safely ignore this message.',
    ]
    if context.get('reset_link'):
        body_lines.insert(3, f"Reset link: {context['reset_link']}")
    return subject, '\n'.join(body_lines)


def _circle_invitation_email(context: dict[str, Any]) -> tuple[str, str]:
    token = context['token']
    circle_name = context.get('circle_name', 'a circle')
    invited_by = context.get('invited_by', 'a circle admin')
    subject = f"You're invited to join {circle_name}"
    body_lines = [
        f"Hi there,",
        f"{invited_by} invited you to join the circle '{circle_name}'.",
        'Use the token below to accept the invitation and create your account:',
        '',
        token,
        '',
        'If you were not expecting this invitation, no action is required.',
    ]
    if context.get('invitation_link'):
        body_lines.insert(4, f"Accept invitation: {context['invitation_link']}")
    return subject, '\n'.join(body_lines)


def _child_upgrade_email(context: dict[str, Any]) -> tuple[str, str]:
    token = context['token']
    child_name = context.get('child_name', 'your child')
    circle_name = context.get('circle_name', 'your circle')
    subject = 'Upgrade to a full account'
    body_lines = [
        f"A guardian from '{circle_name}' invited you to upgrade {child_name}'s profile to a full account.",
        'Use the token below to finish setting up the account:',
        '',
        token,
        '',
        'If you do not wish to proceed, simply ignore this email.',
    ]
    if context.get('upgrade_link'):
        body_lines.insert(3, f"Complete upgrade: {context['upgrade_link']}")
    return subject, '\n'.join(body_lines)


_TEMPLATE_REGISTRY: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    EMAIL_VERIFICATION_TEMPLATE: _verification_email,
    PASSWORD_RESET_TEMPLATE: _password_reset_email,
    CIRCLE_INVITATION_TEMPLATE: _circle_invitation_email,
    CHILD_UPGRADE_TEMPLATE: _child_upgrade_email,
}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_email_task(self, *, to_email: str, template_id: str, context: dict[str, Any]) -> None:
    renderer = _TEMPLATE_REGISTRY.get(template_id)
    if renderer is None:
        logger.error('Unknown email template %s; dropping email', template_id)
        return

    subject, body = renderer(context)
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
        logger.info('Dispatched %s email to %s', template_id, to_email)
    except Exception as exc:
        logger.warning('Email send failed for %s (%s): %s', template_id, to_email, exc)
        raise
