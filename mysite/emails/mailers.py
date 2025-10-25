from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.core.mail import send_mail
from requests import Response

logger = logging.getLogger(__name__)


class MailerConfigurationError(RuntimeError):
    """Raised when Mailjet is not configured but attempted to be used."""

# Lazy import to avoid circular import at module load time
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # only for type checkers
    from mysite.emails.services import EmailDispatchService


def _dispatch_service():
    # Import here to break circular import chain
    from mysite.emails.services import email_dispatch_service
    return email_dispatch_service



class MailerSendError(RuntimeError):
    """Raised when Mailjet responds with a non-successful status."""


def _build_payload(
    *, to_email: str, subject: str, text_body: str, html_body: str | None, template_id: str
) -> dict[str, Any]:
    message: dict[str, Any] = {
        'From': {
            'Email': settings.MAILJET_FROM_EMAIL,
            'Name': settings.MAILJET_FROM_NAME,
        },
        'To': [{'Email': to_email}],
        'Subject': subject,
        'TextPart': text_body,
        'CustomID': template_id,
    }
    if html_body:
        message['HTMLPart'] = html_body
    payload: dict[str, Any] = {'Messages': [message]}
    if settings.MAILJET_USE_SANDBOX:
        payload['SandboxMode'] = True
    return payload


def send_via_mailjet(
    *, to_email: str, subject: str, text_body: str, html_body: str | None = None, template_id: str
) -> None:
    if not settings.MAILJET_ENABLED:
        raise MailerConfigurationError('Mailjet is not configured')

    payload = _build_payload(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        template_id=template_id,
    )
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


from mysite.emails.templates import (
    TWOFA_CODE_TEMPLATE,
    TWOFA_ENABLED_TEMPLATE,
    TWOFA_DISABLED_TEMPLATE,
    TWOFA_TRUSTED_DEVICE_ADDED_TEMPLATE,
    TWOFA_RECOVERY_CODE_USED_TEMPLATE,
)

class TwoFactorMailer:
    """Mailer for 2FA related emails (uses Django template-based emails)"""

    @staticmethod
    def _enqueue_email(to_email: str, template_id: str, context: dict[str, Any]) -> None:
        """
        Try to enqueue an email via Celery. If Celery is unavailable fall back to the local dispatcher.
        """
        try:
            from mysite.emails.tasks import send_email_task

            send_email_task.delay(
                to_email=to_email,
                template_id=template_id,
                context=context,
            )
            return
        except Exception as exc:
            logger.warning("Falling back to synchronous email send for %s: %s", template_id, exc)
            _dispatch_service().send_email(
                to_email=to_email,
                template_id=template_id,
                context=context,
            )

    @staticmethod
    def send_2fa_code(user, code):
        """Send 2FA verification code via email using template"""
        context = {
            'email': user.email,
            'full_name': user.display_name,
            'code': code,
            'expires_in_minutes': getattr(settings, 'TWOFA_CODE_EXPIRY_MINUTES', 10),
        }
        try:
            TwoFactorMailer._enqueue_email(
                to_email=user.email,
                template_id=TWOFA_CODE_TEMPLATE,
                context=context,
            )
        except Exception as e:
            logger.error(f"Failed to send 2FA code email: {e}")

    @staticmethod
    def send_2fa_enabled_notification(user):
        """Notify user that 2FA was enabled (template)"""
        context = {
            'email': user.email,
            'full_name': user.display_name,
        }
        try:
            TwoFactorMailer._enqueue_email(
                to_email=user.email,
                template_id=TWOFA_ENABLED_TEMPLATE,
                context=context,
            )
        except Exception as e:
            logger.error(f"Failed to send 2FA enabled notification: {e}")

    @staticmethod
    def send_2fa_disabled_notification(user):
        """Notify user that 2FA was disabled (template)"""
        context = {
            'email': user.email,
            'full_name': user.display_name,
        }
        try:
            TwoFactorMailer._enqueue_email(
                to_email=user.email,
                template_id=TWOFA_DISABLED_TEMPLATE,
                context=context,
            )
        except Exception as e:
            logger.error(f"Failed to send 2FA disabled notification: {e}")

    @staticmethod
    def send_trusted_device_added(user, device):
        """Notify user that a new trusted device was added (template)"""
        context = {
            'email': user.email,
            'full_name': user.display_name,
            'device_name': device.device_name,
            'ip_address': device.ip_address,
            'created_at': device.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        }
        try:
            TwoFactorMailer._enqueue_email(
                to_email=user.email,
                template_id=TWOFA_TRUSTED_DEVICE_ADDED_TEMPLATE,
                context=context,
            )
        except Exception as e:
            logger.error(f"Failed to send trusted device notification: {e}")

    @staticmethod
    def send_recovery_code_used_alert(user):
        """Alert user that a recovery code was used (template)"""
        # We no longer include the code itself in the email for security reasons
        from django.utils import timezone
        context = {
            'email': user.email,
            'full_name': user.display_name,
            'used_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        }
        try:
            TwoFactorMailer._enqueue_email(
                to_email=user.email,
                template_id=TWOFA_RECOVERY_CODE_USED_TEMPLATE,
                context=context,
            )
        except Exception as e:
            logger.error(f"Failed to send recovery code alert: {e}")
