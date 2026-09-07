#!/usr/bin/env python3
"""Print deterministic Commentary v1.2 consolidation diagnostics.

The command reads persisted canary artifacts and the local EvidenceBundle.  It
never calls a renderer and never writes commentary or pipeline state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from bhf_agent.chapter_commentary.consolidation import (
    audit_prose_overlap,
    consolidation_metrics,
    map_commentary_blocks,
)
from bhf_agent.chapter_commentary.evidence_bundling import get_chapter_evidence_bundle
from bhf_agent.chapter_commentary.storage import load_commentary
from bhf_agent.chapter_commentary.synthesis.storage import load_synthesis
from bhf_agent.presentation.models import EVIDENCE_BUNDLE_CANDIDATE_VERSION


CANARY_ROOT = Path(
    ".bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/canary"
)


def audit_canary(book: str, chapter: int, root: Path = CANARY_ROOT) -> dict:
    synthesis = load_synthesis(root / "synthesis", book, chapter)
    commentary = load_commentary(root / "responses/accepted", book, chapter)
    bundle = get_chapter_evidence_bundle(
        book, chapter, evidence_bundle_version=EVIDENCE_BUNDLE_CANDIDATE_VERSION
    )
    if synthesis is None or commentary is None or bundle is None:
        raise RuntimeError(f"missing canary artifacts for {book} {chapter}")
    records, clusters = map_commentary_blocks(
        commentary, synthesis.synthesis_units, bundle.evidence_items
    )
    overlaps = audit_prose_overlap(records)
    return {
        "reference": f"{book} {chapter}",
        "metrics": consolidation_metrics(records, clusters, overlaps),
        "blocks": [record.to_dict() for record in records],
        "idea_clusters": [cluster.to_dict() for cluster in clusters],
        "prose_overlap_pairs": [overlap.to_dict() for overlap in overlaps],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    parser.add_argument("--root", type=Path, default=CANARY_ROOT)
    args = parser.parse_args()
    print(json.dumps(audit_canary(args.book, args.chapter, args.root), indent=2))


if __name__ == "__main__":
    main()
