"""
QuickLender — Celery App Loader

NOTE: If you see "ImportError: cannot import name 'Celery' from 'celery'",
it means there is a file named celery.py in the backend/ directory that
conflicts with the celery library. Delete it:
    Windows: del celery.py
    Mac/Linux: rm celery.py
"""
import sys
import os

# Auto-detect and warn about celery.py naming conflict
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_conflict_file = os.path.join(_backend_dir, 'celery.py')
if os.path.exists(_conflict_file):
    import warnings
    warnings.warn(
        f"\n\n"
        f"  CONFLICT: {_conflict_file}\n"
        f"  A file named 'celery.py' in the backend/ folder shadows the celery library.\n"
        f"  Delete it by running this command in the backend/ folder:\n"
        f"    Windows: del celery.py\n"
        f"    Mac/Linux: rm celery.py\n",
        stacklevel=2
    )

try:
    from .celery_app import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    pass
