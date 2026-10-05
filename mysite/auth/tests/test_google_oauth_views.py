"""View-level tests for the Google OAuth callback, link and unlink endpoints.

Google itself is mocked at the GoogleOAuthService boundary; the views, serializers,
token issuing and response envelope are real. These cover existing accounts, where
the response used to be re-validated as input and failed UserSerializer's
unique-email check (HTTP 500 for every existing user).
"""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from mysite.users.models import User


def _mock_service(user, action="linked"):
    service = MagicMock()
    state = MagicMock()
    state.mark_as_used.return_value = True
    service.validate_state_token.return_value = state
    service.exchange_code_for_token.return_value = {"user_info": {"email": user.email, "sub": "google-123"}}
    service.get_or_create_user.return_value = (user, action)
    service.link_google_account.return_value = user
    service.unlink_google_account.return_value = user
    return service


class GoogleOAuthViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(email="existing@example.com", password="Sup3r-secret-pw")
        self.user.email_verified = True
        self.user.save(update_fields=["email_verified"])

    def test_callback_for_existing_account_returns_tokens(self):
        with patch("mysite.auth.views.google_oauth.callback.GoogleOAuthService", return_value=_mock_service(self.user)):
            response = self.client.post(reverse("auth-google-callback"), {"code": "c", "state": "s"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["data"]
        self.assertTrue(body["tokens"]["access"])
        self.assertEqual(body["user"]["email"], "existing@example.com")
        self.assertEqual(body["account_action"], "linked")
        self.assertIn("refresh_token", response.cookies)

    def test_callback_for_new_account_returns_tokens(self):
        new_user = User.objects.create_user(email="new@example.com", password=None)
        service = _mock_service(new_user, action="created")
        with patch("mysite.auth.views.google_oauth.callback.GoogleOAuthService", return_value=service):
            response = self.client.post(reverse("auth-google-callback"), {"code": "c", "state": "s"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["account_action"], "created")

    def test_link_for_existing_account(self):
        self.client.force_authenticate(self.user)
        with patch("mysite.auth.views.google_oauth.linking.GoogleOAuthService", return_value=_mock_service(self.user)):
            response = self.client.post(reverse("auth-google-link"), {"code": "c", "state": "s"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["user"]["email"], "existing@example.com")

    def test_unlink_for_existing_account(self):
        self.client.force_authenticate(self.user)
        with patch("mysite.auth.views.google_oauth.linking.GoogleOAuthService", return_value=_mock_service(self.user)):
            response = self.client.delete(reverse("auth-google-unlink"), {"password": "Sup3r-secret-pw"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["user"]["email"], "existing@example.com")
