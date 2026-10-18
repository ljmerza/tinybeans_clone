"""The operator's provider settings: read without raising, checked when used, fail closed."""

import importlib

import pytest

from mysite.agent_api.tests.helpers import audit_actions, captured_logs
from mysite.ai import providers
from mysite.config.settings import ai as ai_settings_module

from .helpers import BASE_URL, MODEL


@pytest.fixture
def reload_ai_settings(monkeypatch):
    """Re-import the settings module under a patched env, then restore it."""

    def reload(**env):
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return importlib.reload(ai_settings_module)

    yield reload
    monkeypatch.undo()
    importlib.reload(ai_settings_module)


class TestSettingsModule:
    def test_defaults_with_nothing_set(self, reload_ai_settings, monkeypatch):
        for name in ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL", "AI_MAX_CALLS_PER_RUN"):
            monkeypatch.delenv(name, raising=False)
        module = reload_ai_settings()

        assert module.AI_BASE_URL == ""
        assert module.AI_MODEL == ""
        assert module.AI_MAX_CALLS_PER_RUN == 200
        assert module.AI_REQUEST_TIMEOUT_SECONDS == 120
        assert module.AI_MAX_CAPTION_CHARS == 1500

    def test_bad_values_never_raise_at_import(self, reload_ai_settings):
        module = reload_ai_settings(
            AI_BASE_URL="ftp://user:pw@nowhere",
            AI_MAX_CALLS_PER_RUN="lots",
            AI_REQUEST_TIMEOUT_SECONDS="-5",
            AI_MAX_CAPTION_CHARS="0",
        )

        assert module.AI_BASE_URL == "ftp://user:pw@nowhere"  # kept raw; checked when used
        assert module.AI_MAX_CALLS_PER_RUN == 200
        assert module.AI_REQUEST_TIMEOUT_SECONDS == 120
        assert module.AI_MAX_CAPTION_CHARS == 1500

    def test_values_are_read(self, reload_ai_settings):
        module = reload_ai_settings(
            AI_BASE_URL=f" {BASE_URL} ", AI_MODEL=MODEL, AI_MAX_CALLS_PER_RUN="20", AI_REQUEST_TIMEOUT_SECONDS="30"
        )

        assert module.AI_BASE_URL == BASE_URL
        assert module.AI_MODEL == MODEL
        assert module.AI_MAX_CALLS_PER_RUN == 20
        assert module.AI_REQUEST_TIMEOUT_SECONDS == 30


class TestProviderConfig:
    def test_off_by_default_in_tests(self):
        assert providers.provider_config() is None
        assert providers.ai_enabled() is False

    @pytest.mark.parametrize(("base_url", "model"), [("", MODEL), (BASE_URL, ""), ("  ", "  ")])
    def test_empty_url_or_model_disables_without_raising(self, settings, base_url, model):
        settings.AI_BASE_URL = base_url
        settings.AI_MODEL = model

        assert providers.ai_enabled() is False

    def test_valid_config(self, ai_on):
        ai_on.AI_BASE_URL = BASE_URL + "/"
        ai_on.AI_REQUEST_TIMEOUT_SECONDS = 45

        config = providers.provider_config()

        assert config.base_url == BASE_URL  # trailing slash dropped
        assert config.model == MODEL
        assert config.api_key == ""
        assert config.timeout_seconds == 45
        assert providers.ai_enabled() is True

    def test_https_with_key(self, ai_on):
        ai_on.AI_BASE_URL = "https://api.example.com/v1"
        ai_on.AI_API_KEY = "sk-secret-value"

        config = providers.provider_config()

        assert config.api_key == "sk-secret-value"
        assert "sk-secret-value" not in repr(config)

    @pytest.mark.parametrize(
        ("base_url", "api_key", "problem"),
        [
            ("ftp://ai.test/v1", "", "url"),
            ("file:///etc/passwd", "", "url"),
            ("ai.test:11434/v1", "", "url"),
            ("http://", "", "url"),
            ("http://user:pw@ai.test/v1", "", "userinfo"),
            ("https://token@ai.test/v1", "", "userinfo"),
            ("http://ai.test/v1", "sk-secret-value", "http_with_key"),
        ],
    )
    def test_invalid_config_is_rejected_and_logged(self, ai_on, caplog, base_url, api_key, problem):
        ai_on.AI_BASE_URL = base_url
        ai_on.AI_API_KEY = api_key

        with captured_logs(caplog, "mysite.audit"):
            assert providers.provider_config() is None
            assert providers.ai_enabled() is False

        assert audit_actions(caplog) == ["ai.config_invalid"]  # once, not on every check
        record = next(record for record in caplog.records if record.name == "mysite.audit")
        assert record.extra["metadata"] == {"problem": problem}
        logged = " ".join(record.getMessage() + str(record.extra) for record in caplog.records)
        assert base_url not in logged
        if api_key:
            assert api_key not in logged
