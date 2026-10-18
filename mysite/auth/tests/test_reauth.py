"""Re-authentication by emailed code: service (verify_reauth) and POST /api/auth/reauth/code/."""

import logging
import re
from contextlib import contextmanager
from unittest.mock import patch

import pyotp
import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import TwoFactorSettings
from mysite.auth.services import reauth_service
from mysite.auth.services.reauth_service import send_reauth_code, verify_reauth
from mysite.users.models import User

CODE_RE = re.compile(r"verification code is: (\d{6})")


@pytest.fixture(autouse=True)
def _clean_state():
    cache.clear()
    mail.outbox = []
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="reauth@example.com", password="Passw0rd!", first_name="Riley", email_verified=True
    )


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user)
    return api_client


def _latest_code(email="reauth@example.com"):
    sent = [message for message in mail.outbox if message.to == [email] and CODE_RE.search(message.body)]
    assert sent, "expected a code email"
    return CODE_RE.search(sent[-1].body).group(1)


def _wrong(code):
    return f"{(int(code) + 1) % 10**6:06d}"


@contextmanager
def _captured(caplog, *names):
    loggers = [logging.getLogger(name) for name in names]
    previous = [logger.propagate for logger in loggers]
    for logger in loggers:
        logger.propagate = True
    try:
        with caplog.at_level(logging.DEBUG):
            yield
    finally:
        for logger, value in zip(loggers, previous, strict=True):
            logger.propagate = value


def _audit_actions(caplog):
    return [record.extra["action"] for record in caplog.records if record.name == "mysite.audit"]


def test_send_returns_202_and_emails_only_the_account_address(user, client):
    TwoFactorSettings.objects.create(user=user, backup_email="backup@example.com", phone_number="+15550100")

    response = client.post(reverse("auth-reauth-code"))

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"data": {}}
    assert [message.to for message in mail.outbox] == [["reauth@example.com"]]
    assert verify_reauth(user, _latest_code())


def test_cache_holds_only_a_hash_of_the_code(user):
    send_reauth_code(user)
    code = _latest_code()

    stored = cache.get(f"reauth:code:{user.pk}")
    assert stored
    assert code not in str(stored)


def test_code_is_single_use(user):
    send_reauth_code(user)
    code = _latest_code()

    assert verify_reauth(user, code) is True
    assert verify_reauth(user, code) is False


def test_concurrent_uses_of_one_code_succeed_only_once(user):
    send_reauth_code(user)
    code = _latest_code()
    results = []
    raced = []
    real_get = cache.get

    def get_then_race(key, *args, **kwargs):
        value = real_get(key, *args, **kwargs)
        if key == f"reauth:code:{user.pk}" and not raced:
            raced.append(True)
            # A second request reads and consumes the code before this one deletes it.
            results.append(("inner", verify_reauth(user, code)))
        return value

    with patch.object(reauth_service.cache, "get", side_effect=get_then_race):
        results.append(("outer", verify_reauth(user, code)))

    assert results == [("inner", True), ("outer", False)]


def test_new_send_replaces_the_previous_code(user):
    send_reauth_code(user)
    first = _latest_code()
    with patch.object(reauth_service.secrets, "randbelow", return_value=(int(first) + 1) % 10**6):
        send_reauth_code(user)
    second = _latest_code()

    assert first != second
    assert verify_reauth(user, first) is False
    assert verify_reauth(user, second) is True


def test_code_survives_four_wrong_guesses(user):
    send_reauth_code(user)
    code = _latest_code()
    for _ in range(4):
        assert verify_reauth(user, _wrong(code)) is False

    assert verify_reauth(user, code) is True


def test_fifth_wrong_guess_deletes_the_code(user):
    send_reauth_code(user)
    code = _latest_code()
    for _ in range(5):
        assert verify_reauth(user, _wrong(code)) is False

    assert cache.get(f"reauth:code:{user.pk}") is None
    assert verify_reauth(user, code) is False


@pytest.mark.parametrize("bad", [None, "", "   ", 123456, ["123456"]])
def test_missing_or_non_string_code_is_rejected(user, bad):
    send_reauth_code(user)

    assert verify_reauth(user, bad) is False


