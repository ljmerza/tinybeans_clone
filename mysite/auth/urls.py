from django.urls import path

from .views import (
    EmailVerificationConfirmView,
    EmailVerificationResendView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SignupView,
    TokenRefreshCookieView,
    get_csrf_token,
)

urlpatterns = [
    path('csrf/', get_csrf_token, name='auth-csrf'),
    path('signup/', SignupView.as_view(), name='auth-signup'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshCookieView.as_view(), name='auth-token-refresh'),
    
    path('verify-email/resend/', EmailVerificationResendView.as_view(), name='auth-verify-resend'),
    path('verify-email/confirm/', EmailVerificationConfirmView.as_view(), name='auth-verify-confirm'),
    
    path('password/change/', PasswordChangeView.as_view(), name='auth-password-change'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
]

# Two-Factor Authentication URLs
from .views_2fa import (
    TwoFactorSetupView,
    TwoFactorVerifySetupView,
    TwoFactorStatusView,
    TwoFactorDisableView,
    RecoveryCodeGenerateView,
    RecoveryCodeDownloadView,
    TrustedDevicesListView,
    TrustedDeviceRemoveView,
    TwoFactorVerifyLoginView,
)

urlpatterns += [
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='2fa-setup'),
    path('2fa/verify-setup/', TwoFactorVerifySetupView.as_view(), name='2fa-verify-setup'),
    path('2fa/verify-login/', TwoFactorVerifyLoginView.as_view(), name='2fa-verify-login'),
    path('2fa/status/', TwoFactorStatusView.as_view(), name='2fa-status'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='2fa-disable'),
    path('2fa/recovery-codes/generate/', RecoveryCodeGenerateView.as_view(), name='2fa-recovery-generate'),
    path('2fa/recovery-codes/download/', RecoveryCodeDownloadView.as_view(), name='2fa-recovery-download'),
    path('2fa/trusted-devices/', TrustedDevicesListView.as_view(), name='2fa-trusted-devices'),
    path('2fa/trusted-devices/<str:device_id>/', TrustedDeviceRemoveView.as_view(), name='2fa-trusted-device-remove'),
]
