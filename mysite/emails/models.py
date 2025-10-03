"""Domain-level models for the email system."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Union


@dataclass(frozen=True)
class RenderedEmail:
    """Rendered email content with optional HTML."""

    subject: str
    text_body: str
    html_body: str | None = None


RenderedOutput = Union[RenderedEmail, tuple[str, str]]
TemplateRenderer = Callable[[dict[str, Any]], RenderedOutput]


@dataclass(frozen=True)
class EmailTemplate:
    """Domain representation of an email template."""

    template_id: str
    renderer: TemplateRenderer

    def render(self, context: dict[str, Any]) -> RenderedEmail:
        rendered = self.renderer(context)
        if isinstance(rendered, tuple):
            subject, body = rendered
            return RenderedEmail(subject=subject, text_body=body)
        return rendered
