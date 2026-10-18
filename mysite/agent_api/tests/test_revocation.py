"""Tokens are revoked when their creator stops being an admin, leaves, or changes or resets their password."""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.agent_api import services, signals
from mysite.agent_api.models import CircleApiToken, RevokeReason
from mysite.auth.token_utils import store_token
from mysite.circles.models import CircleMembership
from mysite.users.models import UserRole

from .helpers import audit_actions, captured_logs, create_token

NEW_PASSWORD = "Fresh-Lantern-42"


def reload(token):
    token.refresh_from_db()
    return token


@pytest.mark.django_db
class TestMembershipSignals:
    def test_demotion_revokes_only_that_circles_tokens(self, admin, circle, other_circle, token):
        other_token, _ = create_token(other_circle, admin)
        membership = CircleMembership.objects.get(user=admin, circle=circle)

        membership.role = UserRole.CIRCLE_MEMBER
        membership.save()

        assert reload(token).revoked_reason == RevokeReason.CREATOR_NOT_ADMIN
        assert reload(other_token).revoked_at is None

    def test_re_promotion_does_not_revive(self, admin, circle, token):
        membership = CircleMembership.objects.get(user=admin, circle=circle)
        membership.role = UserRole.CIRCLE_MEMBER
        membership.save()
        membership.role = UserRole.CIRCLE_ADMIN
        membership.save()

        assert reload(token).revoked_reason == RevokeReason.CREATOR_NOT_ADMIN

    def test_other_admins_tokens_are_untouched(self, circle, co_admin, member, token):
        membership = CircleMembership.objects.get(user=co_admin, circle=circle)
        membership.role = UserRole.CIRCLE_MEMBER
        membership.save()

        assert reload(token).revoked_at is None

    def test_removal_revokes(self, circle, co_admin):
        token, _ = create_token(circle, co_admin)

        CircleMembership.objects.get(user=co_admin, circle=circle).delete()

        assert reload(token).revoked_reason == RevokeReason.CREATOR_REMOVED

    def test_deleting_the_circle_logs_no_auto_revoke(self, circle, token, caplog):
        with captured_logs(caplog, "mysite.audit"):
            circle.delete()

        assert "api_token.auto_revoke" not in audit_actions(caplog)
        assert not CircleApiToken.objects.exists()

    def test_removal_during_a_circle_delete_skips_the_revoke(self, admin, circle, token, caplog):
        # Django deletes the tokens before the memberships, so the delete above can't
        # show the guard; call the receiver as that cascade would.
        membership = CircleMembership.objects.get(user=admin, circle=circle)
        with captured_logs(caplog, "mysite.audit"):
            signals.revoke_tokens_on_removal(CircleMembership, membership, origin=circle)

        assert reload(token).revoked_at is None
        assert "api_token.auto_revoke" not in audit_actions(caplog)

    def test_removal_outside_a_circle_delete_revokes(self, admin, circle, token):
        membership = CircleMembership.objects.get(user=admin, circle=circle)

        signals.revoke_tokens_on_removal(CircleMembership, membership, origin=membership)

        assert reload(token).revoked_reason == RevokeReason.CREATOR_REMOVED

    def test_auto_revoke_is_audited(self, admin, circle, token, caplog):
        membership = CircleMembership.objects.get(user=admin, circle=circle)
        membership.role = UserRole.CIRCLE_MEMBER
        with captured_logs(caplog, "mysite.audit"):
            membership.save()

        records = [r for r in caplog.records if r.name == "mysite.audit"]
        assert [r.extra["action"] for r in records] == ["api_token.auto_revoke"]
        assert records[0].extra["metadata"] == {
            "reason": RevokeReason.CREATOR_NOT_ADMIN,
            "circle_id": circle.id,
            "prefix": token.display_prefix,
        }


@pytest.mark.django_db
class TestPasswordHooks:
    def test_password_change_revokes_every_circles_tokens(self, admin, circle, other_circle, token):
        other_token, _ = create_token(other_circle, admin)
        client = APIClient()
        client.force_authenticate(admin)

        response = client.post(
            reverse("auth-password-change"),
            {"current_password": "Passw0rd!", "password": NEW_PASSWORD, "password_confirm": NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert reload(token).revoked_reason == RevokeReason.PASSWORD_CHANGED
        assert reload(other_token).revoked_reason == RevokeReason.PASSWORD_CHANGED

    def test_password_reset_revokes(self, admin, token):
        reset = store_token("password-reset", {"user_id": admin.id, "issued_at": timezone.now().isoformat()})

        response = APIClient().post(
            reverse("auth-password-reset-confirm"),
            {"token": reset, "password": NEW_PASSWORD, "password_confirm": NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert reload(token).revoked_reason == RevokeReason.PASSWORD_CHANGED

    def test_other_users_tokens_survive_a_password_change(self, circle, co_admin, token):
        client = APIClient()
        client.force_authenticate(co_admin)

        client.post(
            reverse("auth-password-change"),
            {"current_password": "Passw0rd!", "password": NEW_PASSWORD, "password_confirm": NEW_PASSWORD},
            format="json",
        )

        assert reload(token).revoked_at is None

    def test_an_already_revoked_token_keeps_its_reason(self, admin, token):
        services.revoke_token(token, by_user=admin)
        client = APIClient()
        client.force_authenticate(admin)

        client.post(
            reverse("auth-password-change"),
            {"current_password": "Passw0rd!", "password": NEW_PASSWORD, "password_confirm": NEW_PASSWORD},
            format="json",
        )

        assert reload(token).revoked_reason == RevokeReason.MANUAL
