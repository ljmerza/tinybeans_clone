"""Auth view package exports."""
from mysite.emails.tasks import send_email_task

from .account import (
    SignupView,
    LoginView,
    TokenRefreshCookieView,
    LogoutView,
    get_csrf_token,
)
from .email_verification import (
    EmailVerificationResendView,
    EmailVerificationConfirmView,
)
from .passwords import (
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordChangeView,
)
from .magic_login import (
    MagicLoginRequestView,
    MagicLoginVerifyView,
)
from .two_factor import (
    TwoFactorSetupView,
    TwoFactorVerifySetupView,
    TwoFactorStatusView,
    TwoFactorPreferredMethodView,
    TwoFactorMethodRemoveView,
    TwoFactorDisableRequestView,
    TwoFactorDisableView,
    RecoveryCodeGenerateView,
    RecoveryCodeDownloadView,
    TrustedDevicesListView,
    TrustedDeviceRemoveView,
    TwoFactorVerifyLoginView,
)
from .google import (
    GoogleOAuthInitiateView,
    GoogleOAuthCallbackView,
    GoogleOAuthLinkView,
    GoogleOAuthUnlinkView,
)

__all__ = [
    'send_email_task',
    'SignupView',
    'LoginView',
    'TokenRefreshCookieView',
    'LogoutView',
    'get_csrf_token',
    'EmailVerificationResendView',
    'EmailVerificationConfirmView',
    'PasswordResetRequestView',
    'PasswordResetConfirmView',
    'PasswordChangeView',
    'MagicLoginRequestView',
    'MagicLoginVerifyView',
    'TwoFactorSetupView',
    'TwoFactorVerifySetupView',
    'TwoFactorStatusView',
    'TwoFactorPreferredMethodView',
    'TwoFactorMethodRemoveView',
    'TwoFactorDisableRequestView',
    'TwoFactorDisableView',
    'RecoveryCodeGenerateView',
    'RecoveryCodeDownloadView',
    'TrustedDevicesListView',
    'TrustedDeviceRemoveView',
    'TwoFactorVerifyLoginView',
    'GoogleOAuthInitiateView',
    'GoogleOAuthCallbackView',
    'GoogleOAuthLinkView',
    'GoogleOAuthUnlinkView',
]
