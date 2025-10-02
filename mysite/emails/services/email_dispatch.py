"""Service responsible for orchestrating email delivery."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings
from django.core.mail import send_mail

from emails.domain import EmailContent, EmailTemplate, TemplateRenderer
from emails.mailers import MailerConfigurationError, MailerSendError, send_via_mailjet
from emails.repositories import EmailTemplateRepository, InMemoryEmailTemplateRepository

logger = logging.getLogger(__name__)


class EmailServiceError(RuntimeError):
    """Base exception for email service issues."""


class UnknownEmailTemplateError(EmailServiceError):
    """Raised when a requested template is not registered."""


@dataclass
class EmailTransport:
    """Handles the actual dispatching of rendered email content."""

    def send(self, *, to_email: str, template_id: str, content: EmailContent) -> None:
        try:
            if getattr(settings, 'MAILJET_ENABLED', False):
                try:
                    send_via_mailjet(
                        to_email=to_email,
                        subject=content.subject,
                        body=content.body,
                        template_id=template_id,
                    )
                    return
                except MailerConfigurationError:
                    send_mail(
                        content.subject,
                        content.body,
                        settings.DEFAULT_FROM_EMAIL,
                        [to_email],
                        fail_silently=False,
                    )
                except MailerSendError:
                    # Propagate Mailjet errors so Celery can retry
                    raise
            else:
                send_mail(
                    content.subject,
                    content.body,
                    settings.DEFAULT_FROM_EMAIL,
                    [to_email],
                    fail_silently=False,
                )
        except Exception as exc:
            logger.warning('Email send failed for %s (%s): %s', template_id, to_email, exc)
            raise


class EmailDispatchService:
    """Coordinates template lookup, rendering, and dispatching."""

    def __init__(
        self,
        *,
        template_repository: EmailTemplateRepository,
        transport: EmailTransport,
        service_logger: logging.Logger | None = None,
    ) -> None:
        self._templates = template_repository
        self._transport = transport
        self._logger = service_logger or logger

    def register_template(self, template_id: str, renderer: TemplateRenderer) -> None:
        template = EmailTemplate(template_id=template_id, renderer=renderer)
        self._templates.save(template)

    def clear_templates(self) -> None:
        self._templates.clear()

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        return self._templates.get(template_id)

    def list_template_ids(self) -> list[str]:
        if hasattr(self._templates, 'list_ids'):
            return self._templates.list_ids()  # type: ignore[attr-defined]
        raise NotImplementedError('Template repository does not support listing templates')

    def send_email(self, *, to_email: str, template_id: str, context: dict[str, Any]) -> bool:
        template = self._templates.get(template_id)
        if template is None:
            self._logger.error('Unknown email template %s; dropping email', template_id)
            return False

        content = template.render(context)
        self._transport.send(to_email=to_email, template_id=template_id, content=content)
        self._logger.info('Dispatched %s email to %s', template_id, to_email)
        return True


# Default service instance used within the process
_template_repository = InMemoryEmailTemplateRepository()
_transport = EmailTransport()
email_dispatch_service = EmailDispatchService(
    template_repository=_template_repository,
    transport=_transport,
    service_logger=logger,
)


def register_email_template(template_id: str, renderer: TemplateRenderer) -> None:
    """Convenience wrapper for the default service instance."""
    email_dispatch_service.register_template(template_id, renderer)


def clear_registered_templates() -> None:
    """Clear templates from the default service instance."""
    email_dispatch_service.clear_templates()
