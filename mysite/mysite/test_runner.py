"""Custom test runner that remaps ``mysite.<app>`` imports.

When the Django test discovery process attempts to import modules under the
``mysite`` namespace (for example ``mysite.auth.tests``), Python resolves them to
the top-level project package instead of the individual app packages (``auth``,
``users``, etc.). That triggers `ModuleNotFoundError` cascades or prevents Django
from associating models with the correct app label during test runs.

To keep the developer ergonomics of running ``python manage.py test`` while the
apps continue to live as top-level packages, we provide a custom test loader
that transparently falls back to importing the actual app module when a
``mysite.<app>`` import fails. The module object is then aliased back on
``sys.modules`` so future imports see the already-loaded module and Django uses
the canonical module path (``auth.models``, ``users.models`` and so on).
"""

from __future__ import annotations

import importlib
import sys
import unittest
from types import ModuleType

from django.test.runner import DiscoverRunner

_NAMESPACE_PREFIX = "mysite."


class _NamespacedTestLoader(unittest.TestLoader):
    """Test loader that aliases ``mysite.<app>`` imports to the real app module."""

    def _get_module_from_name(self, name: str) -> ModuleType:  # type: ignore[override]
        if name.startswith(_NAMESPACE_PREFIX):
            fallback_name = name.removeprefix(_NAMESPACE_PREFIX)
            if fallback_name:
                module = importlib.import_module(fallback_name)
                sys.modules[name] = module
                return module

        return super()._get_module_from_name(name)


class ProjectDiscoverRunner(DiscoverRunner):
    """Django test runner that relies on the namespace-aware loader."""

    test_loader = _NamespacedTestLoader()
