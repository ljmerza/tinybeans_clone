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


class TwoFactorMailer:
    """Mailer for 2FA related emails"""
    
    @staticmethod
    def send_2fa_code(user, code):
        """Send 2FA verification code via email"""
        email = user.email
        subject = "Your Tinybeans Verification Code"
        body = f"""
Hello {user.username},

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email or contact support if you're concerned about your account security.

Best regards,
The Tinybeans Team
"""
        try:
            if settings.MAILJET_ENABLED:
                send_via_mailjet(
                    to_email=email,
                    subject=subject,
                    text_body=body,
                    html_body=None,
                    template_id='2fa_code',
                )
            else:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                logger.info('Sent 2FA code email to %s via Django backend', email)
        except Exception as e:
            logger.error(f"Failed to send 2FA code email: {e}")
    
    @staticmethod
    def send_2fa_enabled_notification(user):
        """Notify user that 2FA was enabled"""
        email = user.email
        subject = "Two-Factor Authentication Enabled"
        body = f"""
Hello {user.username},

Two-factor authentication has been successfully enabled on your Tinybeans account.

From now on, you'll need to enter a verification code when logging in.

If you didn't enable 2FA, please contact support immediately.

Best regards,
The Tinybeans Team
"""
        try:
            send_via_mailjet(
                to_email=email,
                subject=subject,
                text_body=body,
                html_body=None,
                template_id='2fa_enabled',
            )
        except Exception as e:
            logger.error(f"Failed to send 2FA enabled notification: {e}")
    
    @staticmethod
    def send_2fa_disabled_notification(user):
        """Notify user that 2FA was disabled"""
        email = user.email
        subject = "Two-Factor Authentication Disabled"
        body = f"""
Hello {user.username},

Two-factor authentication has been disabled on your Tinybeans account.

If you didn't disable 2FA, please contact support immediately and secure your account.

Best regards,
The Tinybeans Team
"""
        try:
            send_via_mailjet(
                to_email=email,
                subject=subject,
                text_body=body,
                html_body=None,
                template_id='2fa_disabled',
            )
        except Exception as e:
            logger.error(f"Failed to send 2FA disabled notification: {e}")
    
    @staticmethod
    def send_trusted_device_added(user, device):
        """Notify user that a new trusted device was added"""
        email = user.email
        subject = "New Trusted Device Added"
        body = f"""
Hello {user.username},

A new device has been added to your trusted devices list:

Device: {device.device_name}
IP Address: {device.ip_address}
Date: {device.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

This device will not require 2FA verification for the next {getattr(settings, 'TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS', 30)} days.

If you don't recognize this device, please remove it from your security settings immediately and change your password.

Best regards,
The Tinybeans Team
"""
        try:
            send_via_mailjet(
                to_email=email,
                subject=subject,
                text_body=body,
                html_body=None,
                template_id='trusted_device_added',
            )
        except Exception as e:
            logger.error(f"Failed to send trusted device notification: {e}")
    
    @staticmethod
    def send_recovery_code_used_alert(user, recovery_code):
        """Alert user that a recovery code was used"""
        email = user.email
        subject = "Recovery Code Used"
        body = f"""
Hello {user.username},

A recovery code was used to access your Tinybeans account.

Code: {recovery_code.code[:4]}... (partially hidden)
Date: {recovery_code.used_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

If this wasn't you, please secure your account immediately by:
1. Changing your password
2. Reviewing your trusted devices
3. Generating new recovery codes

Best regards,
The Tinybeans Team
"""
        try:
            send_via_mailjet(
                to_email=email,
                subject=subject,
                body=body,
                template_id='recovery_code_used'
            )
        except Exception as e:
            logger.error(f"Failed to send recovery code alert: {e}")
