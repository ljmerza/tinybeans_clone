"""Token management API: list, create with an emailed re-auth code, revoke; the notice email; Django admin."""

import re
from datetime import timedelta
from unittest.mock import patch

import pyotp
import pytest
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.agent_api import tokens
from mysite.agent_api.admin import CircleApiTokenAdmin
from mysite.agent_api.models import CircleApiToken, RevokeReason
from mysite.agent_api.serializers import ApiTokenCreateSerializer
from mysite.auth.services import reauth_service
from mysite.auth.services.reauth_service import send_reauth_code
from mysite.circles.models import Circle

from .helpers import audit_actions, bearer_client, captured_logs, create_token

User = get_user_model()
CODE_RE = re.compile(r"verification code is: (\d{6})")
TOKEN_KEYS = {
    "id",
    "name",
    "display_prefix",
    "can_suggest",
    "status",
    "created_by",
    "created_at",
    "expires_at",
    "last_used_at",
    "last_used_ip",
    "revoked_at",
    "revoked_reason",
}


def list_url(circle):
    return reverse("circle-api-token-list", args=[circle.id])


def detail_url(circle, token):
    return reverse("circle-api-token-detail", args=[circle.id, token.id])


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def emailed_code(user):
    send_reauth_code(user)
    sent = [m for m in mail.outbox if m.to == [user.email] and CODE_RE.search(m.body)]
    mail.outbox = []
    return CODE_RE.search(sent[-1].body).group(1)


def wrong(code):
    return f"{(int(code) + 1) % 10**6:06d}"


def body(code, **overrides):
    return {"name": "Claude Code", "can_suggest": False, "expires_at": None, "code": code, **overrides}


@pytest.fixture
def admin_client(admin):
    return client_for(admin)


@pytest.mark.django_db
class TestPermissions:
    def test_member_is_forbidden(self, circle, member):
        client = client_for(member)

        assert client.get(list_url(circle)).status_code == status.HTTP_403_FORBIDDEN
        assert client.post(list_url(circle), body("123456"), format="json").status_code == status.HTTP_403_FORBIDDEN

    def test_admin_of_another_circle_is_forbidden(self, circle, token):
        stranger = User.objects.create_user(email="stranger@example.com", password="x", email_verified=True)
        Circle.objects.create(name="Stranger Family", created_by=stranger)
        client = client_for(stranger)

        assert client.get(list_url(circle)).status_code == status.HTTP_403_FORBIDDEN
        assert client.delete(detail_url(circle, token)).status_code == status.HTTP_403_FORBIDDEN
        assert CircleApiToken.objects.get(pk=token.pk).revoked_at is None

    def test_superuser_who_is_not_a_member_is_forbidden(self, circle, token):
        boss = User.objects.create_superuser(email="boss@example.com", password="x", email_verified=True)
        client = client_for(boss)

        assert client.get(list_url(circle)).status_code == status.HTTP_403_FORBIDDEN
        assert client.post(list_url(circle), body("123456"), format="json").status_code == status.HTTP_403_FORBIDDEN
        assert client.delete(detail_url(circle, token)).status_code == status.HTTP_403_FORBIDDEN

    def test_anonymous_is_rejected(self, circle):
        assert APIClient().get(list_url(circle)).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestList:
    def test_lists_tokens_without_secrets(self, admin_client, circle, admin, token, raw):
        revoked, _ = create_token(circle, admin, name="Old")
        CircleApiToken.objects.filter(pk=revoked.pk).update(revoked_at=timezone.now(), revoked_reason="manual")

        response = admin_client.get(list_url(circle))

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["agent_api_enabled"] is True
        assert [item["name"] for item in data["tokens"]] == ["Old", "Laptop"]
        assert all(set(item) == TOKEN_KEYS for item in data["tokens"])
        assert [item["status"] for item in data["tokens"]] == ["revoked", "active"]
        assert data["tokens"][1]["created_by"] == {"id": admin.id, "display_name": "Ada Admin"}
        assert raw not in response.content.decode()
        assert token.token_hash not in response.content.decode()

    def test_reports_the_kill_switch(self, admin_client, circle, settings):
        settings.AGENT_API_ENABLED = False

        assert admin_client.get(list_url(circle)).json()["agent_api_enabled"] is False

    def test_only_this_circles_tokens(self, admin_client, admin, circle, other_circle, token):
        create_token(other_circle, admin, name="Elsewhere")

        names = [item["name"] for item in admin_client.get(list_url(circle)).json()["tokens"]]

        assert names == ["Laptop"]


