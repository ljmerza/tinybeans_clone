"""Helpers for emitting structured audit and security logs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging as std_logging

from mysite import project_logging

AUDIT_LOGGER_NAME = 'mysite.audit'


@dataclass
class AuditEvent:
    """Structured payload for audit trail events."""

    action: str
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    status: str = 'success'
    severity: str = 'info'
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            'action': self.action,
            'actor_id': self.actor_id,
            'actor_type': self.actor_type,
            'target_id': self.target_id,
            'target_type': self.target_type,
            'status': self.status,
            'severity': self.severity,
            'description': self.description,
            'metadata': self.metadata,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        return {key: value for key, value in payload.items() if value is not None}


def log_audit_event(event: AuditEvent, *, level: Optional[int] = None) -> None:
    """Emit an audit event via the dedicated audit logger."""
    logger = std_logging.getLogger(AUDIT_LOGGER_NAME)
    payload = event.to_dict()
    level = level or _severity_to_level(event.severity)

    with project_logging.log_context(audit_action=event.action, actor_id=event.actor_id, target_id=event.target_id):
        logger.log(
            level,
            event.description or event.action,
            extra={
                'event': f'audit.{event.action}',
                'extra': payload,
            },
        )


def log_security_event(action: str, *, actor_id: Optional[str] = None, target_id: Optional[str] = None, status: str = 'success', severity: str = 'warning', description: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Convenience wrapper specialising AuditEvent for security-related records."""
    log_audit_event(
        AuditEvent(
            action=action,
            actor_id=actor_id,
            target_id=target_id,
            status=status,
            severity=severity,
            description=description,
            metadata=metadata or {},
        ),
        level=None,
    )


def _severity_to_level(severity: str) -> int:
    mapping = {
        'debug': std_logging.DEBUG,
        'info': std_logging.INFO,
        'notice': std_logging.INFO,
        'warning': std_logging.WARNING,
        'error': std_logging.ERROR,
        'critical': std_logging.CRITICAL,
    }
    return mapping.get(severity.lower(), std_logging.INFO)


__all__ = ['AuditEvent', 'log_audit_event', 'log_security_event', 'AUDIT_LOGGER_NAME']
