"""Account Linking Service.

This service handles:
- Creating new users from Google OAuth
- Linking Google accounts to existing users
- Unlinking Google accounts from users
"""
import logging
from typing import Dict, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

User = get_user_model()
logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class UnverifiedAccountError(OAuthError):
    """Account with this email exists but is unverified."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Unverified account exists: {email}")


class GoogleAccountAlreadyLinkedError(OAuthError):
    """Google account is already linked to a different user."""
    pass


class AccountLinkingService:
    """Service for linking/unlinking Google accounts."""

    @transaction.atomic
    def get_or_create_user(
        self,
        google_user_info: Dict[str, any]
    ) -> Tuple[User, str]:
        """Get existing user or create new user from Google info.

        Implements the 5 account scenarios from ADR-010:
        1. New user → Create account
        2. Existing verified user → Link Google ID
        3. Existing unverified user → BLOCK
        4. User with Google ID → Login
        5. Link to authenticated user

        Args:
            google_user_info: User info from Google ID token

        Returns:
            Tuple of (User, action) where action is 'created', 'linked', or 'login'

        Raises:
            UnverifiedAccountError: If unverified account exists
            GoogleAccountAlreadyLinkedError: If Google ID already linked
        """
        google_id = google_user_info['sub']
        google_email = google_user_info['email']
        email_verified = google_user_info.get('email_verified', False)

        # Check if Google ID already exists
        try:
            existing_user = User.objects.get(google_id=google_id)
            logger.info(
                "OAuth login - existing Google user",
                extra={'user_id': existing_user.id, 'google_id': google_id}
            )
            return existing_user, 'login'
        except User.DoesNotExist:
            pass

        # Check if email exists
        try:
            existing_user = User.objects.get(email=google_email)

            # CRITICAL SECURITY CHECK: Prevent account takeover
            if not existing_user.email_verified:
                logger.warning(
                    "OAuth blocked - unverified account exists",
                    extra={'email': google_email, 'google_id': google_id}
                )
                raise UnverifiedAccountError(google_email)

            # Verified account - link Google ID
            existing_user.google_id = google_id
            existing_user.google_email = google_email
            existing_user.auth_provider = 'hybrid'
            existing_user.google_linked_at = timezone.now()
            existing_user.last_google_sync = timezone.now()
            existing_user.email_verified = True  # Ensure verified
            existing_user.save()

            logger.info(
                "OAuth account linked",
                extra={'user_id': existing_user.id, 'google_id': google_id}
            )

            return existing_user, 'linked'

        except User.DoesNotExist:
            pass

        # Create new Google-only user
        new_user = User.objects.create(
            email=google_email,
            google_id=google_id,
            google_email=google_email,
            first_name=google_user_info.get('given_name', ''),
            last_name=google_user_info.get('family_name', ''),
            email_verified=True,  # Google verifies emails
            auth_provider='google',
            password_login_enabled=False,  # No password set
            google_linked_at=timezone.now(),
            last_google_sync=timezone.now()
        )

        # Set unusable password (prevents password login)
        new_user.set_unusable_password()
        new_user.save()

        logger.info(
            "OAuth user created",
            extra={'user_id': new_user.id, 'google_id': google_id, 'email': google_email}
        )

        return new_user, 'created'

    @transaction.atomic
    def link_google_account(
        self,
        user: User,
        google_user_info: Dict[str, any]
    ) -> User:
        """Link Google account to existing authenticated user.

        Args:
            user: Authenticated user
            google_user_info: User info from Google

        Returns:
            Updated user

        Raises:
            GoogleAccountAlreadyLinkedError: If Google ID already used
            OAuthError: If email doesn't match
        """
        google_id = google_user_info['sub']
        google_email = google_user_info['email']

        # Verify email matches
        if user.email != google_email:
            raise OAuthError(
                f"Google email ({google_email}) doesn't match user email ({user.email})"
            )

        # Check if Google ID already linked to different user
        if User.objects.filter(google_id=google_id).exclude(id=user.id).exists():
            raise GoogleAccountAlreadyLinkedError(
                "This Google account is already linked to another user"
            )

        # Link Google account
        user.google_id = google_id
        user.google_email = google_email
        user.auth_provider = 'hybrid' if user.password_login_enabled else 'google'
        user.google_linked_at = timezone.now()
        user.last_google_sync = timezone.now()
        user.email_verified = True
        user.save()

        logger.info(
            "Google account linked to user",
            extra={'user_id': user.id, 'google_id': google_id}
        )

        return user

    @transaction.atomic
    def unlink_google_account(self, user: User) -> User:
        """Unlink Google account from user.

        Args:
            user: User to unlink from

        Returns:
            Updated user

        Raises:
            OAuthError: If user has no password and can't unlink
        """
        if not user.password_login_enabled:
            raise OAuthError(
                "Cannot unlink Google account without setting a password first"
            )

        user.google_id = None
        user.google_email = None
        user.auth_provider = 'manual'
        user.google_linked_at = None
        user.save()

        logger.info(
            "Google account unlinked",
            extra={'user_id': user.id}
        )

        return user
