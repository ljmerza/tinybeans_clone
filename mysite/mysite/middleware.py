"""Project-specific Django middleware."""
from __future__ import annotations

from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse

from mysite import logging as project_logging


class RequestContextMiddleware:
    """Populate log context with request identifiers and user metadata."""

    header_name = 'HTTP_X_REQUEST_ID'

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = self._resolve_request_id(request)
        user_id: Optional[str] = None
        if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
            user_id = str(request.user.pk)

        session_id: Optional[str] = getattr(request.session, 'session_key', None)
        remote_ip = self._remote_ip(request)

        token = project_logging.push_context(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            remote_ip=remote_ip,
            path=request.path,
            method=request.method,
        )
        request.request_id = request_id

        try:
            response = self.get_response(request)
        finally:
            project_logging.pop_context(token)

        if response is not None:
            response['X-Request-ID'] = request_id
        return response

    def _resolve_request_id(self, request: HttpRequest) -> str:
        header_value = request.META.get(self.header_name)
        if header_value:
            return header_value
        return project_logging.generate_request_id()

    @staticmethod
    def _remote_ip(request: HttpRequest) -> Optional[str]:
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
