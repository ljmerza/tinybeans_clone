"""Client IP resolution behind proxies, and the rate limits keyed on it."""

import os
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, override_settings
from django_ratelimit.core import is_ratelimited
from rest_framework.request import Request

from mysite.config.settings.security import _get_ip_trust_config
from mysite.security.ip_utils import get_client_ip, ratelimit_client_ip
from mysite.security.throttling import ClientIPAnonRateThrottle

CLIENT = "203.0.113.7"
SPOOFED = "198.51.100.66"

# Production shape: gunicorn only hears from the in-image nginx on loopback.
PROD = {"DEBUG": False, "TRUST_FORWARDED_FOR": True, "TRUSTED_PROXY_IPS": ["127.0.0.1", "::1"]}
# A deeper chain with Docker bridge proxies trusted by CIDR.
DOCKER_CIDR = {"DEBUG": False, "TRUST_FORWARDED_FOR": True, "TRUSTED_PROXY_IPS": ["127.0.0.1", "172.16.0.0/12"]}


def _request(remote_addr="127.0.0.1", xff=None, real_ip=None):
    meta = {"REMOTE_ADDR": remote_addr}
    if xff is not None:
        meta["HTTP_X_FORWARDED_FOR"] = xff
    if real_ip is not None:
        meta["HTTP_X_REAL_IP"] = real_ip
    return RequestFactory().post("/api/auth/login/", **meta)


class GetClientIPTests(SimpleTestCase):
    @override_settings(**PROD)
    def test_spoofed_left_most_entry_is_ignored(self):
        request = _request(xff=f"{SPOOFED}, {CLIENT}")
        self.assertEqual(get_client_ip(request), CLIENT)

    @override_settings(**DOCKER_CIDR)
    def test_trusted_cidr_chain_is_walked_from_the_right(self):
        # client-written entry, the real client, then two Docker-bridge proxies
        request = _request(xff=f"{SPOOFED}, {CLIENT}, 172.22.0.1, 172.19.0.5")
        self.assertEqual(get_client_ip(request), CLIENT)

    @override_settings(**DOCKER_CIDR)
    def test_lan_client_is_not_skipped_as_a_proxy(self):
        request = _request(xff=f"{SPOOFED}, 192.168.1.50, 172.22.0.1")
        self.assertEqual(get_client_ip(request), "192.168.1.50")

    @override_settings(**PROD)
    def test_no_forwarded_header_uses_remote_addr(self):
        self.assertEqual(get_client_ip(_request()), "127.0.0.1")

    @override_settings(**PROD)
    def test_x_real_ip_from_trusted_proxy_without_xff(self):
        self.assertEqual(get_client_ip(_request(real_ip=CLIENT)), CLIENT)

    @override_settings(**PROD)
    def test_untrusted_peer_cannot_supply_forwarded_headers(self):
        request = _request(remote_addr=CLIENT, xff=SPOOFED, real_ip=SPOOFED)
        self.assertEqual(get_client_ip(request), CLIENT)

    @override_settings(**PROD)
    def test_malformed_entry_stops_the_walk(self):
        # Nothing left of the garbage can be vouched for; the nearest trusted hop is used.
        self.assertEqual(get_client_ip(_request(xff=f"{SPOOFED}, not-an-ip")), "127.0.0.1")
        self.assertEqual(get_client_ip(_request(xff=f"not-an-ip, {CLIENT}")), CLIENT)
        self.assertEqual(get_client_ip(_request(xff=" , ,")), "127.0.0.1")

    @override_settings(**PROD)
    def test_ipv4_mapped_ipv6_is_normalised(self):
        request = _request(remote_addr="::ffff:127.0.0.1", xff=f"::ffff:{CLIENT}")
        self.assertEqual(get_client_ip(request), CLIENT)

    @override_settings(DEBUG=False, TRUST_FORWARDED_FOR=False, TRUSTED_PROXY_IPS=["127.0.0.1"])
    def test_forwarded_headers_ignored_when_trust_is_off(self):
        self.assertEqual(get_client_ip(_request(xff=CLIENT, real_ip=CLIENT)), "127.0.0.1")

    @override_settings(DEBUG=False, TRUST_FORWARDED_FOR=True, TRUSTED_PROXY_IPS=[])
    def test_trust_without_trusted_proxies_does_not_believe_xff(self):
        self.assertEqual(get_client_ip(_request(xff=SPOOFED)), "127.0.0.1")

    @override_settings(DEBUG=True, TRUST_FORWARDED_FOR=True, TRUSTED_PROXY_IPS=["127.0.0.1", "::1"])
    def test_debug_keeps_the_permissive_left_most_behaviour(self):
        request = _request(remote_addr="172.22.0.1", xff=f"{SPOOFED}, {CLIENT}")
        self.assertEqual(get_client_ip(request), SPOOFED)


class RatelimitClientIPTests(SimpleTestCase):
    @override_settings(**PROD)
    def test_always_returns_a_parseable_address(self):
        self.assertEqual(ratelimit_client_ip(_request(xff=CLIENT)), CLIENT)
        self.assertEqual(ratelimit_client_ip(_request(remote_addr="")), "0.0.0.0")

    @override_settings(DEBUG=True, TRUST_FORWARDED_FOR=True)
    def test_malformed_debug_value_falls_back_to_remote_addr(self):
        self.assertEqual(ratelimit_client_ip(_request(remote_addr="10.0.0.9", xff="garbage")), "10.0.0.9")


@override_settings(RATELIMIT_ENABLE=True, **PROD)
class DjangoRatelimitKeyTests(SimpleTestCase):
    """`key="ip"` in django-ratelimit goes through RATELIMIT_IP_META_KEY."""

    def setUp(self):
        cache.clear()

    def _limited(self, request):
        return is_ratelimited(request, group="test-ip", key="ip", rate="2/m", method="POST", increment=True)

    def test_rotating_spoofed_entries_share_the_real_clients_bucket(self):
        results = [self._limited(_request(xff=f"198.51.100.{n}, {CLIENT}")) for n in range(3)]
        self.assertEqual(results, [False, False, True])

    def test_distinct_clients_behind_the_same_proxy_get_separate_buckets(self):
        results = [self._limited(_request(xff=f"203.0.113.{n}")) for n in range(3)]
        self.assertEqual(results, [False, False, False])


@override_settings(**PROD)
class DRFThrottleIdentTests(SimpleTestCase):
    def test_anon_throttle_keys_on_the_resolved_client(self):
        request = Request(_request(xff=f"{SPOOFED}, {CLIENT}"))
        self.assertEqual(ClientIPAnonRateThrottle().get_ident(request), CLIENT)


class TrustedProxySettingTests(SimpleTestCase):
    def test_cidr_entries_are_accepted(self):
        with patch.dict(os.environ, {"DJANGO_TRUSTED_PROXY_IPS": "127.0.0.1, 172.16.0.0/12, ::1"}):
            config = _get_ip_trust_config(debug=False)
        self.assertEqual(config["TRUSTED_PROXY_IPS"], ["127.0.0.1", "172.16.0.0/12", "::1"])

    def test_invalid_entry_fails_fast(self):
        with (
            patch.dict(os.environ, {"DJANGO_TRUSTED_PROXY_IPS": "127.0.0.1,not-a-proxy"}),
            self.assertRaises(ImproperlyConfigured),
        ):
            _get_ip_trust_config(debug=False)
