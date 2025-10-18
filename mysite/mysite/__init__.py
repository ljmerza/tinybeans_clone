from pathlib import Path
import sys

# Ensure the project root (containing the aggregate `mysite` package and top-level apps)
# is on sys.path when Celery/Flower import this inner package directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .celery import app as celery_app

__all__ = ('celery_app',)
