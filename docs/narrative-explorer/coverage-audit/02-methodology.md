# NE-A1 methodology

## Corpus and baseline

- NE-5B base: `8e6283a68c020691161278504127e566f63c41a4`; known NE-1 through NE-5B hashes are recorded in `methodology-validation.json`.
- CKL source: validated committed JSON under `framework/canonical_library/objects/`; manifest declares 687 objects and loader validated 687.
- Canonical chapter identity: committed ASV `books[].chapters[]`, cross-checked against `bhf_agent.references.BOOKS` (66 names; 1,189 chapters).

## Census algorithm

1. Load `CanonicalLibrary` once. Use its normalized Scripture book index and parsed per-object reference spans to construct candidate object IDs for all chapters. Candidate matching uses the repository's `scripture_reference_overlaps` semantics and the same retrieval status filters (`include_placeholders=True`, deprecated/rejected excluded).
2. Pass each chapter's candidate objects to `project_narrative_explorer` with a complete CKL lookup. The projector applies the existing broad-anchor and semantic-misanchor rules, parent/child distinction, NE-5A section taxonomy, source hydration, and CKL relationship projection.
3. Count projected parents, claims, evidence items, and interpretive notes separately. Passage-specific coverage requires a projected claim or evidence item whose source ID resolves to a parent bibliography entry with a title and at least one author/publisher/year/locator/URL field. Object counts alone do not qualify.
4. Check CKL references against the canonical book/chapter/verse bounds. Read existing map and archaeology link tables using SQLite URI `mode=ro` plus `PRAGMA query_only=ON`; validate targets and bounds, then associate valid rows with chapters by overlap. These are explicit link inventory counts, not complete resolver results.
5. Run a seeded cross-canon sample through standard CKL Scripture retrieval and the normal `NarrativeExplorerService.build` path. Compare candidate IDs, projected CKL item IDs, section assignment, and CKL connection IDs for every selected chapter. Run full resolver-backed builds only for the seven pilots plus one seeded chapter per stratum; record map/archaeology IDs and states separately.

## Coverage definitions

- `passage_specific_evidence`: complete CKL lookup and at least one directly projected claim or evidence item with resolvable source details.
- `contextual_coverage`: CKL items are projected, but no source-grounded claim/evidence item meets the definition above.
- `entity_only_coverage`: only eligible parent entities of type person, people-group, place, or event are represented.
- `no_eligible_ckl_material`: completed CKL retrieval/projection returned no eligible item for that chapter.
- `incomplete_or_unknown`: retrieval/index coverage or an unparseable/out-of-canon anchor associated with a book prevents a conclusive chapter judgment.
- Map/archaeology full API resolution is `unknown_not_run` outside the sample. An empty explicit-link table is not a claim that no relevant evidence exists.

## Assumptions and limits

- CKL source anchors are parsed with BHF's canonical Scripture parser; no generic keyword classification is used for the cosmic-geography section.
- The exact NE-5A special cosmic rules are left unchanged. A physical location, general presence/temple/mountain theme, or generic worldview-concept does not gain a cosmic label by this audit.
- Source bibliography resolution is reported by resolvable source ID and a stricter title-plus-author/publisher/year/locator/URL check; passage-specific category requires the stricter traceability check.
- Physical coordinates and geometry are never generated. Stored coordinates do not establish site identification.
- Topic trails use explicit stable IDs and authored relationship edges only. Shared terms do not create an intertextual relationship.
- Dynamic map text matches, archaeological text-first matches, and empty resolver results are exact only for the sampled live builds; other per-chapter resolver states remain unknown.
- Run: `python3 scripts/audit_narrative_explorer_coverage.py --output-dir docs/narrative-explorer/coverage-audit`.
