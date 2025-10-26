"""Email and SMS configuration"""
import os


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


# Email Backend Configuration
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 25))
EMAIL_USE_TLS = _env_flag('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = _env_flag('EMAIL_USE_SSL', default=False)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.com')

# Frontend URL for email links
ACCOUNT_FRONTEND_BASE_URL = os.environ.get(
    'ACCOUNT_FRONTEND_BASE_URL',
    os.environ.get('FRONTEND_BASE_URL', 'http://localhost:3000'),
)

# Mailjet Configuration
MAILJET_API_KEY = os.environ.get('MAILJET_API_KEY', '')
MAILJET_API_SECRET = os.environ.get('MAILJET_API_SECRET', '')
MAILJET_API_URL = os.environ.get('MAILJET_API_URL', 'https://api.mailjet.com/v3.1/send')
MAILJET_FROM_EMAIL = os.environ.get('MAILJET_FROM_EMAIL') or DEFAULT_FROM_EMAIL
MAILJET_FROM_NAME = os.environ.get('MAILJET_FROM_NAME', 'Tinybeans Circles')
MAILJET_USE_SANDBOX = _env_flag('MAILJET_USE_SANDBOX', default=False)
MAILJET_ENABLED = bool(MAILJET_API_KEY and MAILJET_API_SECRET)

# SMS Provider Settings
SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'twilio')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
