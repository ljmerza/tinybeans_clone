"""Helper utilities for Google OAuth views.

This module provides shared utilities used across OAuth views:
- IP address extraction
- Validation error handling
- Rate limit checking
"""
from rest_framework.response import Response
from mysite.notification_utils import (
    validation_error_response,
    rate_limit_response,
    create_message
)
from mysite.security.ip_utils import get_client_ip


def check_rate_limit(request):
    """Check if request was rate limited.

    Args:
        request: The HTTP request

    Returns:
        Response if rate limited, None otherwise
    """
    was_limited = getattr(request, 'limited', False)
    if was_limited:
        return rate_limit_response('errors.rate_limit')
    return None


def handle_validation_errors(serializer):
    """Convert serializer errors to validation error response.

    Args:
        serializer: DRF serializer with errors

    Returns:
        Response with validation errors
    """
    errors = []
    for field, field_errors in serializer.errors.items():
        for error_msg in field_errors:
            errors.append(create_message('errors.validation_error', {
                'field': field,
                'message': str(error_msg)
            }))
    return validation_error_response(errors)
