"""Backward-compatible re-export of shared emailing task utilities."""

from emailing.tasks import register_email_template, send_email_task
from emailing.templates import (  # noqa: F401  (ensures templates register via emailing app)
    CIRCLE_INVITATION_TEMPLATE,
    CHILD_UPGRADE_TEMPLATE,
    EMAIL_VERIFICATION_TEMPLATE,
    PASSWORD_RESET_TEMPLATE,
)

__all__ = [
    'register_email_template',
    'send_email_task',
    'EMAIL_VERIFICATION_TEMPLATE',
    'PASSWORD_RESET_TEMPLATE',
    'CIRCLE_INVITATION_TEMPLATE',
    'CHILD_UPGRADE_TEMPLATE',
]
