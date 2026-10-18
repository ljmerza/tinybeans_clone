"""``request.user`` for API token requests."""

from __future__ import annotations


class ApiTokenPrincipal:
    """Stands in for a user on agent API requests; it is a circle, not a person.

    ``pk`` and ``id`` raise instead of returning None: otherwise user-scoped
    code such as ``filter(created_by_id=request.user.pk)`` would quietly match
    rows with no owner, in any circle. Every accidental reuse fails closed.
    """

    is_authenticated = True
    is_anonymous = False
    is_active = True
    is_staff = False
    is_superuser = False

    def __init__(self, token):
        self.token = token
        self.circle_id = token.circle_id

    @property
    def pk(self):
        raise RuntimeError("An API token is not a user; use request.auth.circle_id.")

    @property
    def id(self):
        raise RuntimeError("An API token is not a user; use request.auth.circle_id.")

    def __str__(self):
        return f"API token {self.token.display_prefix}"
