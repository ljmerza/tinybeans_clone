"""Auth view package exports."""

from mysite.emails.tasks import send_email_task

from .account import (
    LoginView,
    LogoutView,
    SignupView,
    TokenRefreshCookieView,
    get_csrf_token,
)
from .email_verification import (
    EmailVerificationConfirmView,
    EmailVerificationResendView,
)
from .google import (
    GoogleOAuthCallbackView,
    GoogleOAuthInitiateView,
    GoogleOAuthLinkView,
    GoogleOAuthUnlinkView,
)
from .magic_login import (
    MagicLoginRequestView,
    MagicLoginVerifyView,
)
from .passwords import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
)
from .two_factor import (
    RecoveryCodeDownloadView,
    RecoveryCodeGenerateView,
    TrustedDeviceRemoveView,
    TrustedDevicesListView,
    TwoFactorDisableRequestView,
    TwoFactorDisableView,
    TwoFactorMethodRemoveView,
    TwoFactorPreferredMethodView,
    TwoFactorSetupView,
    TwoFactorStatusView,
    TwoFactorVerifyLoginView,
    TwoFactorVerifySetupView,
)

__all__ = [
    "send_email_task",
    "SignupView",
    "LoginView",
    "TokenRefreshCookieView",
    "LogoutView",
    "get_csrf_token",
    "EmailVerificationResendView",
    "EmailVerificationConfirmView",
    "PasswordResetRequestView",
    "PasswordResetConfirmView",
    "PasswordChangeView",
    "MagicLoginRequestView",
    "MagicLoginVerifyView",
    "TwoFactorSetupView",
    "TwoFactorVerifySetupView",
    "TwoFactorStatusView",
    "TwoFactorPreferredMethodView",
    "TwoFactorMethodRemoveView",
    "TwoFactorDisableRequestView",
    "TwoFactorDisableView",
    "RecoveryCodeGenerateView",
    "RecoveryCodeDownloadView",
    "TrustedDevicesListView",
    "TrustedDeviceRemoveView",
    "TwoFactorVerifyLoginView",
    "GoogleOAuthInitiateView",
    "GoogleOAuthCallbackView",
    "GoogleOAuthLinkView",
    "GoogleOAuthUnlinkView",
]
