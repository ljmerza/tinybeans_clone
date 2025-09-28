import uuid
from django.utils.text import slugify


def generate_unique_slug(base_value: str, queryset):
    """Generate a unique slug for a given base value and queryset."""
    base_slug = slugify(base_value) or uuid.uuid4().hex[:12]
    slug = base_slug
    counter = 1
    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug