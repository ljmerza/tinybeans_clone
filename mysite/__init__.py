"""Project package aggregator for Django apps and settings."""
from pathlib import Path
from pkgutil import extend_path

# Support namespace-style imports while keeping the legacy "mysite" project package
# under ``mysite/mysite``.
__path__ = list(extend_path(__path__, __name__))  # type: ignore  # noqa: F821
_inner = Path(__file__).resolve().parent / 'mysite'
if _inner.exists():
    __path__.append(str(_inner))

__all__ = []
