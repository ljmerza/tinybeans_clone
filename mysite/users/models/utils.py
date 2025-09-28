"""Model utility functions for the users app.

This module contains helper functions for working with Django models,
particularly for generating unique identifiers and slugs.
"""
import uuid
from django.utils.text import slugify


def generate_unique_slug(base_value: str, queryset):
    """Generate a unique slug for a given base value and queryset.
    
    This function creates a URL-friendly slug from the base_value. If the
    resulting slug already exists in the queryset, it appends a counter
    to make it unique.
    
    Args:
        base_value: The string to convert to a slug (e.g., a title or name)
        queryset: Django QuerySet to check for existing slugs
        
    Returns:
        A unique slug string that doesn't exist in the queryset
        
    Example:
        >>> qs = Article.objects.all()
        >>> generate_unique_slug("My Article Title", qs)
        "my-article-title"
        >>> # If "my-article-title" exists, returns "my-article-title-1"
    """
    base_slug = slugify(base_value) or uuid.uuid4().hex[:12]
    slug = base_slug
    counter = 1
    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug