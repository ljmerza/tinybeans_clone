# Import all models to maintain backwards compatibility
from .user import CircleOnboardingStatus, UserRole, UserManager, User
from .circle import Circle, CircleMembership, CircleInvitation, CircleInvitationStatus
from .child_profile import (
    ChildProfile, 
    ChildProfileUpgradeStatus, 
    ChildGuardianConsent, 
    GuardianConsentMethod, 
    ChildUpgradeAuditLog, 
    ChildUpgradeEventType
)
from .pet_profile import PetProfile, PetType
from .notifications import UserNotificationPreferences, NotificationChannel, DigestFrequency
from .utils import generate_unique_slug

__all__ = [
    'CircleOnboardingStatus', 'UserRole', 'UserManager', 'User',
    'Circle', 'CircleMembership', 'CircleInvitation', 'CircleInvitationStatus',
    'ChildProfile', 'ChildProfileUpgradeStatus', 'ChildGuardianConsent', 
    'GuardianConsentMethod', 'ChildUpgradeAuditLog', 'ChildUpgradeEventType',
    'PetProfile', 'PetType',
    'UserNotificationPreferences', 'NotificationChannel', 'DigestFrequency',
    'generate_unique_slug'
]
