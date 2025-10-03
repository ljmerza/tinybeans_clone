"""Load email templates from Django template files."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Engine
from django.template.loader_tags import BlockNode
from django.utils.html import strip_tags

from emails.models import RenderedEmail
from emails.services import register_email_template
from emails.templates import EMAIL_TEMPLATE_FILES

logger = logging.getLogger(__name__)

_EMAIL_TEMPLATE_DIR = Path(__file__).resolve().parent / 'email_templates'
_BLOCK_SUBJECT = 'subject'
_BLOCK_TEXT = 'text_body'
_BLOCK_HTML = 'html_body'


def load_email_templates() -> None:
    """Load template files and register them with the email service."""
    if not _EMAIL_TEMPLATE_DIR.exists():
        logger.warning('Email template directory %s does not exist', _EMAIL_TEMPLATE_DIR)
        return

    try:
        engine = Engine.get_default()
    except ImproperlyConfigured as exc:
        logger.error('Cannot load email templates; Django settings not configured: %s', exc)
        return

    for template_id, filename in EMAIL_TEMPLATE_FILES.items():
        template_path = _EMAIL_TEMPLATE_DIR / filename
        if not template_path.exists():
            logger.warning('Email template %s is missing file %s', template_id, template_path)
            continue

        try:
            template_source = template_path.read_text(encoding='utf-8')
        except OSError as exc:
            logger.error('Failed to read email template %s: %s', template_path, exc)
            continue

        compiled_template = engine.from_string(template_source)
        block_map = _collect_blocks(compiled_template)

        if _BLOCK_SUBJECT not in block_map:
            logger.error('Email template %s lacks a "subject" block; skipping registration', template_id)
            continue

        renderer = _build_renderer(compiled_template, block_map, template_id)
        register_email_template(template_id, renderer)


def _collect_blocks(template) -> Dict[str, BlockNode]:
    block_nodes: Dict[str, BlockNode] = {}

    def _walk(nodelist):
        for node in nodelist:
            if isinstance(node, BlockNode):
                block_nodes[node.name] = node
            # Recurse into child nodelists if available
            for child_list in getattr(node, 'child_nodelists', []) or []:
                _walk(child_list)
            if hasattr(node, 'nodelist') and node.nodelist is not None:
                _walk(node.nodelist)

    compiled = getattr(template, 'template', template)
    _walk(compiled.nodelist)
    return block_nodes


def _build_renderer(template, block_map: Dict[str, BlockNode], template_id: str):
    def renderer(context: dict[str, Any]) -> RenderedEmail:
        ctx_data = context or {}
        subject = _render_block(block_map.get(_BLOCK_SUBJECT), ctx_data).strip()
        if not subject:
            raise ValueError(f'Email template {template_id} rendered empty subject')

        text_body = _render_block(block_map.get(_BLOCK_TEXT), ctx_data).strip()
        html_body = _render_block(block_map.get(_BLOCK_HTML), ctx_data).strip() or None

        if not text_body:
            if html_body:
                text_body = strip_tags(html_body)
            else:
                text_body = ''

        return RenderedEmail(subject=subject, text_body=text_body, html_body=html_body)

    return renderer


def _render_block(block: BlockNode | None, context_data: dict[str, Any]) -> str:
    if block is None:
        return ''
    render_context = Context(context_data)
    return block.render(render_context)
