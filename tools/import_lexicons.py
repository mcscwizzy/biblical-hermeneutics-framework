#!/usr/bin/env python3
"""Import local lexical source data into the CKL SQLite database."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.canonical_library.lexicon_importer import main


if __name__ == "__main__":
    raise SystemExit(main())
