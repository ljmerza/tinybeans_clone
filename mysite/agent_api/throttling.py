"""Per-token rate limits for the agent API.

Rates come from Django settings rather than ``DEFAULT_THROTTLE_RATES``: DRF
binds that dict when the module is imported, and ``local.py`` empties it. DRF
makes a new throttle for every request, so ``override_settings`` works too.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class AgentReadThrottle(SimpleRateThrottle):
    """Every agent request, per token (``AGENT_API_READ_RATE``)."""

    scope = "agent_read"

    def get_rate(self):
        return settings.AGENT_API_READ_RATE

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": str(request.auth.id)}


class AgentSuggestThrottle(AgentReadThrottle):
    """Milestone suggestions, per token (``AGENT_API_SUGGEST_RATE``)."""

    scope = "agent_suggest"

    def get_rate(self):
        return settings.AGENT_API_SUGGEST_RATE