@pytest.mark.django_db
class TestCreate:
    def test_creates_and_shows_the_plaintext_once(
        self, admin_client, admin, circle, django_capture_on_commit_callbacks
    ):
        code = emailed_code(admin)

        with django_capture_on_commit_callbacks(execute=True):
            response = admin_client.post(list_url(circle), body(code, can_suggest=True, name="  MCP  "), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response["Cache-Control"] == "no-store"
        data = response.json()
        plaintext = data["plaintext"]
        assert tokens.is_well_formed(plaintext)
        assert set(data["token"]) == TOKEN_KEYS
        assert data["token"]["name"] == "MCP"
        assert data["token"]["can_suggest"] is True
        assert data["token"]["expires_at"] is None
        token = CircleApiToken.objects.get(pk=data["token"]["id"])
        assert token.token_hash == tokens.hash_token(plaintext)
        assert token.created_by == admin
        # It works, and the list never shows it again.
        assert bearer_client(plaintext).get(reverse("agent_api:whoami")).status_code == status.HTTP_200_OK
        assert plaintext not in admin_client.get(list_url(circle)).content.decode()

    def test_notice_goes_to_every_admin(
        self, admin_client, admin, circle, co_admin, member, django_capture_on_commit_callbacks
    ):
        code = emailed_code(admin)

        with django_capture_on_commit_callbacks(execute=True):
            response = admin_client.post(list_url(circle), body(code), format="json")

        plaintext = response.json()["plaintext"]
        notices = [m for m in mail.outbox if "API token" in m.subject]
        assert sorted(m.to[0] for m in notices) == sorted([admin.email, co_admin.email])
        for message in notices:
            assert "Claude Code" in message.body
            assert response.json()["token"]["display_prefix"] in message.body
            assert plaintext not in message.body
            assert plaintext[12:] not in message.body
            assert "Never" in message.body

    def test_audited(self, admin_client, admin, circle, caplog):
        code = emailed_code(admin)
        with captured_logs(caplog, "mysite.audit"):
            response = admin_client.post(list_url(circle), body(code), format="json")

        assert "api_token.create" in audit_actions(caplog)
        plaintext = response.json()["plaintext"]
        assert all(plaintext not in f"{r.__dict__}" for r in caplog.records)

    def test_expiry(self, admin_client, admin, circle):
        expires = timezone.now() + timedelta(days=90)

        response = admin_client.post(
            list_url(circle), body(emailed_code(admin), expires_at=expires.isoformat()), format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert CircleApiToken.objects.get().expires_at == expires

    @pytest.mark.parametrize("delta", [timedelta(days=-1), timedelta(minutes=30)])
    def test_expiry_must_be_an_hour_away(self, admin_client, admin, circle, delta):
        expires = (timezone.now() + delta).isoformat()

        response = admin_client.post(list_url(circle), body("123456", expires_at=expires), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CircleApiToken.objects.exists()

    def test_missing_code(self, admin_client, circle):
        payload = body("x")
        del payload["code"]

        response = admin_client.post(list_url(circle), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CircleApiToken.objects.exists()

    def test_wrong_code(self, admin_client, admin, circle):
        code = emailed_code(admin)

        response = admin_client.post(list_url(circle), body(wrong(code)), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["messages"] == [{"i18n_key": "errors.reauth_invalid_code", "context": {"field": "code"}}]
        assert not CircleApiToken.objects.exists()

    def test_code_is_single_use(self, admin_client, admin, circle):
        code = emailed_code(admin)
        assert admin_client.post(list_url(circle), body(code), format="json").status_code == 201

        response = admin_client.post(list_url(circle), body(code, name="Again"), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CircleApiToken.objects.count() == 1

    def test_validation_error_does_not_use_up_the_code(self, admin_client, admin, circle):
        code = emailed_code(admin)

        bad = admin_client.post(list_url(circle), body(code, name=""), format="json")
        good = admin_client.post(list_url(circle), body(code), format="json")

        assert bad.status_code == status.HTTP_400_BAD_REQUEST
        assert good.status_code == status.HTTP_201_CREATED

    def test_name_too_long(self, admin_client, circle):
        response = admin_client.post(list_url(circle), body("123456", name="x" * 101), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_totp_reenrolled_with_only_a_session_cannot_create_a_token(self, admin_client, admin, circle):
        # A stolen session can enrol its own authenticator; only the emailed code counts.
        setup = admin_client.post(reverse("2fa-setup"), {"method": "totp"}, format="json")
        totp = pyotp.TOTP(setup.json()["data"]["secret"])
        assert admin_client.post(reverse("2fa-verify-setup"), {"code": totp.now()}, format="json").status_code == 200
        totp_code = totp.now()
        with patch.object(reauth_service.secrets, "randbelow", return_value=(int(totp_code) + 1) % 10**6):
            send_reauth_code(admin)

        response = admin_client.post(list_url(circle), body(totp_code), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CircleApiToken.objects.exists()

    def test_cap(self, admin_client, admin, circle, settings):
        settings.AGENT_API_MAX_TOKENS_PER_CIRCLE = 2
        create_token(circle, admin, name="One")
        expired, _ = create_token(circle, admin, name="Expired")
        CircleApiToken.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(days=1))
        create_token(circle, admin, name="Two")
        code = emailed_code(admin)

        response = admin_client.post(list_url(circle), body(code), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"] == "api_token_limit"
        assert response.json()["messages"] == [{"i18n_key": "errors.api_token_limit", "context": {"max": 2}}]
        # The cap is checked before the code, so the code still works once a token is revoked.
        CircleApiToken.objects.filter(name="One").update(revoked_at=timezone.now())
        assert admin_client.post(list_url(circle), body(code), format="json").status_code == 201

    def test_rate_limited(self, admin_client, circle, settings):
        settings.RATELIMIT_ENABLE = True
        responses = [admin_client.post(list_url(circle), body("000000"), format="json") for _ in range(6)]

        assert [r.status_code for r in responses] == [400] * 5 + [429]
        assert responses[-1].json()["error"] == "rate_limit_exceeded"


@pytest.mark.django_db
class TestRevoke:
    def test_any_admin_can_revoke_idempotently(self, circle, co_admin, token, raw, caplog):
        client = client_for(co_admin)

        with captured_logs(caplog, "mysite.audit"):
            first = client.delete(detail_url(circle, token))
            second = client.delete(detail_url(circle, token))

        assert first.status_code == second.status_code == status.HTTP_204_NO_CONTENT
        token.refresh_from_db()
        assert (token.revoked_reason, token.revoked_by) == (RevokeReason.MANUAL, co_admin)
        assert audit_actions(caplog).count("api_token.revoke") == 1
        assert bearer_client(raw).get(reverse("agent_api:whoami")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_of_another_circle_is_a_404(self, admin_client, admin, circle, other_circle):
        elsewhere, _ = create_token(other_circle, admin)

        response = admin_client.delete(detail_url(circle, elsewhere))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert CircleApiToken.objects.get(pk=elsewhere.pk).revoked_at is None


@pytest.mark.django_db
class TestSerializerLengths:
    def test_name_matches_the_model_column(self):
        assert ApiTokenCreateSerializer().fields["name"].max_length == CircleApiToken._meta.get_field("name").max_length


@pytest.mark.django_db
class TestDjangoAdmin:
    def test_read_only_without_the_hash(self, token):
        model_admin = CircleApiTokenAdmin(CircleApiToken, django_admin.site)
        request = RequestFactory().get("/")

        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_change_permission(request, token) is False
        assert model_admin.has_delete_permission(request, token) is False
        assert "token_hash" in model_admin.exclude
        assert "token_hash" not in model_admin.readonly_fields

    def test_revoke_action(self, token, admin):
        boss = User.objects.create_superuser(email="boss@example.com", password="x")
        model_admin = CircleApiTokenAdmin(CircleApiToken, django_admin.site)
        request = RequestFactory().post("/")
        request.user = boss
        model_admin.message_user = lambda *args, **kwargs: None

        model_admin.revoke_selected(request, CircleApiToken.objects.all())

        token.refresh_from_db()
        assert (token.revoked_reason, token.revoked_by) == (RevokeReason.MANUAL, boss)

    def test_revoke_action_on_the_changelist(self, token, client):
        boss = User.objects.create_superuser(email="boss@example.com", password="x")
        client.force_login(boss)
        url = reverse("admin:agent_api_circleapitoken_changelist")

        assert client.get(url).status_code == status.HTTP_200_OK
        response = client.post(url, {"action": "revoke_selected", "_selected_action": [token.pk]})

        assert response.status_code == status.HTTP_302_FOUND
        token.refresh_from_db()
        assert (token.revoked_reason, token.revoked_by) == (RevokeReason.MANUAL, boss)
