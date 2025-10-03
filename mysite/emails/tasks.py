from __future__ import annotations

from typing import Any

from celery import shared_task

from emails.models import TemplateRenderer
from emails.services import email_dispatch_service, register_email_template


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_email_task(self, *, to_email: str, template_id: str, context: dict[str, Any]) -> None:
    dispatched = email_dispatch_service.send_email(
        to_email=to_email,
        template_id=template_id,
        context=context,
    )

    # A missing template is logged by the service and should not raise to avoid retries.
    if not dispatched:
        return
