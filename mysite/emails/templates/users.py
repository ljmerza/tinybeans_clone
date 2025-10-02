from __future__ import annotations

from typing import Any, Tuple

from emails.tasks import register_email_template

EMAIL_VERIFICATION_TEMPLATE = 'users.email.verification'
PASSWORD_RESET_TEMPLATE = 'users.password.reset'
CIRCLE_INVITATION_TEMPLATE = 'users.circle.invitation'
CHILD_UPGRADE_TEMPLATE = 'users.child.upgrade'


def _verification_email(context: dict[str, Any]) -> Tuple[str, str]:
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


def _password_reset_email(context: dict[str, Any]) -> Tuple[str, str]:
    token = context['token']
    subject = 'Password reset instructions'
    reset_link = context.get('reset_link')
    expires_in_minutes = context.get('expires_in_minutes')
    username = context.get('username') or 'there'

    body_lines = [
        f"Hi {username},",
        'We received a request to reset your password.',
    ]

    if reset_link:
        if isinstance(expires_in_minutes, int) and expires_in_minutes > 0:
            expiry_notice = f'This secure link expires in {expires_in_minutes} minutes.'
        else:
            expiry_notice = 'This secure link expires soon.'

        body_lines.extend([
            'To keep your account safe, use the link below to choose a new password:',
            '',
            reset_link,
            '',
            expiry_notice,
            '',
            'Need to enter a code manually? Use this one-time token:',
            '',
            token,
        ])
    else:
        body_lines.extend([
            'Use the token below to set a new password:',
            '',
            token,
        ])

    body_lines.extend([
        '',
        'If you did not request a password reset, you can safely ignore this message.',
    ])
    return subject, '\n'.join(body_lines)


def _circle_invitation_email(context: dict[str, Any]) -> Tuple[str, str]:
    token = context['token']
    circle_name = context.get('circle_name', 'a circle')
    invited_by = context.get('invited_by', 'a circle admin')
    subject = f"You're invited to join {circle_name}"
    body_lines = [
        'Hi there,',
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


def _child_upgrade_email(context: dict[str, Any]) -> Tuple[str, str]:
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


register_email_template(EMAIL_VERIFICATION_TEMPLATE, _verification_email)
register_email_template(PASSWORD_RESET_TEMPLATE, _password_reset_email)
register_email_template(CIRCLE_INVITATION_TEMPLATE, _circle_invitation_email)
register_email_template(CHILD_UPGRADE_TEMPLATE, _child_upgrade_email)

__all__ = [
    'EMAIL_VERIFICATION_TEMPLATE',
    'PASSWORD_RESET_TEMPLATE',
    'CIRCLE_INVITATION_TEMPLATE',
    'CHILD_UPGRADE_TEMPLATE',
]
