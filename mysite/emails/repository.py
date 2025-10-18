"""Repository layer for email templates."""
from __future__ import annotations

from typing import Dict, Optional, Protocol

from mysite.emails.models import EmailTemplate


class EmailTemplateRepository(Protocol):
    """Interface for storing and retrieving email templates."""

    def save(self, template: EmailTemplate) -> None:
        ...

    def get(self, template_id: str) -> Optional[EmailTemplate]:
        ...

    def clear(self) -> None:
        ...


class InMemoryEmailTemplateRepository:
    """Simple in-memory repository suitable for process-local template registration."""

    def __init__(self) -> None:
        self._templates: Dict[str, EmailTemplate] = {}

    def save(self, template: EmailTemplate) -> None:
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> Optional[EmailTemplate]:
        return self._templates.get(template_id)

    def clear(self) -> None:
        self._templates.clear()

    def list_ids(self) -> list[str]:
        return list(self._templates.keys())
