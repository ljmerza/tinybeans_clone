"""Service layer entry points for the email app."""

from .email_dispatch import EmailDispatchService, EmailServiceError, UnknownEmailTemplateError, email_dispatch_service

__all__ = [
    'EmailDispatchService',
    'EmailServiceError',
    'UnknownEmailTemplateError',
    'email_dispatch_service',
]
