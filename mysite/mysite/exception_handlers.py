"""Custom exception handling for REST framework responses.

Transforms validation errors into standardized notification payloads that
the frontend can translate using i18n keys.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rest_framework import status
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

from .notification_utils import create_message, error_response


def _coerce_to_str(detail: Any) -> str:
    """Convert any validation detail into a string."""
    if isinstance(detail, ErrorDetail):
        return str(detail)
    return str(detail)


def _flatten_validation_detail(detail: Any, field: str | None = None) -> list[dict[str, Any]]:
    """Recursively flatten DRF validation error details into message dicts."""
    messages: list[dict[str, Any]] = []

    if isinstance(detail, Mapping):
        # Direct message payload from serializers (already in notification format)
        if 'i18n_key' in detail:
            context = dict(detail.get('context') or {})
            if field and 'field' not in context:
                context['field'] = field
            messages.append(create_message(str(detail['i18n_key']), context or None))
            return messages

        for key, value in detail.items():
            if key == 'messages':
                messages.extend(_flatten_validation_detail(value, field))
                continue

            next_field = field
            if key not in {'non_field_errors', 'messages'}:
                next_field = key
            messages.extend(_flatten_validation_detail(value, next_field))
        return messages

    if isinstance(detail, Sequence) and not isinstance(detail, (str, bytes)):
        for item in detail:
            messages.extend(_flatten_validation_detail(item, field))
        return messages

    # Primitive value - fall back to generic validation error template
    context: dict[str, Any] = {'message': _coerce_to_str(detail)}
    if field:
        context['field'] = field
    messages.append(create_message('errors.validation_error' if field else 'errors.general_validation_error', context))
    return messages


def custom_exception_handler(exc, context):
    """Handle exceptions and convert validation errors to notification format."""
    if isinstance(exc, ValidationError):
        messages = _flatten_validation_detail(exc.detail)
        if not messages:
            messages = [create_message('errors.validation_failed')]
        return error_response('validation_failed', messages, status.HTTP_400_BAD_REQUEST)

    return drf_exception_handler(exc, context)


__all__ = ['custom_exception_handler']
