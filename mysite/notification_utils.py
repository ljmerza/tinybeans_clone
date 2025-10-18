"""Standardized notification response utilities.

This module provides utilities to create API responses following ADR-012:
Notification Strategy. Messages are returned with i18n keys and context,
allowing the frontend to handle translation and presentation.
"""
from typing import Any, Optional
from rest_framework import status
from rest_framework.response import Response


def create_message(i18n_key: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Create a standardized message object.
    
    Args:
        i18n_key: Translation key from frontend i18n files (e.g., 'errors.file_too_large')
        context: Optional flat dictionary with dynamic values for parameterized messages
        
    Returns:
        Dictionary with i18n_key and context
        
    Example:
        >>> create_message('errors.file_too_large', {'filename': 'photo.jpg', 'maxSize': '10MB'})
        {'i18n_key': 'errors.file_too_large', 'context': {'filename': 'photo.jpg', 'maxSize': '10MB'}}
    """
    message = {'i18n_key': i18n_key}
    if context:
        message['context'] = context
    return message


def success_response(
    data: dict[str, Any],
    messages: Optional[list[dict[str, Any]]] = None,
    status_code: int = status.HTTP_200_OK
) -> Response:
    """Create a standardized success response.
    
    Success responses typically don't need messages as the frontend handles
    optimistic UI. Include messages only when necessary.
    
    Args:
        data: Response data dictionary
        messages: Optional list of message objects created with create_message()
        status_code: HTTP status code (defaults to 200 OK)
        
    Returns:
        Response object with data and optional messages
        
    Example:
        >>> success_response({'user_id': 123}, [create_message('notifications.profile.updated')])
    """
    response_data = {'data': data}
    if messages:
        response_data['messages'] = messages
    return Response(response_data, status=status_code)


def error_response(
    error: str,
    messages: list[dict[str, Any]],
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> Response:
    """Create a standardized error response.
    
    Error responses don't include a data property. The error field provides
    a machine-readable error code while messages provide user-facing content.
    
    Args:
        error: Machine-readable error code (e.g., 'validation_failed', 'file_too_large')
        messages: List of message objects created with create_message()
        status_code: HTTP status code (defaults to 400 Bad Request)
        
    Returns:
        Response object with error code and messages
        
    Example:
        >>> error_response(
        ...     'file_too_large',
        ...     [create_message('errors.file_too_large', {'filename': 'photo.jpg', 'maxSize': '10MB'})],
        ...     status.HTTP_400_BAD_REQUEST
        ... )
    """
    return Response(
        {
            'error': error,
            'messages': messages
        },
        status=status_code
    )


def validation_error_response(
    messages: list[dict[str, Any]],
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> Response:
    """Create a standardized validation error response.
    
    Convenience function for validation errors with multiple field-level messages.
    
    Args:
        messages: List of message objects, typically with 'field' in context
        status_code: HTTP status code (defaults to 400 Bad Request)
        
    Returns:
        Response object with validation_failed error and messages
        
    Example:
        >>> validation_error_response([
        ...     create_message('errors.email_invalid', {'field': 'email'}),
        ...     create_message('errors.password_too_short', {'field': 'password', 'minLength': 8})
        ... ])
    """
    return error_response('validation_failed', messages, status_code)


def rate_limit_response(
    i18n_key: str = 'errors.rate_limit',
    context: Optional[dict[str, Any]] = None
) -> Response:
    """Create a standardized rate limit response.
    
    Args:
        i18n_key: Translation key for rate limit message
        context: Optional context (e.g., retry_after seconds)
        
    Returns:
        Response object with 429 status code and rate limit message
        
    Example:
        >>> rate_limit_response('errors.rate_limit', {'retry_after': 60})
    """
    return error_response(
        'rate_limit_exceeded',
        [create_message(i18n_key, context)],
        status.HTTP_429_TOO_MANY_REQUESTS
    )