def test_ten_failures_in_a_day_lock_the_user_and_send_an_email(user, caplog):
    with _captured(caplog, "mysite.audit"):
        for _ in range(2):
            send_reauth_code(user)
            code = _latest_code()
            for _ in range(5):
                assert verify_reauth(user, _wrong(code)) is False

    assert reauth_service.is_reauth_locked(user)
    lock_emails = [message for message in mail.outbox if "Too many wrong verification codes" in message.subject]
    assert [message.to for message in lock_emails] == [["reauth@example.com"]]
    assert _audit_actions(caplog).count("reauth.locked") == 1

    # While locked no code is sent and nothing verifies, not even a fresh real code.
    sent_before = len(mail.outbox)
    assert send_reauth_code(user) is False
    assert len(mail.outbox) == sent_before
    cache.set(f"reauth:code:{user.pk}", reauth_service._hash_code("111111"), timeout=600)
    assert verify_reauth(user, "111111") is False
    assert len([message for message in mail.outbox if "Too many wrong" in message.subject]) == 1


def test_failures_without_any_code_also_count_toward_the_lock(user):
    for _ in range(10):
        assert verify_reauth(user, "000000") is False

    assert reauth_service.is_reauth_locked(user)


def test_totp_user_gets_an_email_code_and_totp_codes_are_rejected(user, client):
    secret = pyotp.random_base32()
    settings_obj = TwoFactorSettings.objects.create(
        user=user, is_enabled=True, preferred_method="totp", totp_verified=True
    )
    settings_obj.totp_secret = secret
    settings_obj.save()
    totp_code = pyotp.TOTP(secret).now()

    with patch.object(reauth_service.secrets, "randbelow", return_value=(int(totp_code) + 1) % 10**6):
        assert client.post(reverse("auth-reauth-code")).status_code == status.HTTP_202_ACCEPTED

    assert [message.to for message in mail.outbox] == [["reauth@example.com"]]
    assert verify_reauth(user, totp_code) is False
    assert verify_reauth(user, _latest_code()) is True


def test_totp_reenrolled_with_only_a_session_does_not_pass_reauth(user, client):
    setup = client.post(reverse("2fa-setup"), {"method": "totp"}, format="json")
    assert setup.status_code == status.HTTP_200_OK
    totp = pyotp.TOTP(setup.json()["data"]["secret"])
    verify = client.post(reverse("2fa-verify-setup"), {"code": totp.now()}, format="json")
    assert verify.status_code == status.HTTP_200_OK

    send_reauth_code(user)
    emailed = _latest_code()
    totp_code = totp.now()
    if totp_code == emailed:  # one-in-a-million collision would make the check meaningless
        pytest.skip("TOTP code collided with the emailed code")

    assert verify_reauth(user, totp_code) is False


@override_settings(RATELIMIT_ENABLE=True)
def test_sends_are_rate_limited_per_user(user, client):
    for _ in range(3):
        assert client.post(reverse("auth-reauth-code")).status_code == status.HTTP_202_ACCEPTED

    limited = client.post(reverse("auth-reauth-code"))

    assert limited.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert limited.json() == {
        "error": "rate_limit_exceeded",
        "messages": [{"i18n_key": "errors.reauth_rate_limited"}],
    }
    assert len(mail.outbox) == 3


def test_requires_authentication(db):
    response = APIClient().post(reverse("auth-reauth-code"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert mail.outbox == []


@override_settings(EMAIL_VERIFICATION_ENFORCED=True)
def test_requires_a_verified_email(user, client):
    user.email_verified = False
    user.save(update_fields=["email_verified"])

    response = client.post(reverse("auth-reauth-code"))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert mail.outbox == []


def test_logs_record_events_but_never_the_code(user, client, caplog):
    with _captured(caplog, "mysite.audit", "django.request", "celery"):
        client.post(reverse("auth-reauth-code"))
        code = _latest_code()
        verify_reauth(user, _wrong(code))
        verify_reauth(user, code)

    assert caplog.records, "expected log records to be captured"
    actions = _audit_actions(caplog)
    assert "reauth.code_sent" in actions
    assert "reauth.failed" in actions
    for record in caplog.records:
        assert code not in record.getMessage()
        assert code not in str(getattr(record, "extra", ""))
        assert code not in str(record.args)
