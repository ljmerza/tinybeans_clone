"""Sign in with Apple: service and views.

Apple is faked at two seams: ``requests.post`` (the token endpoint) and the
JWKS client (Apple's public keys). Everything else - state handling, JWT
signing/verification, account rules, views and envelopes - runs for real.
"""

import time
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from mysite.auth.models import AppleOAuthState
from mysite.auth.services.apple_oauth_service import (
    AppleAccountAlreadyLinkedError,
    AppleOAuthNotConfiguredError,
    AppleOAuthService,
    InvalidRedirectURIError,
    OAuthError,
    UnverifiedAccountError,
)
from mysite.auth.views.passwords import _enable_password_login
from mysite.users.models import User

CLIENT_ID = "com.example.circles.web"
RETURN_URI = "http://localhost:3000/auth/apple-callback"

_APPLE_KEY = ec.generate_private_key(ec.SECP256R1())
_APPLE_KEY_PEM = _APPLE_KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
# Stands in for the key Apple signs ID tokens with.
_ID_TOKEN_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

APPLE_SETTINGS = {
    "APPLE_OAUTH_CLIENT_ID": CLIENT_ID,
    "APPLE_OAUTH_TEAM_ID": "TEAM123456",
    "APPLE_OAUTH_KEY_ID": "KEY1234567",
    "APPLE_OAUTH_PRIVATE_KEY": _APPLE_KEY_PEM,
    "APPLE_OAUTH_REDIRECT_URI": "https://circles.example.com/api/auth/apple/return/",
    "APPLE_OAUTH_ALLOWED_RETURN_URIS": [RETURN_URI],
}


def make_id_token(nonce, **overrides):
    now = int(time.time())
    claims = {
        "iss": "https://appleid.apple.com",
        "aud": CLIENT_ID,
        "iat": now,
        "exp": now + 600,
        "sub": "001234.apple-user",
        "email": "kid@privaterelay.appleid.com",
        "email_verified": "true",
        "is_private_email": "true",
        "nonce": nonce,
    }
    claims.update(overrides)
    return jwt.encode(claims, _ID_TOKEN_KEY, algorithm="RS256", headers={"kid": "apple-kid"})


def fake_jwks_client():
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = MagicMock(key=_ID_TOKEN_KEY.public_key(), algorithm_name="RS256")
    return client


def token_response(id_token=None, status_code=200, body=None):
    response = MagicMock(status_code=status_code)
    response.json.return_value = body if body is not None else {"id_token": id_token}
    return response


def make_state(**overrides):
    service = AppleOAuthService()
    service.generate_auth_url(RETURN_URI, "127.0.0.1", "pytest")
    state = AppleOAuthState.objects.latest("created_at")
    for field, value in overrides.items():
        setattr(state, field, value)
    if overrides:
        state.save()
    return state


