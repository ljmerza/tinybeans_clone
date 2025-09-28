"""Child profile and upgrade management models.

This module defines models for managing child profiles within circles,
including child account upgrades, guardian consent, and audit logging
for child-related operations.
"""
import uuid
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from .circle import Circle


class ChildProfileUpgradeStatus(models.TextChoices):
    """Status of a child profile's upgrade to a full user account.
    
    Tracks the progression from basic profile to linked user account.
    """
    UNLINKED = 'unlinked', 'Unlinked'
    PENDING = 'pending', 'Pending'
    LINKED = 'linked', 'Linked'


class ChildProfile(models.Model):
    """Profile for a child within a family circle.
    
    Represents a child's profile with basic information and the ability to
    upgrade to a full user account when appropriate age is reached.
    
    Attributes:
        id: UUID primary key for secure identification
        circle: The family circle this child belongs to
        display_name: Child's name as shown in the app
        birthdate: Child's date of birth (optional)
        avatar_url: URL to child's profile picture (optional)
        pronouns: Child's preferred pronouns (optional)
        favorite_moments: JSON list of favorited content IDs
        linked_user: Full user account if child has been upgraded
        pending_invite_email: Email for pending upgrade invitation
        upgrade_status: Current status of account upgrade process
        upgrade_requested_by: User who initiated the upgrade request
        upgrade_token: Secure token for completing upgrade
        upgrade_token_expires_at: When the upgrade token expires
        created_at: When the profile was created
        updated_at: When the profile was last modified
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='children')
    display_name = models.CharField(max_length=150, validators=[MinLengthValidator(1)])
    birthdate = models.DateField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    pronouns = models.CharField(max_length=64, blank=True)
    favorite_moments = models.JSONField(default=list, blank=True)
    linked_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='child_profile',
    )
    pending_invite_email = models.EmailField(blank=True, null=True)
    upgrade_status = models.CharField(
        max_length=20,
        choices=ChildProfileUpgradeStatus.choices,
        default=ChildProfileUpgradeStatus.UNLINKED,
    )
    upgrade_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='child_upgrades_requested',
    )
    upgrade_token = models.CharField(max_length=64, blank=True, null=True)
    upgrade_token_expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

    def log_upgrade_event(self, event_type: str, performed_by=None, metadata=None):
        """Log an upgrade-related event for audit purposes.
        
        Args:
            event_type: Type of event from ChildUpgradeEventType choices
            performed_by: User who performed the action (optional)
            metadata: Additional event data (optional)
        """
        ChildUpgradeAuditLog.objects.create(
            child=self,
            event_type=event_type,
            performed_by=performed_by,
            metadata=metadata or {},
        )

    def clear_upgrade_token(self):
        """Clear the upgrade token and expiration date."""
        self.upgrade_token = None
        self.upgrade_token_expires_at = None


class GuardianConsentMethod(models.TextChoices):
    """Methods by which guardian consent can be obtained.
    
    Different ways to capture legal guardian consent for child account operations.
    """
    DIGITAL_SIGNATURE = 'digital_signature', 'Digital Signature'
    PAPER_UPLOAD = 'paper_upload', 'Paper Upload'
    VERBAL = 'verbal', 'Documented Verbal Consent'


class ChildGuardianConsent(models.Model):
    """Record of guardian consent for child-related operations.
    
    Captures legal guardian consent required for child account operations,
    including the method used and relevant metadata for compliance.
    
    Attributes:
        id: UUID primary key for secure identification
        child: The child profile this consent relates to
        guardian_name: Full name of the guardian providing consent
        guardian_relationship: Relationship to the child (e.g., "mother", "father")
        agreement_reference: Reference to specific agreement or terms
        consent_method: How the consent was captured
        consent_metadata: Additional data related to consent capture
        signed_at: When the consent was provided
        captured_by: User who captured/recorded the consent
        created_at: When this record was created
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(ChildProfile, on_delete=models.CASCADE, related_name='guardian_consents')
    guardian_name = models.CharField(max_length=255)
    guardian_relationship = models.CharField(max_length=255)
    agreement_reference = models.CharField(max_length=255, blank=True)
    consent_method = models.CharField(max_length=32, choices=GuardianConsentMethod.choices)
    consent_metadata = models.JSONField(default=dict, blank=True)
    signed_at = models.DateTimeField(default=timezone.now)
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='guardian_consents_captured',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Consent for {self.child.display_name} by {self.guardian_name}"


class ChildUpgradeEventType(models.TextChoices):
    """Types of events in the child upgrade process.
    
    Defines the different audit events that can occur during child account upgrades.
    """
    REQUEST_INITIATED = 'request_initiated', 'Request Initiated'
    TOKEN_REISSUED = 'token_reissued', 'Token Reissued'
    TOKEN_REVOKED = 'token_revoked', 'Token Revoked'
    UPGRADE_COMPLETED = 'upgrade_completed', 'Upgrade Completed'


class ChildUpgradeAuditLog(models.Model):
    """Audit log for child profile upgrade events.
    
    Maintains a complete audit trail of all actions taken during the child
    profile upgrade process for security and compliance purposes.
    
    Attributes:
        id: UUID primary key for secure identification
        child: The child profile this event relates to
        event_type: Type of event that occurred
        performed_by: User who performed the action (if applicable)
        metadata: Additional event-specific data
        created_at: When the event occurred
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(ChildProfile, on_delete=models.CASCADE, related_name='upgrade_audit_logs')
    event_type = models.CharField(max_length=32, choices=ChildUpgradeEventType.choices)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='child_upgrade_events',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.child.display_name}: {self.event_type}"