"""Template identifiers and metadata for email rendering."""
from __future__ import annotations

EMAIL_VERIFICATION_TEMPLATE = 'users.email.verification'
PASSWORD_RESET_TEMPLATE = 'users.password.reset'
CIRCLE_INVITATION_TEMPLATE = 'users.circle.invitation'
CIRCLE_INVITATION_REMINDER_TEMPLATE = 'users.circle.invitation_reminder'
CIRCLE_INVITATION_ACCEPTED_TEMPLATE = 'users.circle.invitation_accepted'
CHILD_UPGRADE_TEMPLATE = 'users.child.upgrade'
MAGIC_LOGIN_TEMPLATE = 'users.magic.login'

# 2FA-related templates
TWOFA_CODE_TEMPLATE = 'twofa.code'
TWOFA_ENABLED_TEMPLATE = 'twofa.enabled'
TWOFA_DISABLED_TEMPLATE = 'twofa.disabled'
TWOFA_TRUSTED_DEVICE_ADDED_TEMPLATE = 'twofa.trusted_device_added'
TWOFA_RECOVERY_CODE_USED_TEMPLATE = 'twofa.recovery_code_used'

# Mapping of template IDs to Django template filenames within `email_templates/`.
EMAIL_TEMPLATE_FILES = {
    EMAIL_VERIFICATION_TEMPLATE: 'verification.email.html',
    PASSWORD_RESET_TEMPLATE: 'password_reset.email.html',
    CIRCLE_INVITATION_TEMPLATE: 'circle_invitation.email.html',
    CIRCLE_INVITATION_REMINDER_TEMPLATE: 'circle_invitation_reminder.email.html',
    CIRCLE_INVITATION_ACCEPTED_TEMPLATE: 'circle_invitation_accepted.email.html',
    CHILD_UPGRADE_TEMPLATE: 'child_upgrade.email.html',
    MAGIC_LOGIN_TEMPLATE: 'magic_login.email.html',
    TWOFA_CODE_TEMPLATE: 'twofa_code.email.html',
    TWOFA_ENABLED_TEMPLATE: 'twofa_enabled.email.html',
    TWOFA_DISABLED_TEMPLATE: 'twofa_disabled.email.html',
    TWOFA_TRUSTED_DEVICE_ADDED_TEMPLATE: 'trusted_device_added.email.html',
    TWOFA_RECOVERY_CODE_USED_TEMPLATE: 'recovery_code_used.email.html',
}

__all__ = [
    'EMAIL_VERIFICATION_TEMPLATE',
    'PASSWORD_RESET_TEMPLATE',
    'CIRCLE_INVITATION_TEMPLATE',
    'CHILD_UPGRADE_TEMPLATE',
    'MAGIC_LOGIN_TEMPLATE',
    'TWOFA_CODE_TEMPLATE',
    'TWOFA_ENABLED_TEMPLATE',
    'TWOFA_DISABLED_TEMPLATE',
    'TWOFA_TRUSTED_DEVICE_ADDED_TEMPLATE',
    'TWOFA_RECOVERY_CODE_USED_TEMPLATE',
    'EMAIL_TEMPLATE_FILES',
]