@override_settings(**APPLE_SETTINGS)
@patch("mysite.auth.services.apple_oauth_service._get_jwks_client", fake_jwks_client)
class AppleOAuthServiceTests(TestCase):
    def setUp(self):
        self.service = AppleOAuthService()

    def test_client_secret_is_es256_jwt_with_apple_claims(self):
        secret = self.service.build_client_secret()

        header = jwt.get_unverified_header(secret)
        self.assertEqual(header["alg"], "ES256")
        self.assertEqual(header["kid"], "KEY1234567")
        claims = jwt.decode(secret, _APPLE_KEY.public_key(), algorithms=["ES256"], audience="https://appleid.apple.com")
        self.assertEqual(claims["iss"], "TEAM123456")
        self.assertEqual(claims["sub"], CLIENT_ID)
        self.assertLessEqual(claims["exp"] - claims["iat"], 15777000)

    def test_auth_url_uses_form_post_and_stores_state(self):
        result = self.service.generate_auth_url(RETURN_URI, "127.0.0.1", "pytest")

        query = parse_qs(urlparse(result["url"]).query)
        self.assertTrue(result["url"].startswith("https://appleid.apple.com/auth/authorize?"))
        self.assertEqual(query["response_mode"], ["form_post"])
        self.assertEqual(query["scope"], ["name email"])
        self.assertEqual(query["redirect_uri"], [APPLE_SETTINGS["APPLE_OAUTH_REDIRECT_URI"]])
        state = AppleOAuthState.objects.get(state_token=result["state"])
        self.assertEqual(query["nonce"], [state.nonce])
        self.assertEqual(state.return_uri, RETURN_URI)

    def test_auth_url_rejects_unlisted_return_uri(self):
        with self.assertRaises(InvalidRedirectURIError):
            self.service.generate_auth_url("https://evil.example.com/auth/apple-callback", "127.0.0.1", "pytest")

    def test_records_name_from_first_authorization(self):
        state = make_state()
        AppleOAuthService.record_authorization_user(
            state, '{"name": {"firstName": " Ada ", "lastName": "Lovelace"}, "email": "x@y.z"}'
        )
        state.refresh_from_db()
        self.assertEqual((state.first_name, state.last_name), ("Ada", "Lovelace"))

    def test_ignores_malformed_user_payload(self):
        state = make_state()
        AppleOAuthService.record_authorization_user(state, "not json")
        state.refresh_from_db()
        self.assertEqual(state.first_name, "")

    def test_verify_id_token_accepts_valid_token(self):
        claims = self.service.verify_id_token(make_id_token("n1"), "n1")
        self.assertEqual(claims["sub"], "001234.apple-user")

    def test_verify_id_token_rejects_nonce_mismatch(self):
        with self.assertRaisesMessage(OAuthError, "Nonce mismatch"):
            self.service.verify_id_token(make_id_token("other"), "n1")

    def test_verify_id_token_rejects_wrong_audience(self):
        with self.assertRaises(OAuthError):
            self.service.verify_id_token(make_id_token("n1", aud="com.someone.else"), "n1")

    def test_verify_id_token_rejects_wrong_issuer(self):
        with self.assertRaises(OAuthError):
            self.service.verify_id_token(make_id_token("n1", iss="https://evil.example.com"), "n1")

    def test_verify_id_token_rejects_expired_token(self):
        with self.assertRaises(OAuthError):
            self.service.verify_id_token(make_id_token("n1", exp=int(time.time()) - 3600), "n1")

    def test_exchange_returns_identity_with_parsed_claims_and_stored_name(self):
        state = make_state(first_name="Ada", last_name="Lovelace")
        with patch("mysite.auth.services.apple_oauth_service.requests.post") as post:
            post.return_value = token_response(make_id_token(state.nonce))
            identity = self.service.exchange_code_for_identity("code-1", state)

        sent = post.call_args.kwargs["data"]
        self.assertEqual(sent["grant_type"], "authorization_code")
        self.assertEqual(sent["redirect_uri"], APPLE_SETTINGS["APPLE_OAUTH_REDIRECT_URI"])
        self.assertTrue(identity["email_verified"])
        self.assertTrue(identity["is_private_email"])
        self.assertEqual(identity["first_name"], "Ada")

    def test_exchange_raises_when_apple_rejects_code(self):
        state = make_state()
        with patch("mysite.auth.services.apple_oauth_service.requests.post") as post:
            post.return_value = token_response(status_code=400, body={"error": "invalid_grant"})
            with self.assertRaisesMessage(OAuthError, "invalid_grant"):
                self.service.exchange_code_for_identity("bad", state)

    # -- account rules ---------------------------------------------------------

    def identity(self, **overrides):
        identity = {
            "sub": "001234.apple-user",
            "email": "kid@privaterelay.appleid.com",
            "email_verified": True,
            "is_private_email": True,
            "first_name": "Ada",
            "last_name": "Lovelace",
        }
        identity.update(overrides)
        return identity

    def test_creates_passwordless_apple_user(self):
        user, action = self.service.get_or_create_user(self.identity(), language="es")

        self.assertEqual(action, "created")
        self.assertEqual(user.auth_provider, "apple")
        self.assertEqual((user.first_name, user.last_name), ("Ada", "Lovelace"))
        self.assertTrue(user.email_verified)
        self.assertFalse(user.password_login_enabled)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.language, "es")

    def test_logs_in_existing_apple_user(self):
        existing = User.objects.create_user(
            email="other@example.com", password="pw-123456789", apple_id="001234.apple-user"
        )
        user, action = self.service.get_or_create_user(self.identity())
        self.assertEqual((user.id, action), (existing.id, "login"))

    def test_links_verified_account_with_same_email(self):
        existing = User.objects.create_user(email="ada@example.com", password="pw-123456789", email_verified=True)
        user, action = self.service.get_or_create_user(self.identity(email="ada@example.com", is_private_email=False))

        self.assertEqual((user.id, action), (existing.id, "linked"))
        self.assertEqual(user.apple_id, "001234.apple-user")
        self.assertEqual(user.auth_provider, "hybrid")

    def test_blocks_unverified_account_with_same_email(self):
        User.objects.create_user(email="ada@example.com", password="pw-123456789", email_verified=False)
        with self.assertRaises(UnverifiedAccountError):
            self.service.get_or_create_user(self.identity(email="ada@example.com"))

    def test_refuses_new_user_without_email(self):
        with self.assertRaises(OAuthError):
            self.service.get_or_create_user(self.identity(email=""))

    def test_link_accepts_relay_email_that_differs_from_account(self):
        user = User.objects.create_user(email="ada@example.com", password="pw-123456789", email_verified=True)
        linked = self.service.link_apple_account(user, self.identity())
        self.assertEqual(linked.apple_email, "kid@privaterelay.appleid.com")
        self.assertEqual(linked.auth_provider, "hybrid")

    def test_link_rejects_apple_id_owned_by_someone_else(self):
        User.objects.create_user(email="other@example.com", password="pw-123456789", apple_id="001234.apple-user")
        user = User.objects.create_user(email="ada@example.com", password="pw-123456789")
        with self.assertRaises(AppleAccountAlreadyLinkedError):
            self.service.link_apple_account(user, self.identity())

    def test_unlink_requires_password_login(self):
        user, _ = self.service.get_or_create_user(self.identity())
        with self.assertRaises(OAuthError):
            AppleOAuthService.unlink_apple_account(user)

    def test_unlink_keeps_hybrid_when_google_still_linked(self):
        user = User.objects.create_user(
            email="ada@example.com", password="pw-123456789", apple_id="a1", google_id="g1", auth_provider="hybrid"
        )
        AppleOAuthService.unlink_apple_account(user)
        user.refresh_from_db()
        self.assertIsNone(user.apple_id)
        self.assertEqual(user.auth_provider, "hybrid")

    def test_google_unlink_keeps_hybrid_when_apple_still_linked(self):
        from mysite.auth.services.oauth.account_linking_service import AccountLinkingService

        user = User.objects.create_user(
            email="ada@example.com", password="pw-123456789", apple_id="a1", google_id="g1", auth_provider="hybrid"
        )
        AccountLinkingService().unlink_google_account(user)
        user.refresh_from_db()
        self.assertIsNone(user.google_id)
        self.assertEqual(user.auth_provider, "hybrid")

    def test_setting_a_password_makes_apple_user_hybrid(self):
        user, _ = self.service.get_or_create_user(self.identity())
        self.assertIn("auth_provider", _enable_password_login(user))
        self.assertEqual(user.auth_provider, "hybrid")


