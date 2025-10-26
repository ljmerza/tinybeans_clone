from django.urls import path

from .views import (
    EmailVerificationConfirmView,
    EmailVerificationResendView,
    GoogleOAuthCallbackView,
    GoogleOAuthInitiateView,
    GoogleOAuthLinkView,
    GoogleOAuthUnlinkView,
    LoginView,
    LogoutView,
    MagicLoginRequestView,
    MagicLoginVerifyView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    SignupView,
    TokenRefreshCookieView,
    TwoFactorDisableRequestView,
    TwoFactorDisableView,
    TwoFactorMethodRemoveView,
    TwoFactorPreferredMethodView,
    TwoFactorSetupView,
    TwoFactorStatusView,
    TwoFactorVerifyLoginView,
    TwoFactorVerifySetupView,
    RecoveryCodeDownloadView,
    RecoveryCodeGenerateView,
    TrustedDeviceRemoveView,
    TrustedDevicesListView,
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
    
    path('magic-login/request/', MagicLoginRequestView.as_view(), name='auth-magic-login-request'),
    path('magic-login/verify/', MagicLoginVerifyView.as_view(), name='auth-magic-login-verify'),
    
    # Google OAuth endpoints
    path('google/initiate/', GoogleOAuthInitiateView.as_view(), name='auth-google-initiate'),
    path('google/callback/', GoogleOAuthCallbackView.as_view(), name='auth-google-callback'),
    path('google/link/', GoogleOAuthLinkView.as_view(), name='auth-google-link'),
    path('google/unlink/', GoogleOAuthUnlinkView.as_view(), name='auth-google-unlink'),
]

urlpatterns += [
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='2fa-setup'),
    path('2fa/verify-setup/', TwoFactorVerifySetupView.as_view(), name='2fa-verify-setup'),
    path('2fa/verify-login/', TwoFactorVerifyLoginView.as_view(), name='2fa-verify-login'),
    path('2fa/status/', TwoFactorStatusView.as_view(), name='2fa-status'),
    path('2fa/preferred-method/', TwoFactorPreferredMethodView.as_view(), name='2fa-preferred-method'),
    path('2fa/methods/<str:method>/', TwoFactorMethodRemoveView.as_view(), name='2fa-method-remove'),
    path('2fa/disable/request/', TwoFactorDisableRequestView.as_view(), name='2fa-disable-request'),
    path('2fa/disable/', TwoFactorDisableView.as_view(), name='2fa-disable'),
    path('2fa/recovery-codes/generate/', RecoveryCodeGenerateView.as_view(), name='2fa-recovery-generate'),
    path('2fa/recovery-codes/download/', RecoveryCodeDownloadView.as_view(), name='2fa-recovery-download'),
    path('2fa/trusted-devices/', TrustedDevicesListView.as_view(), name='2fa-trusted-devices'),
    path('2fa/trusted-devices/<str:device_id>/', TrustedDeviceRemoveView.as_view(), name='2fa-trusted-device-remove'),
]
