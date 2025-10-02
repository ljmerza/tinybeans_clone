"""Domain-level models for the email system."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

TemplateRenderer = Callable[[dict[str, Any]], tuple[str, str]]


@dataclass(frozen=True)
class EmailContent:
    """Rendered email content."""

    subject: str
    body: str


@dataclass(frozen=True)
class EmailTemplate:
    """Domain representation of an email template."""

    template_id: str
    renderer: TemplateRenderer

    def render(self, context: dict[str, Any]) -> EmailContent:
        subject, body = self.renderer(context)
        return EmailContent(subject=subject, body=body)