class AppleOAuthDisabledTests(TestCase):
    """Test settings carry no Apple credentials: everything stays off."""

    def setUp(self):
        cache.clear()

    def test_service_refuses_to_start(self):
        with self.assertRaises(AppleOAuthNotConfiguredError):
            AppleOAuthService()

    def test_providers_endpoint_hides_apple(self):
        response = APIClient().get(reverse("auth-oauth-providers"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"google": True, "apple": False})

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="")
    def test_providers_endpoint_hides_google_without_credentials(self):
        response = APIClient().get(reverse("auth-oauth-providers"))
        self.assertEqual(response.json()["data"]["google"], False)

    @override_settings(OAUTH_ALLOWED_REDIRECT_URIS=[])
    def test_providers_endpoint_hides_google_without_allowed_redirect(self):
        response = APIClient().get(reverse("auth-oauth-providers"))
        self.assertEqual(response.json()["data"]["google"], False)

    @override_settings(**{**APPLE_SETTINGS, "APPLE_OAUTH_ALLOWED_RETURN_URIS": []})
    def test_providers_endpoint_hides_apple_without_allowed_return_uri(self):
        response = APIClient().get(reverse("auth-oauth-providers"))
        self.assertEqual(response.json()["data"]["apple"], False)

    def test_initiate_reports_disabled(self):
        response = APIClient().post(reverse("auth-apple-initiate"), {"redirect_uri": RETURN_URI}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "apple_oauth_disabled")


