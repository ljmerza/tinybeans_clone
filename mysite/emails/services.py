"""Service responsible for orchestrating email delivery."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail

from emails.models import EmailTemplate, RenderedEmail, TemplateRenderer
from emails.mailers import MailerConfigurationError, MailerSendError, send_via_mailjet
from emails.repository import EmailTemplateRepository, InMemoryEmailTemplateRepository

logger = logging.getLogger(__name__)


class EmailServiceError(RuntimeError):
    """Base exception for email service issues."""


class UnknownEmailTemplateError(EmailServiceError):
    """Raised when a requested template is not registered."""


@dataclass
class EmailTransport:
    """Handles the actual dispatching of rendered email content."""

    def send(self, *, to_email: str, template_id: str, content: RenderedEmail) -> None:
        try:
            if getattr(settings, 'MAILJET_ENABLED', False):
                try:
                    send_via_mailjet(
                        to_email=to_email,
                        subject=content.subject,
                        text_body=content.text_body,
                        html_body=content.html_body,
                        template_id=template_id,
                    )
                    return
                except MailerConfigurationError:
                    _send_via_django_backend(
                        to_email=to_email,
                        subject=content.subject,
                        text_body=content.text_body,
                        html_body=content.html_body,
                    )
                except MailerSendError:
                    # Propagate Mailjet errors so Celery can retry
                    raise
            else:
                _send_via_django_backend(
                    to_email=to_email,
                    subject=content.subject,
                    text_body=content.text_body,
                    html_body=content.html_body,
                )
        except Exception as exc:
            logger.warning('Email send failed for %s (%s): %s', template_id, to_email, exc)
            raise


def _send_via_django_backend(*, to_email: str, subject: str, text_body: str, html_body: str | None) -> None:
    if html_body:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        return

    send_mail(
        subject,
        text_body,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )


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
