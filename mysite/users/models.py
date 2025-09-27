# This file maintains backwards compatibility by importing all models
# All models have been split into separate files in the models/ directory
# for better organization and maintainability.

# Import all models to maintain backwards compatibility
from .models.user import UserRole, UserManager, User
from .models.circle import Circle, CircleMembership, CircleInvitation, CircleInvitationStatus
from .models.child_profile import (
    ChildProfile, 
    ChildProfileUpgradeStatus, 
    ChildGuardianConsent, 
    GuardianConsentMethod, 
    ChildUpgradeAuditLog, 
    ChildUpgradeEventType
)
from .models.notifications import UserNotificationPreferences, NotificationChannel, DigestFrequency
from .models.utils import generate_unique_slug
