"""DRF throttles keyed on the proxy-aware client IP.

DRF's own ``get_ident`` reads ``X-Forwarded-For`` with ``NUM_PROXIES``; when
that is unset it keys on the whole header, which a client can vary at will.
These subclasses use the same resolver as django-ratelimit instead.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from mysite.security.ip_utils import ratelimit_client_ip


class ClientIPThrottleMixin:
    def get_ident(self, request):
        return ratelimit_client_ip(request)


class ClientIPAnonRateThrottle(ClientIPThrottleMixin, AnonRateThrottle):
    pass


class ClientIPUserRateThrottle(ClientIPThrottleMixin, UserRateThrottle):
    pass
