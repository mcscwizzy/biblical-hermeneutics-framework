# Commentary v1.2 five-chapter structured enrichment

The bounded enrichment covered exactly five chapters: Psalms 19, Psalms 103,
2 Kings 4, Psalms 2, and Genesis 5. Editorial claims were proposed before CKL
mutation and added as source-addressable child claims with exact verse anchors.
Parent legacy prose was not promoted.

## Deterministic result

The immutable artifact is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-five-chapter-structured-enrichment-v1-22e32598/`

All five chapters passed the deterministic threshold. Each had legal current-
chapter renderer paths, valid ancestry and provenance, resolved source IDs,
zero duplicate inflation, and zero legally promoted legacy evidence. Raw legacy
records remain visible only as background evidence.

Psalm 2 used a bounded task-local canonical-text projection that removes the
known Psalm 3 heading contamination from the final verse. The committed ASV
dataset was not modified. The renderer audit reports surrounding-passage paths
as ambiguous when their source scope is not the current chapter; these paths
retain their exact source references and are not counted as current-chapter
hard errors.

## Model result

Because all five chapters passed, exactly one fresh `gpt-5.6-sol` generation at
medium effort was run per chapter. The final validation artifact is
`final-report-v3.json`: 5/5 structurally valid, 5/5 Gate PASS, zero high-dump
outputs, zero ancestry mismatches, and PASS readability/normal-reader
usefulness for every chapter.

Recommendation: `READY_FOR_BROADER_PILOT`.

The raw responses, normalized outputs, validation records, deterministic hashes,
contract identities, and editorial proposal are retained in the immutable
artifact namespace.
