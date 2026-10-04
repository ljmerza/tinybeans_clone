"""The Google OAuth redirect allow-list comes from OAUTH_ALLOWED_REDIRECT_URIS."""

import os
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.tests.helpers import response_payload
from mysite.config.settings.auth import _get_oauth_allowed_redirect_uris

APP_CALLBACK = "https://app.example.com/auth/google-callback"
DEV_CALLBACK = "https://dev.example.com/auth/google-callback"


class OAuthAllowedRedirectURISettingTests(SimpleTestCase):
    def test_comma_separated_env_value(self):
        with patch.dict(os.environ, {"OAUTH_ALLOWED_REDIRECT_URIS": f" {APP_CALLBACK}, ,{DEV_CALLBACK} "}):
            self.assertEqual(_get_oauth_allowed_redirect_uris(debug=False), [APP_CALLBACK, DEV_CALLBACK])

    def test_unset_defaults_to_localhost_only_in_debug(self):
        with patch.dict(os.environ, {"OAUTH_ALLOWED_REDIRECT_URIS": ""}):
            dev_defaults = _get_oauth_allowed_redirect_uris(debug=True)
            prod_defaults = _get_oauth_allowed_redirect_uris(debug=False)
        self.assertIn("http://localhost:3053/auth/google-callback", dev_defaults)
        self.assertTrue(all(urlparse(uri).hostname in {"localhost", "127.0.0.1"} for uri in dev_defaults))
        self.assertEqual(prod_defaults, [])


@override_settings(OAUTH_ALLOWED_REDIRECT_URIS=[APP_CALLBACK])
class OAuthInitiateRedirectURITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_configured_redirect_uri_is_sent_to_google(self):
        response = self.client.post(reverse("auth-google-initiate"), {"redirect_uri": APP_CALLBACK}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        google_url = urlparse(response_payload(response)["google_oauth_url"])
        self.assertEqual(parse_qs(google_url.query)["redirect_uri"], [APP_CALLBACK])

    def test_unlisted_redirect_uri_is_rejected(self):
        response = self.client.post(
            reverse("auth-google-initiate"),
            {"redirect_uri": "https://evil.example.net/auth/google-callback"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"], "invalid_redirect_uri")
