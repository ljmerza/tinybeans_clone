import uuid
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from .circle import Circle


class ChildProfileUpgradeStatus(models.TextChoices):
    UNLINKED = 'unlinked', 'Unlinked'
    PENDING = 'pending', 'Pending'
    LINKED = 'linked', 'Linked'


class ChildProfile(models.Model):
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
        ChildUpgradeAuditLog.objects.create(
            child=self,
            event_type=event_type,
            performed_by=performed_by,
            metadata=metadata or {},
        )

    def clear_upgrade_token(self):
        self.upgrade_token = None
        self.upgrade_token_expires_at = None


class GuardianConsentMethod(models.TextChoices):
    DIGITAL_SIGNATURE = 'digital_signature', 'Digital Signature'
    PAPER_UPLOAD = 'paper_upload', 'Paper Upload'
    VERBAL = 'verbal', 'Documented Verbal Consent'


class ChildGuardianConsent(models.Model):
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
    REQUEST_INITIATED = 'request_initiated', 'Request Initiated'
    TOKEN_REISSUED = 'token_reissued', 'Token Reissued'
    TOKEN_REVOKED = 'token_revoked', 'Token Revoked'
    UPGRADE_COMPLETED = 'upgrade_completed', 'Upgrade Completed'


class ChildUpgradeAuditLog(models.Model):
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