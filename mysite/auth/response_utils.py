"""Reusable response utilities for API views"""
from rest_framework import status
from rest_framework.response import Response


def rate_limit_response(message: str = 'Too many requests. Please try again later.') -> Response:
    """
    Create a standardized rate limit response.
    
    Args:
        message: Custom error message. Defaults to a generic rate limit message.
    
    Returns:
        Response object with 429 status code and error message.
    
    Example:
        >>> return rate_limit_response()
        >>> return rate_limit_response('Account temporarily locked due to too many failed attempts.')
    """
    return Response(
        {'error': message},
        status=status.HTTP_429_TOO_MANY_REQUESTS
    )


def error_response(message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """
    Create a standardized error response.
    
    Args:
        message: Error message to return to the client.
        status_code: HTTP status code. Defaults to 400 Bad Request.
    
    Returns:
        Response object with specified status code and error message.
    
    Example:
        >>> return error_response('Invalid verification code')
        >>> return error_response('Not found', status.HTTP_404_NOT_FOUND)
    """
    return Response(
        {'error': message},
        status=status_code
    )


def success_response(data: dict, status_code: int = status.HTTP_200_OK) -> Response:
    """
    Create a standardized success response.
    
    Args:
        data: Response data dictionary.
        status_code: HTTP status code. Defaults to 200 OK.
    
    Returns:
        Response object with specified status code and data.
    
    Example:
        >>> return success_response({'message': 'Operation successful'})
        >>> return success_response({'id': 123}, status.HTTP_201_CREATED)
    """
    return Response(data, status=status_code)
