"""Centralized logging helpers and configuration for the project."""
from __future__ import annotations

import json
import logging as std_logging
import os
import socket
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

SENSITIVE_KEYS = {'password', 'token', 'secret', 'authorization', 'cookie', 'api_key'}

_context: ContextVar[Optional[Mapping[str, Any]]] = ContextVar('log_context', default=None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_context() -> Mapping[str, Any]:
    data = _context.get()
    if not data:
        return {}
    return data


def _normalized_context(extra: Mapping[str, Any]) -> Mapping[str, Any]:
    clean: Dict[str, Any] = dict(_current_context())
    for key, value in extra.items():
        if value is None:
            continue
        clean[key] = value
    return clean


def push_context(**extra: Any):
    """Merge additional log context into the context variable."""
    token = _context.set(_normalized_context(extra))
    return token


def pop_context(token) -> None:
    """Reset the context stack to a prior token."""
    if token is None:
        return
    _context.reset(token)


def clear_context() -> None:
    """Remove any contextual metadata currently stored."""
    _context.set({})


@contextmanager
def log_context(**extra: Any):
    """Context manager that temporarily adds contextual metadata to log records."""
    token = push_context(**extra)
    try:
        yield
    finally:
        pop_context(token)


def redacted_value(key: str, value: Any) -> Any:
    if isinstance(value, MutableMapping):
        return {nested_key: redacted_value(f'{key}.{nested_key}', nested_val) for nested_key, nested_val in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redacted_value(f'{key}[{index}]', item) for index, item in enumerate(value)]
    lowered = key.lower()
    if any(part in lowered for part in SENSITIVE_KEYS):
        return '***'
    return value


def _scrub_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: redacted_value(key, value) for key, value in payload.items()}


class LoggingContextFilter(std_logging.Filter):
    """Inject contextvars metadata and static attributes into each log record."""

    def __init__(self, service_name: str, environment: str):
        super().__init__()
        self.service_name = service_name
        self.environment = environment
        self.hostname = socket.gethostname()

    def filter(self, record: std_logging.LogRecord) -> bool:
        context = dict(_current_context())
        record.service = self.service_name
        record.environment = self.environment
        record.hostname = self.hostname
        record.context = _scrub_payload(context)
        record.request_id = context.get('request_id') or context.get('trace_id')
        record.user_id = context.get('user_id')
        record.session_id = context.get('session_id')
        record.remote_ip = context.get('remote_ip')
        record.correlation_id = record.request_id
        record.extra_data = _scrub_payload(context.get('extra', {})) if isinstance(context.get('extra'), Mapping) else None
        return True


class JsonLogFormatter(std_logging.Formatter):
    """Render log records as structured JSON for log shipping."""

    def format(self, record: std_logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            'timestamp': _now_iso(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': getattr(record, 'service', None),
            'environment': getattr(record, 'environment', None),
            'hostname': getattr(record, 'hostname', None),
        }

        if getattr(record, 'request_id', None):
            payload['request_id'] = record.request_id
        if getattr(record, 'user_id', None):
            payload['user_id'] = record.user_id
        if getattr(record, 'session_id', None):
            payload['session_id'] = record.session_id
        if getattr(record, 'remote_ip', None):
            payload['remote_ip'] = record.remote_ip

        if getattr(record, 'context', None):
            payload['context'] = record.context
        if getattr(record, 'extra_data', None):
            payload['extra'] = record.extra_data
        if getattr(record, 'event', None):
            payload['event'] = record.event

        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)

        return json.dumps({key: value for key, value in payload.items() if value is not None}, default=str)


def _console_handler_config(formatter: str, filters: Iterable[str], stream: str = 'ext://sys.stdout') -> Dict[str, Any]:
    return {
        'class': 'logging.StreamHandler',
        'formatter': formatter,
        'filters': list(filters),
        'stream': stream,
    }


def _null_handler_config(filters: Iterable[str]) -> Dict[str, Any]:
    return {
        'class': 'logging.NullHandler',
        'filters': list(filters),
    }


