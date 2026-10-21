# NE-9A methodology

## Baseline and inputs

The audit used the verified `origin/master` commit `fc8234947fc01b3adc95437ccde709cce1cf1232`, which includes NE-8B PR #38. It reviewed:

- NE-A1’s coverage audit and selected narrative trails in `docs/narrative-explorer/coverage-audit/`.
- NE-A2’s relationship inventory, mapping policy, and before/after report in `docs/narrative-explorer/ne-a2/`.
- The evidence and connection contract at `docs/narrative-explorer/03-evidence-and-connection-contract.md`.
- CKL schema, JSON objects, `evidence_graph_edges()`, CKL loader, and the current Narrative Explorer projection and interaction contract.
- NE-8B’s connection-discovery results and source-backed preview criteria.
- Seven pilot threads: Genesis 1–3; Genesis 6; Deuteronomy 32; Psalm 82; Exodus 3; John 1; Revelation 21–22.

The three passage-review passes covered Genesis; Deuteronomy/Psalm 82/Exodus 3; and John/Revelation. No source record was edited. The NE-A1 and NE-A2 counts are compared as historical/current projection versions, not treated as competing counts of the underlying CKL.

## Reproduction

From a complete checkout, recreate and verify the inventory in a temporary location:

```sh
python3 scripts/audit_ckl_connection_coverage.py \
  --source-root . \
  --output /tmp/ne9a-relationship-inventory.csv
python3 -c 'import hashlib; p="/tmp/ne9a-relationship-inventory.csv"; print(hashlib.sha256(open(p,"rb").read()).hexdigest())'
```

The script imports the repository’s `CanonicalLibrary`, `evidence_graph_edges()`, `normalize_id()`, and Narrative Explorer’s exact `_CONNECTION_TYPE_BY_LABEL` mapping. It reads CKL JSON and writes only the requested CSV and a summary to stdout. It does not open SQLite, create a database, regenerate evidence, or edit CKL records.

The expected export has 53,097 data rows (53,098 lines including the header), 53,638,723 bytes, and SHA-256 `b03b5ce267e415b997e6d1cfbe8fe69049731b3a4b10262f1e77d8e395aedef4`. The command's JSON summary must report `validation_status: passed`, 687 loaded and manifest objects, CKL fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`, object-tree SHA-256 `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`, and manifest SHA-256 `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4`. The raw CKL object tree and manifest are the protected inputs; regenerate the export instead of checking in another duplicate snapshot.

## Classification boundaries

### Relationship records

- A formal top-level edge is one `CanonicalRelationship` in a CKL object’s `related_objects` list. Its source ID, target ID, original label, weight-derived record identity, notes, direction, and projection category are retained.
- `evidence_graph_edges()` supplies existing authored evidence-to-object and evidence-to-evidence links, passage anchors, claim/evidence membership, evidence/source links, geography, historical period, and external references. The export supplements graph output with claim-source, object-source, interpretive-note-source, relationship-list, and selected legacy metadata fields that this projection does not include.
- Nested record membership and provenance rows are inventoried, but they are not counted as new literary or theological relationships. In particular, passage-to-record rows describe applicability; they do not establish a connection between passages.
- Object-to-object relationships have no edge-level evidence IDs, source IDs, temporal qualification, uncertainty, or review-status fields in the current `CanonicalRelationship` schema. The CSV records those values as not recorded on the edge rather than inheriting the parent object’s bibliography as if it supported that specific edge. Relevant claim and evidence rows carry their own available source, passage, temporal, certainty, dispute, and review metadata.
- Free-text values in `related_people`, `key_places`, `maps`, `timeline`, and similar fields are retained as field associations. A value matching a CKL ID is marked resolved; a narrative description is marked descriptive text. `canonical_story.preceded_by` and `followed_by` values are treated the same way. Neither field family is silently converted into an authored `related_objects` relationship.

### Direction, scope, and source status

- A top-level edge is reciprocal only when the reverse source/target pair has the exact same original relationship label. An edge with a reverse endpoint but a different label remains one-way for this measure. No reverse edge is generated.
- Evidence-to-evidence and evidence-to-object edges use the same exact reverse-label rule. Graph-generated anchors and provenance have structural direction and are not included in authored relationship direction totals.
- Passage scope is copied from authored Scripture references and explicitly scoped evidence records. It is not widened from a book title or topic overlap. Evidence source IDs are resolved only against the source records on the owning CKL object; two missing object-local records remain unresolved.
- Temporal fields preserve the CKL record as written. They are not inferred from source dates, later literary parallels, manuscript dates, or object-level historical ranges.

### Reader-facing categories

The audit uses the requested classifications:

- **A — Existing connection, UI/projection gap:** the supported relationship exists in CKL but a reader cannot reach its supported destination or the projection omits its recorded basis.
- **B — Existing relationship, classification issue:** an authored edge or anchor exists, but its type, passage scope, direction, rationale, or metadata needs review.
- **C — Supported candidate for CKL curation:** relevant CKL material already supplies a traceable basis, but a new edge still needs separate scholarly/source-owner approval.
- **D — Research gap:** the potential connection lacks sufficient passage-scoped support in current CKL material.
- **E — Do not promote:** the proposed edge would imply dependence, equivalence, chronology, geography, or identity beyond what the records establish.

These categories classify the audit finding, not the truth of a historical or theological claim. An uncategorized association may be useful descriptive metadata; a Scripture anchor can be accurate and still not be an intertextual edge.

## Integrity and deterministic validation

Validation used the current CKL loader and validator, plus protected database checks in read-only mode. The JSON inventory and CKL cache agree on the 687-object inventory fingerprint. Both protected SQLite files passed `PRAGMA quick_check`; neither was written. The CKL validator returned 687 valid objects, zero errors, and 14 warning records about incomplete section-status metadata. CSV validation checks the manifest count, complete group totals, relationship counts, target-status categories, exact reverse pairs, and the output fingerprint.

The exporter checks unique row IDs, complete group totals, reciprocal reverse references, exact-direction totals, and passage-anchor source shape before writing. It then streams the written CSV to verify row count and unique IDs. An independent audit pass recomputes the full CSV counts and compared the deterministic output hash. The export’s top-level relationship totals match NE-A2’s independently documented results: 4,061 total, 113 mapped, 3,948 uncategorized, 98 reciprocal pairs, and 3,865 one-way edges. NE-A1’s 4,061-all-uncategorized figure remains labeled historical throughout this audit.
