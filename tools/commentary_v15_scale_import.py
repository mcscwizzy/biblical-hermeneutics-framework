#!/usr/bin/env python3
"""Import and hard-validate one Commentary 1.5 scale-pilot wave."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.commentary_canary_import import import_responses


TARGET_ROOT = ROOT / ".bhf-data/bhf-commentary-candidates/commentary-v1.5-scale-pilot"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", required=True, choices=("A", "B", "C"))
    parser.add_argument("--candidate-root", type=Path, default=TARGET_ROOT)
    args = parser.parse_args()
    wave_root = args.candidate_root / f"wave-{args.wave.lower()}"
    result = import_responses(candidate_root=wave_root, input_dir=wave_root / "canary/responses/raw", repo_root=ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