@override_settings(**APPLE_SETTINGS)
@patch("mysite.auth.services.apple_oauth_service._get_jwks_client", fake_jwks_client)
class AppleOAuthViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()

    def initiate(self):
        response = self.api.post(reverse("auth-apple-initiate"), {"redirect_uri": RETURN_URI}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["data"]["state"]

    def apple_posts_back(self, data):
        # Apple's POST is cross-site and carries no CSRF token.
        return Client(enforce_csrf_checks=True).post(reverse("auth-apple-return"), data)

    def test_providers_endpoint_shows_apple(self):
        self.assertTrue(self.api.get(reverse("auth-oauth-providers")).json()["data"]["apple"])

    def test_return_redirects_to_spa_with_code_in_fragment(self):
        state = self.initiate()
        response = self.apple_posts_back(
            {"state": state, "code": "code-1", "user": '{"name": {"firstName": "Ada", "lastName": "Lovelace"}}'}
        )

        self.assertEqual(response.status_code, 303)
        location = urlparse(response["Location"])
        self.assertEqual(f"{location.scheme}://{location.netloc}{location.path}", RETURN_URI)
        self.assertEqual(location.query, "")
        self.assertEqual(parse_qs(location.fragment), {"code": ["code-1"], "state": [state]})
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertEqual(AppleOAuthState.objects.get(state_token=state).first_name, "Ada")

    def test_return_passes_apple_error_through(self):
        state = self.initiate()
        response = self.apple_posts_back({"state": state, "error": "user_cancelled_authorize"})
        fragment = parse_qs(urlparse(response["Location"]).fragment)
        self.assertEqual(fragment["error"], ["user_cancelled_authorize"])

    def test_return_with_unknown_state_goes_to_fallback(self):
        response = self.apple_posts_back({"state": "nope", "code": "code-1"})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response["Location"], "/auth/apple-callback#error=invalid_state")

    def test_return_rejects_get(self):
        self.assertEqual(Client().get(reverse("auth-apple-return")).status_code, 405)

    def test_full_sign_up_then_replay_is_rejected(self):
        state = self.initiate()
        self.apple_posts_back(
            {"state": state, "code": "code-1", "user": '{"name": {"firstName": "Ada", "lastName": "Lovelace"}}'}
        )
        nonce = AppleOAuthState.objects.get(state_token=state).nonce

        with patch("mysite.auth.services.apple_oauth_service.requests.post") as post:
            post.return_value = token_response(make_id_token(nonce))
            response = self.api.post(reverse("auth-apple-callback"), {"code": "code-1", "state": state}, format="json")
            replay = self.api.post(reverse("auth-apple-callback"), {"code": "code-1", "state": state}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["data"]
        self.assertEqual(body["account_action"], "created")
        self.assertTrue(body["tokens"]["access"])
        self.assertIn("refresh_token", response.cookies)
        user = User.objects.get(apple_id="001234.apple-user")
        self.assertEqual((user.first_name, user.email), ("Ada", "kid@privaterelay.appleid.com"))

        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.json()["error"], "invalid_state_token")
        self.assertEqual(post.call_count, 1)

    def test_callback_with_bad_id_token_fails_cleanly(self):
        state = self.initiate()
        with patch("mysite.auth.services.apple_oauth_service.requests.post") as post:
            post.return_value = token_response(make_id_token("wrong-nonce"))
            response = self.api.post(reverse("auth-apple-callback"), {"code": "code-1", "state": state}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "oauth_error")
        self.assertFalse(User.objects.filter(apple_id="001234.apple-user").exists())

    def test_link_conflict_returns_409(self):
        User.objects.create_user(email="other@example.com", password="pw-123456789", apple_id="001234.apple-user")
        user = User.objects.create_user(email="ada@example.com", password="pw-123456789", email_verified=True)
        self.api.force_authenticate(user)
        state = self.initiate()
        nonce = AppleOAuthState.objects.get(state_token=state).nonce

        with patch("mysite.auth.services.apple_oauth_service.requests.post") as post:
            post.return_value = token_response(make_id_token(nonce))
            response = self.api.post(reverse("auth-apple-link"), {"code": "code-1", "state": state}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "apple_account_already_linked")

    def test_unlink_with_password(self):
        user = User.objects.create_user(
            email="ada@example.com", password="pw-123456789", email_verified=True, apple_id="a1", auth_provider="hybrid"
        )
        self.api.force_authenticate(user)
        response = self.api.delete(reverse("auth-apple-unlink"), {"password": "pw-123456789"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        user.refresh_from_db()
        self.assertIsNone(user.apple_id)
        self.assertEqual(user.auth_provider, "manual")
