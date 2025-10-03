"""Template identifiers and metadata for email rendering."""
from __future__ import annotations

EMAIL_VERIFICATION_TEMPLATE = 'users.email.verification'
PASSWORD_RESET_TEMPLATE = 'users.password.reset'
CIRCLE_INVITATION_TEMPLATE = 'users.circle.invitation'
CHILD_UPGRADE_TEMPLATE = 'users.child.upgrade'

# Mapping of template IDs to Django template filenames within `email_templates/`.
EMAIL_TEMPLATE_FILES = {
    EMAIL_VERIFICATION_TEMPLATE: 'verification.email.html',
    PASSWORD_RESET_TEMPLATE: 'password_reset.email.html',
    CIRCLE_INVITATION_TEMPLATE: 'circle_invitation.email.html',
    CHILD_UPGRADE_TEMPLATE: 'child_upgrade.email.html',
}

__all__ = [
    'EMAIL_VERIFICATION_TEMPLATE',
    'PASSWORD_RESET_TEMPLATE',
    'CIRCLE_INVITATION_TEMPLATE',
    'CHILD_UPGRADE_TEMPLATE',
    'EMAIL_TEMPLATE_FILES',
]
