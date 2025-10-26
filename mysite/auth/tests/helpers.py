"""Shared utilities for auth test suites."""


def response_payload(response):
    """Return the unwrapped success payload from API responses."""
    data = getattr(response, 'data', None)
    if isinstance(data, dict) and 'data' in data:
        return data['data']
    return data
