from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from requests import Response

logger = logging.getLogger(__name__)


class MailerConfigurationError(RuntimeError):
    """Raised when Mailjet is not configured but attempted to be used."""


class MailerSendError(RuntimeError):
    """Raised when Mailjet responds with a non-successful status."""


def _build_payload(*, to_email: str, subject: str, body: str, template_id: str) -> dict[str, Any]:
    message: dict[str, Any] = {
        'From': {
            'Email': settings.MAILJET_FROM_EMAIL,
            'Name': settings.MAILJET_FROM_NAME,
        },
        'To': [{'Email': to_email}],
        'Subject': subject,
        'TextPart': body,
        'CustomID': template_id,
    }
    payload: dict[str, Any] = {'Messages': [message]}
    if settings.MAILJET_USE_SANDBOX:
        payload['SandboxMode'] = True
    return payload


def send_via_mailjet(*, to_email: str, subject: str, body: str, template_id: str) -> None:
    if not settings.MAILJET_ENABLED:
        raise MailerConfigurationError('Mailjet is not configured')

    payload = _build_payload(to_email=to_email, subject=subject, body=body, template_id=template_id)
    try:
        response: Response = requests.post(
            settings.MAILJET_API_URL,
            json=payload,
            auth=(settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET),
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.error('Mailjet request failed: %s', exc)
        raise MailerSendError(str(exc)) from exc

    if response.status_code >= 400:
        logger.error('Mailjet responded with %s: %s', response.status_code, response.text)
        raise MailerSendError(f'HTTP {response.status_code}')

    try:
        response_json = response.json()
    except ValueError:
        logger.warning('Mailjet response was not JSON, proceeding anyway')
        return

    messages = response_json.get('Messages', [])
    for message in messages:
        status = message.get('Status')
        if status and status.upper() != 'SUCCESS':
            logger.warning('Mailjet message delivered with status %s: %s', status, message)

    logger.info('Mailjet dispatched template %s to %s', template_id, to_email)
