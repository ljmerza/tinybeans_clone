"""Cursor pagination for agent post lists, oldest or newest first."""

from urllib.parse import parse_qs, urlparse

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import CursorPagination

ORDERS = ("oldest", "newest")


class AgentPostPagination(CursorPagination):
    """Oldest first by default; ``order=newest`` flips every ordering field.

    The cursor positions on ``date_of_memory``; ``created_at`` and ``id``
    break ties between posts imported with the same date.
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 50
    ordering = ("date_of_memory", "created_at", "id")

    def get_ordering(self, request, queryset, view):
        if request.query_params.get("order") == "newest":
            return tuple(f"-{field}" for field in self.ordering)
        return self.ordering

    def decode_cursor(self, request):
        try:
            return super().decode_cursor(request)
        except NotFound:
            raise ValidationError({"cursor": "Not a valid cursor."}) from None

    def get_next_cursor(self):
        """The bare cursor for the next page, or None; the API never returns URLs."""
        link = self.get_next_link()
        if not link:
            return None
        return parse_qs(urlparse(link).query).get(self.cursor_query_param, [None])[0]
