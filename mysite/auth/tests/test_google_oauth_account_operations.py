"""
Google OAuth Account Operations Tests

Tests for user account creation, linking, and unlinking with Google OAuth.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from mysite.auth.serializers import OAuthCallbackRequestSerializer
from mysite.auth.services.google_oauth_service import GoogleOAuthService, UnverifiedAccountError

User = get_user_model()


class TestUserCreation(TestCase):
    """Test creating new users from Google OAuth."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()

    def test_get_or_create_user_new_user(self):
        """Test creating new user from Google OAuth."""
        user, action = self.service.get_or_create_user(
            {
                "sub": "123456789",
                "email": "newuser@gmail.com",
                "given_name": "New",
                "family_name": "User",
            }
        )

        self.assertEqual(action, "created")
        self.assertEqual(user.email, "newuser@gmail.com")
        self.assertEqual(user.google_id, "123456789")
        self.assertTrue(user.email_verified)
        self.assertEqual(user.auth_provider, "google")
        self.assertFalse(user.has_usable_password())


class TestAccountLinkingSecurity(TestCase):
    """Test security aspects of account linking (CRITICAL)."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()

    def test_get_or_create_user_unverified_account_blocks(self):
        """Test that linking to unverified account is blocked (CRITICAL)."""
        existing = User.objects.create_user(
            email="existing@gmail.com",
            password="testpass123",
            email_verified=False,  # UNVERIFIED
        )

        # Should raise error - CRITICAL SECURITY CHECK
        with self.assertRaises(UnverifiedAccountError):
            self.service.get_or_create_user({"sub": "123456789", "email": "existing@gmail.com"})

        existing.refresh_from_db()
        self.assertIsNone(existing.google_id)

    def test_get_or_create_user_existing_verified_links(self):
        """Test linking Google to existing verified account."""
        User.objects.create_user(
            email="verified@gmail.com",
            password="testpass123",
            email_verified=True,  # VERIFIED
        )

        user, action = self.service.get_or_create_user({"sub": "123456789", "email": "verified@gmail.com"})

        self.assertEqual(action, "linked")
        self.assertEqual(user.email, "verified@gmail.com")
        self.assertEqual(user.google_id, "123456789")
        self.assertEqual(user.auth_provider, "hybrid")


class TestAccountLinkingOperations(TestCase):
    """Test linking and unlinking Google accounts to existing users."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()

    def test_link_google_account_success(self):
        """Test linking Google account to authenticated user."""
        # Create user
        user = User.objects.create_user(email="test@gmail.com", password="testpass123", email_verified=True)

        # Link Google account
        google_user_info = {
            "sub": "987654321",
            "email": "test@gmail.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }

        updated_user = self.service.link_google_account(user=user, google_user_info=google_user_info)

        self.assertEqual(updated_user.google_id, "987654321")
        self.assertEqual(updated_user.auth_provider, "hybrid")
        self.assertIsNotNone(updated_user.google_linked_at)

    def test_unlink_google_account_success(self):
        """Test unlinking Google account."""
        # Create user with Google linked
        user = User.objects.create_user(
            email="test@gmail.com",
            password="testpass123",
            email_verified=True,
            google_id="123456789",
            auth_provider="hybrid",
        )

        # Unlink
        updated_user = self.service.unlink_google_account(user)

        self.assertIsNone(updated_user.google_id)
        self.assertEqual(updated_user.auth_provider, "manual")
        self.assertIsNone(updated_user.google_linked_at)


class TestNewGoogleUserLanguage(TestCase):
    """The callback's optional ``language`` applies only to newly created accounts."""

    google_user_info = {
        "sub": "555000111",
        "email": "lang@gmail.com",
        "given_name": "Lang",
        "family_name": "User",
    }

    def setUp(self):
        self.service = GoogleOAuthService()

    def test_new_user_gets_requested_language(self):
        user, action = self.service.get_or_create_user(self.google_user_info, language="es")

        self.assertEqual(action, "created")
        self.assertEqual(user.language, "es")

    def test_new_user_gets_italian(self):
        user, action = self.service.get_or_create_user(self.google_user_info, language="it")

        self.assertEqual(action, "created")
        self.assertEqual(user.language, "it")

    def test_new_user_without_language_uses_default(self):
        user, action = self.service.get_or_create_user(self.google_user_info)

        self.assertEqual(action, "created")
        self.assertEqual(user.language, "en")

    def test_existing_user_language_is_not_overwritten(self):
        User.objects.create_user(email="lang@gmail.com", password="testpass123", email_verified=True, language="en")

        user, action = self.service.get_or_create_user(self.google_user_info, language="es")

        self.assertEqual(action, "linked")
        self.assertEqual(user.language, "en")

    def test_callback_serializer_drops_unsupported_language(self):
        valid = OAuthCallbackRequestSerializer(data={"code": "c", "state": "s", "language": "es"})
        italian = OAuthCallbackRequestSerializer(data={"code": "c", "state": "s", "language": "it"})
        unsupported = OAuthCallbackRequestSerializer(data={"code": "c", "state": "s", "language": "fr"})
        missing = OAuthCallbackRequestSerializer(data={"code": "c", "state": "s"})

        for serializer in (valid, italian, unsupported, missing):
            self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(valid.validated_data["language"], "es")
        self.assertEqual(italian.validated_data["language"], "it")
        self.assertIsNone(unsupported.validated_data["language"])
        self.assertNotIn("language", missing.validated_data)
