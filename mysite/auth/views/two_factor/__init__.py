"""Aggregated exports for two-factor authentication views."""

from .login import TwoFactorVerifyLoginView
from .management import (
    TwoFactorDisableRequestView,
    TwoFactorDisableView,
    TwoFactorMethodRemoveView,
    TwoFactorPreferredMethodView,
    TwoFactorStatusView,
)
from .recovery import RecoveryCodeDownloadView, RecoveryCodeGenerateView
from .setup import TwoFactorSetupView, TwoFactorVerifySetupView
from .trusted_devices import TrustedDeviceRemoveView, TrustedDevicesListView

__all__ = [
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
]
