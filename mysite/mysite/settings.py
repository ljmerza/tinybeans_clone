"""Compatibility shim for legacy imports.

Default to local settings; prefer setting DJANGO_SETTINGS_MODULE to
`mysite.config.settings.<environment>` explicitly.
"""

from mysite.config.settings.local import *  # noqa: F401,F403
