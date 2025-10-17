"""Project package aggregator for Django apps and settings."""
from pathlib import Path

_package_dir = Path(__file__).resolve().parent
_inner = _package_dir / 'mysite'

# Expose both the app collection (mysite/*) and the legacy project package (mysite/mysite/*)
# on the same import namespace.
__path__ = [str(_package_dir)]
if _inner.exists():
    __path__.append(str(_inner))

__all__ = []
