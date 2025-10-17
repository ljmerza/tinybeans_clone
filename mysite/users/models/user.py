"""User authentication and role management models.

This module defines the custom User model and related authentication classes
for the Tinybeans application, including user roles and custom user management.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    """User roles within circles.
    
    Defines the different permission levels a user can have within a circle.
    Circle admins have elevated permissions to manage the circle and its members.
    """
    CIRCLE_ADMIN = 'admin', 'Circle Admin'
    CIRCLE_MEMBER = 'member', 'Circle Member'


class UserManager(BaseUserManager):
    """Custom user manager for the User model.
    
    Handles user creation with custom fields and validation.
    Ensures both username and email are required and properly normalized.
    """
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """Create and save a user with the given username, email and password.
        
        Args:
            username: The username for the user
            email: The email address for the user
            password: The password for the user
            **extra_fields: Additional fields to set on the user
            
        Returns:
            The created User instance
            
        Raises:
            ValueError: If username or email is not provided
        """
        if not username:
            raise ValueError('The username must be set')
        if not email:
            raise ValueError('The email address must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        """Create a regular user with default permissions.
        
        Args:
            username: The username for the user
            email: The email address for the user
            password: The password for the user (optional)
            **extra_fields: Additional fields to set on the user
            
        Returns:
            The created User instance
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', UserRole.CIRCLE_MEMBER)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create a superuser with admin permissions.
        
        Args:
            username: The username for the superuser
            email: The email address for the superuser
            password: The password for the superuser (optional)
            **extra_fields: Additional fields to set on the user
            
        Returns:
            The created User instance
            
        Raises:
            ValueError: If is_staff or is_superuser is not True
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.CIRCLE_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class AuthProvider(models.TextChoices):
    """Authentication provider choices for users.
    
    Defines how a user authenticated with the system:
    - MANUAL: Traditional email/password registration
    - GOOGLE: Google OAuth only
    - HYBRID: Both manual and Google OAuth linked
    """
    MANUAL = 'manual', 'Manual Registration'
    GOOGLE = 'google', 'Google OAuth Only'
    HYBRID = 'hybrid', 'Both Manual and Google'


class Language(models.TextChoices):
    """Language choices for user interface.
    
    Defines the available languages for the application interface.
    """
    ENGLISH = 'en', 'English'
    SPANISH = 'es', 'Spanish'



class CircleOnboardingStatus(models.TextChoices):
    """Onboarding status choices for first-circle flow."""
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    DISMISSED = "dismissed", "Dismissed"


class User(AbstractUser):
    """Custom user model for the Tinybeans application.
    
    Extends Django's AbstractUser with additional fields for email verification,
    user roles within circles, and Google OAuth integration.
    
    Attributes:
        email: User's email address (required, unique)
        role: User's default role (admin or member)
        email_verified: Whether the user's email has been verified
        google_id: Google user ID from OAuth (unique, nullable)
        google_email: Email from Google for debugging/tracking (nullable)
        has_usable_password: Whether user has set a password
        auth_provider: How the user authenticates (manual, google, hybrid)
        google_linked_at: When Google account was linked (nullable)
        last_google_sync: Last time user info was synced from Google (nullable)
    """
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CIRCLE_MEMBER,
    )
    email_verified = models.BooleanField(default=False)
    
    # Google OAuth fields
    google_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Google user ID from OAuth"
    )
    google_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email from Google (for debugging/tracking)"
    )
    has_usable_password = models.BooleanField(
        default=True,
        help_text="Whether user has set a password"
    )
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.MANUAL,
        help_text="Authentication method used by user"
    )
    google_linked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When Google account was linked"
    )
    last_google_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time user info was synced from Google"
    )
    language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.ENGLISH,
        help_text="User's preferred language for the interface"
    )

    circle_onboarding_status = models.CharField(
        max_length=20,
        choices=CircleOnboardingStatus.choices,
        default=CircleOnboardingStatus.PENDING,
        help_text="Progress of the user's first-circle onboarding"
    )
    circle_onboarding_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the circle onboarding status changed"
    )

    @property
    def needs_circle_onboarding(self) -> bool:
        """Return True when the user should be guided through circle onboarding."""
        if self.circle_onboarding_status != CircleOnboardingStatus.PENDING:
            return False
        return not self.circle_memberships.exists()

    def set_circle_onboarding_status(self, status: str, *, save: bool = True) -> bool:
        """Update the onboarding status and timestamp.

        Args:
            status: New status from ``CircleOnboardingStatus`` choices.
            save: Whether to persist the change immediately.

        Returns:
            bool: True when the status changed, False otherwise.
        """
        if status not in CircleOnboardingStatus.values:
            raise ValueError(f"Invalid circle onboarding status: {status}")

        if self.circle_onboarding_status == status:
            if save and status == CircleOnboardingStatus.PENDING and self.circle_onboarding_updated_at is None:
                self.circle_onboarding_updated_at = timezone.now()
                self.save(update_fields=["circle_onboarding_updated_at"])
            return False

        self.circle_onboarding_status = status
        self.circle_onboarding_updated_at = timezone.now()
        if save:
            self.save(update_fields=["circle_onboarding_status", "circle_onboarding_updated_at"])
        return True


    objects = UserManager()

    REQUIRED_FIELDS = ['email']

    class Meta:
        ordering = ['username']
        indexes = [
            models.Index(fields=['google_id'], name='users_google_id_idx'),
        ]