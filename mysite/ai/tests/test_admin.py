"""Django admin for in-app AI: a superuser can only switch a circle on or off."""

import pytest
from django.contrib.admin.sites import site
from django.test import RequestFactory

from mysite.agent_api.tests.helpers import audit_actions, captured_logs
from mysite.ai.admin import CircleAiSettingsAdmin
from mysite.ai.models import CircleAiSettings

from .helpers import turn_on


@pytest.mark.django_db
class TestCircleAiSettingsAdmin:
    @pytest.fixture
    def model_admin(self):
        return CircleAiSettingsAdmin(CircleAiSettings, site)

    @pytest.fixture
    def request_(self, django_user_model):
        request = RequestFactory().post("/")
        request.user = django_user_model.objects.create_superuser(email="root@example.com", password="Passw0rd!")
        return request

    def test_only_enabled_is_editable(self, model_admin, request_):
        assert set(model_admin.fields) - set(model_admin.readonly_fields) == {"enabled"}
        assert model_admin.has_add_permission(request_) is False
        assert model_admin.has_delete_permission(request_) is False

    def test_turning_a_circle_off_is_audited(self, model_admin, request_, circle, admin, caplog):
        ai_settings = turn_on(circle, admin)
        form = model_admin.get_form(request_, ai_settings)(data={"enabled": False}, instance=ai_settings)
        assert form.is_valid(), form.errors

        with captured_logs(caplog, "mysite.audit"):
            model_admin.save_model(request_, form.save(commit=False), form, change=True)

        ai_settings.refresh_from_db()
        assert ai_settings.enabled is False
        assert ai_settings.updated_by == request_.user
        assert audit_actions(caplog) == ["circle.ai_settings.update"]
