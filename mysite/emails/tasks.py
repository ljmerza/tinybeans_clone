from __future__ import annotations

import logging
from typing import Any, Callable

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

_TemplateRenderer = Callable[[dict[str, Any]], tuple[str, str]]
_TEMPLATE_REGISTRY: dict[str, _TemplateRenderer] = {}


def register_email_template(template_id: str, renderer: _TemplateRenderer) -> None:
    """Register or replace a template renderer for the shared email task."""
    _TEMPLATE_REGISTRY[template_id] = renderer


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_email_task(self, *, to_email: str, template_id: str, context: dict[str, Any]) -> None:
    renderer = _TEMPLATE_REGISTRY.get(template_id)
    if renderer is None:
        logger.error('Unknown email template %s; dropping email', template_id)
        return

    subject, body = renderer(context)
    try:
        if getattr(settings, 'MAILJET_ENABLED', False):
            from .mailers import MailerConfigurationError, MailerSendError, send_via_mailjet

            try:
                send_via_mailjet(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                    template_id=template_id,
                )
            except MailerConfigurationError:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [to_email],
                    fail_silently=False,
                )
            except MailerSendError as exc:
                logger.warning('Mailjet send failed for %s (%s): %s', template_id, to_email, exc)
                raise
        else:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)

        logger.info('Dispatched %s email to %s', template_id, to_email)
    except Exception as exc:
        logger.warning('Email send failed for %s (%s): %s', template_id, to_email, exc)
        raise