def get_logging_config(
    *,
    log_level: Optional[str] = None,
    environment: Optional[str] = None,
    service_name: Optional[str] = None,
    enable_console: bool = True,
    enable_audit_console: Optional[bool] = None,
) -> Dict[str, Any]:
    """Return a dictConfig-compatible logging configuration."""
    level = (log_level or os.environ.get('DJANGO_LOG_LEVEL') or 'INFO').upper()
    env = environment or os.environ.get('DJANGO_ENVIRONMENT', 'local')
    service = service_name or os.environ.get('SERVICE_NAME', 'mysite')
    audit_console = enable_console if enable_audit_console is None else enable_audit_console

    filters = {
        'context': {
            '()': 'mysite.project_logging.LoggingContextFilter',
            'service_name': service,
            'environment': env,
        }
    }

    formatters = {
        'json': {
            '()': 'mysite.project_logging.JsonLogFormatter',
        }
    }

    handlers: Dict[str, Dict[str, Any]] = {}
    if enable_console:
        handlers['console'] = _console_handler_config('json', ['context'])
    else:
        handlers['console'] = _null_handler_config(['context'])

    if audit_console:
        handlers['audit_console'] = _console_handler_config('json', ['context'])
    else:
        handlers['audit_console'] = _null_handler_config(['context'])

    root_handlers = ['console']
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': filters,
        'formatters': formatters,
        'handlers': handlers,
        'root': {
            'level': level,
            'handlers': root_handlers,
        },
        'loggers': {
            'django': {
                'level': os.environ.get('DJANGO_LOG_LEVEL_DJANGO', level),
                'handlers': ['console'],
                'propagate': False,
            },
            'django.request': {
                'level': os.environ.get('DJANGO_LOG_LEVEL_REQUEST', 'WARNING'),
                'handlers': ['console'],
                'propagate': False,
            },
            'celery': {
                'handlers': ['console'],
                'level': os.environ.get('DJANGO_LOG_LEVEL_CELERY', level),
                'propagate': False,
            },
            'mysite.audit': {
                'handlers': ['audit_console'],
                'level': os.environ.get('DJANGO_LOG_LEVEL_AUDIT', 'INFO'),
                'propagate': False,
            },
        },
    }
    return logging_config


def generate_request_id() -> str:
    return uuid.uuid4().hex


def bind_celery_signals(app) -> None:
    """Attach Celery signal handlers to apply logging context."""
    from celery import signals

    @signals.task_prerun.connect
    def _task_prerun(task_id=None, task=None, **kwargs):
        request = getattr(task, 'request', None)
        correlation_id = getattr(request, 'correlation_id', None) or getattr(request, 'id', None)
        token = push_context(
            request_id=correlation_id or generate_request_id(),
            task_id=task_id,
            task_name=getattr(task, 'name', None),
        )
        if request is not None:
            setattr(request, '_logging_token', token)
        else:
            setattr(task, '_logging_token', token)

    @signals.task_postrun.connect
    def _task_postrun(task_id=None, task=None, **kwargs):
        request = getattr(task, 'request', None)
        token = None
        if request is not None:
            token = getattr(request, '_logging_token', None)
            if token is not None:
                delattr(request, '_logging_token')
        if token is None and task is not None:
            token = getattr(task, '_logging_token', None)
            if token is not None:
                delattr(task, '_logging_token')
        pop_context(token)

    @signals.task_failure.connect
    def _task_failure(task_id=None, exception=None, traceback=None, einfo=None, sender=None, **kwargs):
        logger = std_logging.getLogger('celery')
        exc_info = getattr(einfo, 'exc_info', None) if einfo is not None else None
        logger.error(
            'Celery task failed',
            extra={
                'event': 'celery.task_failure',
                'extra': {
                    'task_id': task_id,
                    'task_name': getattr(sender, 'name', None),
                    'exception': repr(exception),
                },
            },
            exc_info=exc_info,
        )
