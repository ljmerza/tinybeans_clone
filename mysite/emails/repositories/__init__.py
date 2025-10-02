"""Repository implementations for email domain models."""

from .templates import EmailTemplateRepository, InMemoryEmailTemplateRepository

__all__ = ['EmailTemplateRepository', 'InMemoryEmailTemplateRepository']
