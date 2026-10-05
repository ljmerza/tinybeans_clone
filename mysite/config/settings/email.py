"""Email and SMS configuration"""

import os


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


# Email Backend Configuration
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 25))
EMAIL_USE_TLS = _env_flag("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = _env_flag("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@example.com")

# Frontend URL for email links
ACCOUNT_FRONTEND_BASE_URL = os.environ.get(
    "ACCOUNT_FRONTEND_BASE_URL",
    os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000"),
)

# Mailjet Configuration
MAILJET_API_KEY = os.environ.get("MAILJET_API_KEY", "")
MAILJET_API_SECRET = os.environ.get("MAILJET_API_SECRET", "")
MAILJET_API_URL = os.environ.get("MAILJET_API_URL", "https://api.mailjet.com/v3.1/send")
MAILJET_FROM_EMAIL = os.environ.get("MAILJET_FROM_EMAIL") or DEFAULT_FROM_EMAIL
MAILJET_FROM_NAME = os.environ.get("MAILJET_FROM_NAME", "Circles")
MAILJET_USE_SANDBOX = _env_flag("MAILJET_USE_SANDBOX", default=False)
MAILJET_ENABLED = bool(MAILJET_API_KEY and MAILJET_API_SECRET)

# SMS Provider Settings
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "twilio")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

# Circle activity notifications
# Texting notifications costs money per message, so it's off until this is on:
# the SMS switch, phone verification and sending all check it.
NOTIFICATIONS_SMS_ENABLED = _env_flag("NOTIFICATIONS_SMS_ENABLED", default=False)
# Most activity texts one user gets per day; the rest are dropped.
NOTIFICATIONS_SMS_DAILY_LIMIT = int(os.environ.get("NOTIFICATIONS_SMS_DAILY_LIMIT", 20))
# E.164 prefixes a notification phone may start with (empty allows every
# country). Keeps verification codes away from premium international ranges.
NOTIFICATIONS_SMS_ALLOWED_PREFIXES = [
    prefix.strip() for prefix in os.environ.get("NOTIFICATIONS_SMS_ALLOWED_PREFIXES", "+1").split(",") if prefix.strip()
]
# Verification codes one user can request (django-ratelimit rate).
NOTIFICATION_PHONE_CODE_RATELIMIT = os.environ.get("NOTIFICATION_PHONE_CODE_RATELIMIT", "3/15m")

# Web push. VAPID keys are base64url; the subject is a mailto: or https: URL.
# Push stays off unless all three are set.
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "")
NOTIFICATIONS_PUSH_ENABLED = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY and VAPID_SUBJECT)
# Host suffixes a push subscription endpoint may point at. The server POSTs to
# the endpoint, so arbitrary URLs would let a user make it call anything.
PUSH_ALLOWED_ENDPOINT_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "PUSH_ALLOWED_ENDPOINT_HOSTS",
        "fcm.googleapis.com,push.services.mozilla.com,push.apple.com,notify.windows.com",
    ).split(",")
    if host.strip()
]
# New-photo notices wait this long so the post's uploads can finish first.
NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS = int(os.environ.get("NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS", 600))
