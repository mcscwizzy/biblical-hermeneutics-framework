"""Build-time importers for external lexical datasets."""

from .openscriptures_greek import import_greek
from .openscriptures_hebrew import import_hebrew

__all__ = ["import_greek", "import_hebrew"]
