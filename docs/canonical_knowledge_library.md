# Canonical Knowledge Library

## Archaeology boundary

CKL is not the authoritative home of archaeological evidence. It stores
curated biblical context, people, places, events, themes, and interpretation.
The Archaeology subsystem owns material evidence and its media/licensing.
Legacy CKL objects in `objects/archaeology/` remain compatibility records for
stable historical IDs during migration; new archaeological content must be
authored in the archaeology domain. CKL UI can show compact related-evidence
cards without copying archaeological detail or image metadata.

## Runtime Storage

CKL JSON files remain the authoritative authoring source. They are human-readable,
validated, version-controlled, and reviewed in pull requests. SQLite is a
generated runtime serving artifact for faster exact lookup and bounded object
deserialization.

Default local runtime database:

```bash
.bhf/ckl.sqlite
```

This path works for local development and Docker because it is outside packaged
source files and can be rebuilt without modifying the repository. Release builds
may place a generated database under package data, but generated SQLite files
should not be manually edited or committed as source.

Lexical data uses the same generated SQLite artifact. Because Greek/Hebrew
source licensing may differ from the curated CKL JSON inventory, production
must explicitly choose one of these runtime policies:

- **Local-generated:** build `.bhf/ckl.sqlite` during deployment from local,
  ignored source checkouts under `data_sources/lexicons/`.
- **Bundled artifact:** distribute a generated lexical SQLite artifact only
  after every imported source permits redistribution and attribution is
  recorded.

Application startup must not download or parse raw lexical source files.

Build and verify:

```bash
python -m framework.canonical_library build-db --output .bhf/ckl.sqlite
python -m framework.canonical_library verify-db --database .bhf/ckl.sqlite
python -m framework.canonical_library db-info --database .bhf/ckl.sqlite
```

Lexical onboarding and smoke checks:

```bash
python tools/import_lexicons.py --output .bhf/ckl.sqlite --source-manifest <manifest.json> --rebuild
python tools/lexicon_onboard.py --manifest <manifest.json> --database .bhf/ckl.sqlite
python tools/lexicon_smoke.py --database .bhf/ckl.sqlite
```

The build loads `manifest.json`, validates every JSON object, populates a
temporary database, verifies metadata and integrity, then atomically replaces the
target path. If validation or verification fails, the previous database remains
in place.

SQLite stores the full validated canonical object in `payload_json` for
compatibility and also normalizes claims, claim scripture references, sources,
claim-to-source support, aliases, keywords, relationships, and object scripture
references. An FTS5 index covers high-signal object and claim text. Runtime
retrieval fuses deterministic exact/keyword/scripture scoring with bounded BM25
candidates, then ranks claims inside the selected objects and hydrates only the
sources linked to those claims. The BHF agent still controls query analysis,
guarded one-hop relationship expansion, context package construction, and
language-model prompting. The model does not query SQLite directly.

The current generated database schema is version 3 and the retrieval index is
version 2. Older artifacts fail with a rebuild command instead of being opened
silently. The build records both the semantic inventory fingerprint and a cheap
source inventory signature so normal startup can detect stale artifacts without
reparsing the complete JSON library.

Configuration example:

```json
{
  "canonical_library": {
    "backend": "sqlite",
    "database_path": ".bhf/ckl.sqlite",
    "json_root": "framework/canonical_library",
    "stale_database_policy": "error",
    "read_only": true,
    "repository_cache_size": 256
  }
}
```

Environment overrides:

```bash
BHF_CKL_BACKEND=sqlite
BHF_CKL_DATABASE_PATH=.bhf/ckl.sqlite
BHF_CKL_STALE_DATABASE_POLICY=error
```

Stale database policies:

- `error`: fail with a rebuild message when SQLite does not match JSON.
- `rebuild`: rebuild from JSON when missing or stale.
- `fallback_to_json`: use the JSON loader when SQLite is missing or stale.
- `ignore`: open SQLite without comparing to JSON.

Production should use `error` after building the database during deployment or
container image creation. Development may use `fallback_to_json` or `rebuild`.

Docker builds the database during image creation:

```bash
docker build .
```

The image build fails if CKL validation or database generation fails. The
container reads `/app/.bhf/ckl.sqlite` at runtime and does not rebuild it on
startup.

The Canonical Knowledge Library (CKL) is a version-controlled store of curated biblical knowledge that lives alongside, but separate from, the LLM. Its job is to return structured facts first so the model can act as a narrator and synthesizer rather than the primary source of biblical information.

CKL is the trusted floor of the BHF knowledge process, not its ceiling. It is
curated and intentionally non-exhaustive. The runtime does not use the CKL
relevance threshold as an answer-completeness score: a Ruth entry, for example,
may be highly relevant while omitting a legal, financial, or disputed scholarly
dimension asked by the user.

After local context retrieval, BHF records an answer-coverage assessment with
covered and missing dimensions. At the default thresholds (`0.85` sufficient,
`0.60` major gap), it routes to CKL-primary synthesis, targeted gap expansion,
or broad knowledge expansion. Explicit research-oriented questions can request
expansion even when the estimate is high. The score is only an explainable
routing heuristic; it is not a mathematically exact measure of all available
scholarship.

Expansion remains offline-safe. Broader model knowledge is permitted only when
configured and is kept distinct from CKL-supported facts. Optional external
research uses a provider-neutral interface and is disabled by default; no
network access is silently enabled. Strict mode blocks both model-knowledge and
external expansion, while provider failures leave the ordinary answer path
available.

## Purpose

CKL stores canonical facts, retrieval metadata, and future scholarship in a deterministic format. The CKL layer itself stops at the retrieval foundation: it does not infer theology, generate explanations, or call an LLM.

## Architectural Role

The long-term flow is:

1. User question
2. Canonical Knowledge Retrieval
3. Hermeneutical Framework
4. Prompt Context Builder
5. LLM
6. Final response

CKL supplies the curated object layer. The hermeneutical framework decides how those objects should be interpreted. The LLM then explains and synthesizes the already-retrieved material.

The framework guidance keeps the interpretive order outside CKL objects themselves: literary context, historical setting, Ancient Near Eastern context when relevant, Hebraic worldview, Second Temple Jewish context when relevant, covenantal-canonical storyline, Christological development when supported by the text, and modern application.

## Prompt Context

When CKL content is prepared for a model prompt, the context builder emits sections in a stable order when relevant:

1. Summary
2. Primary Scripture References
3. Sourced Claims
4. Immediate Literary Context
5. Historical Context
6. Ancient Near Eastern Context
7. Hebraic Worldview
8. Second Temple Context
9. Covenant and Canonical Context
10. Intertextual Connections
11. New Testament Connections
12. Interpretive Disputes and Cautions
13. Later Christian Reception
14. Sources

Each prompt entry also identifies its primary knowledge layer so biblical text,
historical context, theological synthesis, reception history, and application
remain distinguishable.

One unified retrieval policy keeps the prompt compact while preserving the main
canonical and historical layers. Legacy answer-mode values are accepted for
compatibility but do not change retrieved context or prompt detail.

Empty sections are skipped rather than padded with filler prose.

## Directory Structure

The CKL lives under `framework/canonical_library/` and is intentionally self-contained.

- `schema.py` defines the canonical object dataclass and validation rules.
- `loader.py` discovers JSON files, validates them, and builds in-memory indexes.
- `normalization.py` provides deterministic text and ID normalization.
- `retrieval.py` defines exact, hybrid, and future retrieval interfaces.
- `context_builder.py` assembles structured prompt context from retrieved objects.
- `authoring.py` provides template, validation, reporting, manifest, and migration helpers.
- `public_cache.py` implements the JSON-backed approved-answer cache.
- `manifest.json` records the library version and inventory counts.
- `.bhf/public-answer-cache.json` stores local cache entries when the cache is enabled.
- `objects/` stores one JSON object per file, grouped by category folder.

Supported object folders are:

- `theology/`
- `themes/`
- `people/`
- `places/`
- `events/`
- `books/`
- `word_studies/`
- `archaeology/`
- `institutions/`
- `prophecy/`
- `faq/`
- `timeline/`
- `covenants/`
- `biblical_theology/`
- `cultural_background/`
- `symbols/`
- `literary_devices/`
- `doctrine/`

The object `type` field stays singular even when the folder name is plural.

## Object Schema

Every canonical object uses the same base schema.

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | string | Canonical lowercase kebab-case identifier. |
| `type` | string | Supported category such as `person` or `place`. |
| `title` | string | Human-readable display name. |
| `aliases` | array of strings | Retrieval phrases and alternate names. |
| `summary` | string | Short curated summary. |
| `historical_context` | string | Historical background. |
| `ancient_near_east_context` | string | Ancient Near East comparison and setting. |
| `hebraic_worldview` | string | Israelite and Jewish worldview framing when relevant. |
| `second_temple_context` | string | Second Temple Jewish background for New Testament and late Second Temple material. |
| `canonical_context` | string | How the object fits the developing biblical storyline. |
| `later_christian_reception` | string | Later Christian interpretation kept distinct from original context. |
| `context_applicability` | object | Boolean flags that tell the context builder which context layers are relevant. |
| `literary_context` | string | Literary observations and genre framing. |
| `covenantal_significance` | string | How the object relates to covenant themes. |
| `intertextuality` | array of strings | Cross-book and canonical links. |
| `timeline` | array of strings | Ordered historical or canonical timeline points. |
| `maps` | array of strings | Geographic references and map anchors. |
| `archaeology` | array of strings | Archaeological references and artifacts. |
| `hebrew_words` | array of strings | Hebrew word-study anchors. |
| `greek_words` | array of strings | Greek word-study anchors. |
| `related_people` | array of strings | Related canonical people. |
| `related_places` | array of strings | Related canonical places. |
| `related_events` | array of strings | Related canonical events. |
| `related_objects` | array of typed relationship objects | Structured canonical links to other objects. |
| `scripture_references` | array of scripture-reference objects | Structured biblical reference anchors. |
| `cross_references` | array of strings | Internal reference pointers for later use. |
| `new_testament_connections` | array of strings | New Testament connection pointers. |
| `interpretive_notes` | array of structured note objects | Interpreter notes and cautions with optional note type, certainty, dispute status, and source IDs. Legacy strings are still accepted and normalized on load. |
| `claims` | array of structured claim objects | Granular claims with controlled type, certainty, dispute status, Scripture anchors, local source IDs, traditions, rationale, and notes. |
| `section_status` | object | Per-section migration and review state used by type-specific completeness rules. |
| `knowledge_layers` | object | One primary and zero or more secondary controlled knowledge layers. |
| `common_questions` | array of strings | Question prompts and FAQs. |
| `sources` | array of source objects | Structured source citations and bibliography with `id`, `source_type`, `title`, `author`, `publisher`, `year`, `locator`, `url`, `supports`, and `notes`. |
| `importance` | integer | Deterministic ranking hint for retrieval. |
| `framework_version` | string | CKL framework version gate. |
| `object_version` | string | Per-object schema version. |
| `content_status` | string | Content governance state for placeholder, draft, complete, or deprecated material. |
| `review_status` | string | Review workflow state for the canonical object. |
| `generated_by` | array of provenance objects | AI, migration, or import provenance for how the object was created or rewritten. |
| `edited_by` | array of strings | Human or tool editor names recorded separately from review. |
| `reviewed_by` | array of strings | Human reviewers who have signed off on the object. |
| `last_reviewed` | string or null | Most recent review date in `YYYY-MM-DD` format. |
| `confidence` | string | Governance confidence label for review and publication state. |
| `human_review_required` | boolean | Whether the record still needs human review before it can be treated as fully reviewed. |

The legacy `related_people`, `related_places`, and `related_events` fields remain supported for now. The context builder normalizes them into typed `related_objects` entries so downstream consumers can adopt the structured form gradually without losing compatibility with the existing inventory.

The `context_applicability` map is defaulted to all `true` on load for older objects. It lets authors suppress context layers that are not relevant to a particular entry without breaking the deterministic retrieval or prompt-construction pipeline.

`interpretive_notes` are now stored as structured note objects with this shape:

```json
{
  "note": "The covenant ceremony resembles Ancient Near Eastern treaty forms.",
  "note_type": "historical-context",
  "certainty": "strong_consensus",
  "dispute_status": "minor_scholarly_disagreement",
  "sources": ["source-id"],
  "scripture_references": ["Genesis 15:1-21"],
  "traditions": [],
  "rationale": "The classification is supported by the cited comparative sources."
}
```

Legacy string notes and the previous certainty/dispute labels remain readable
during migration. Approved notes must use the current taxonomies and include a
certainty rationale.

Current certainty values are `textually_explicit`, `strong_consensus`,
`probable`, `plausible`, `disputed`, `tradition_dependent`, `speculative`, and
`insufficient_evidence`. Current dispute values are `not_disputed`,
`minor_scholarly_disagreement`, `major_scholarly_disagreement`,
`denominational_disagreement`, `textual_variant`, `historical_uncertainty`,
`chronological_uncertainty`, `archaeological_uncertainty`, and
`lexical_uncertainty`.

Section completeness is additive and does not replace the legacy scalar
`content_status`:

```json
{
  "section_status": {
    "core_summary": "complete",
    "scripture_anchors": "complete",
    "historical_context": "draft",
    "literary_context": "needs_review",
    "canonical_context": "draft",
    "original_audience": "missing",
    "lexical_links": "not_applicable",
    "intertextuality": "draft",
    "interpretive_views": "missing",
    "common_misinterpretations": "missing",
    "sources": "needs_review",
    "relationships": "draft",
    "retrieval_metadata": "draft",
    "human_review": "missing"
  }
}
```

Allowed section states are `missing`, `generated`, `draft`, `needs_review`,
`reviewed`, `complete`, and `not_applicable`. Required sections vary by object
type. An approved object must mark all of its required sections `complete` or
`not_applicable`.

Knowledge layers use this shape:

```json
{
  "knowledge_layers": {
    "primary": "biblical_theology",
    "secondary": ["biblical_text", "historical_cultural"]
  }
}
```

Retrieval uses layer priority only as a deterministic tie-breaker after direct
relevance and evidence signals. It prefers biblical-text and literary layers
before historical context, lexical work, theological synthesis, reception
history, denominational interpretation, and pastoral application.

Granular claims use this shape:

```json
{
  "id": "genesis-ane-flood-context",
  "claim": "Genesis participates in an ancient Near Eastern flood-story environment while presenting distinct theological claims.",
  "claim_type": "historical_cultural",
  "certainty": "strong_consensus",
  "dispute_status": "minor_scholarly_disagreement",
  "scripture_references": ["Genesis 6:1-9:29"],
  "source_ids": ["approved-ane-reference-source"],
  "traditions": [],
  "rationale": "Multiple primary texts and modern comparative studies support the cultural comparison.",
  "notes": "Shared environment does not by itself demonstrate direct literary copying."
}
```

Claim source IDs resolve against the containing object's `sources` list.
Approved claims need a rationale and at least one Scripture reference or source
ID.

`sources` are now stored as structured source objects with this shape:

```json
{
  "id": "westermann-genesis",
  "source_type": "reference-work",
  "title": "Westermann, Genesis",
  "author": "",
  "publisher": "",
  "year": null,
  "locator": "",
  "url": "",
  "supports": [],
  "notes": ""
}
```

Legacy string sources are still accepted during migration. Scripture-like strings normalize to `source_type: "scripture"`, while other short legacy citations normalize conservatively to `reference-work`. Approved content still needs substantive sources, but the loader now preserves backward compatibility without leaving source records unstructured.

AI provenance is tracked separately from human review. Legacy `reviewed_by` values that identify Codex or other AI workflows migrate into `generated_by`, while `reviewed_by` remains reserved for human reviewers and `human_review_required` records whether the item still needs human sign-off.

Validation distinguishes between legacy inventory warnings and hard errors for newly authored content. The loader and authoring tools surface actionable issues for invalid schema fields, unsupported applicability metadata, generic repeated prose, weak source support, and other CKL hygiene problems without forcing the entire legacy inventory to fail migration.

## Validation And Retrieval Policy

The CKL validation layer now treats legacy content and new authoring content differently:

- Legacy inventory issues are surfaced as warnings when they help preserve backward compatibility.
- Newly authored content that violates the same rules should be treated as an error.
- Historical, lexical, and archaeological claims should carry the appropriate source types rather than generic filler sources.
- Broad generalizations, simplistic Hebrew-versus-Greek contrasts, generic ANE comparisons, and confessional claims presented as consensus are flagged for review.
- Mature records that mark a context layer as applicable should not leave that field empty.

The deterministic retrieval path also applies a production-oriented review filter:

- `context_applicability` defaults to `true` for older objects so legacy records stay searchable.
- The context builder suppresses inapplicable fields and skips empty prompt sections instead of padding them.
- The agent configuration defaults to excluding placeholders and unreviewed records unless the caller explicitly opts in with `allowed_statuses`.
- That keeps normal answers grounded in curated, reviewed material while still allowing development and migration workflows to inspect the fuller inventory.

Authoring guidance follows the same boundary:

- Prefer an accurate empty field over invented prose.
- Name the specific culture, institution, source, or practice when making an Ancient Near Eastern comparison.
- Keep later Christian reception separate from original historical meaning.
- Keep `generated_by` for AI or import provenance and `reviewed_by` for human review only.

## Book Record Fields

Book records carry a few extra metadata fields so canonical books can be searched and ranked more precisely:

- `authorship_positions`
- `date_ranges`
- `original_audience`
- `historical_setting`
- `genre`
- `structure`
- `major_themes`
- `canonical_placement`
- `key_people`
- `key_places`
- `key_events`
- `interpretive_disputes`
- `primary_sources`

These fields are part of the canonical book record shape and are populated across all 66 Bible-book objects.

## Placeholder Rules

The current inventory is intentionally thin. Each placeholder object contains:

- `id`
- `type`
- `title`
- `aliases`
- `importance`
- `framework_version`
- `object_version`
- `content_status` set to `placeholder`
- `review_status` set to `unreviewed`
- `generated_by` as an empty array
- `edited_by` as an empty array
- `reviewed_by` as an empty array
- `last_reviewed` as `null`
- `confidence` set to `unrated`
- `human_review_required` set to `true`

All other string fields are empty strings, and all collection fields are empty arrays. The governance metadata is defaulted on load for older JSON files, and legacy string `sources` values are migrated to structured source objects, so the current inventory remains backward compatible while the schema grows. That means the library can be tested, indexed, and queried without pretending scholarship exists where it does not.

The agent runtime now defaults to excluding placeholder records and unreviewed content unless a workflow explicitly opts in, so production answers stay grounded in curated material.

## Retrieval Flow

The deterministic retrieval path is:

1. Normalize the incoming question.
2. Try exact ID lookup.
3. Try exact alias lookup.
4. Try exact title lookup.
5. Try scripture-reference retrieval when the question mentions a passage.
6. Apply category-aware, phrase, fuzzy alias, and full-text ranking.
7. Package the results into structured, tiered context with estimated token counts.
8. Hand that context to the downstream prompt builder and, later, to the LLM.

This keeps lookups predictable. For example, `shechem` can be retrieved without the caller knowing that it lives in the places category.

## Scripture and Graph Index

CKL now keeps a local scripture reverse index and a relationship graph helper so reference questions can move through the inventory instead of relying on keyword coincidence alone.

- `retrieve_by_scripture_reference()` resolves normalized book, chapter, and verse queries back to the objects that cite those passages.
- `trace_relationship_graph()` follows `related_objects` chains outward from a seed object in a deterministic order.
- `audit_bidirectional_relationships()` reports missing reverse links as review items instead of failing the current inventory.

That gives the agent a safe way to surface Shechem, Abraham, covenant, Joshua, and Joseph together when a question is really about the Joshua 24 covenant-renewal chain.

## Token Reduction and Context Compression

CKL reduces prompt size by retrieving only the objects that matter for a question instead of asking the LLM to reconstruct broad biblical knowledge on every turn. The context builder tracks estimated topic tokens, removes duplicate facts, compacts sources, and uses one balanced context policy.

Relationship expansion is token-aware so the library can stay compact on small models.

## Smaller Local Models

Smaller models usually improve when they are given high-quality structure instead of raw open-ended prompts. CKL is designed to provide that structure so a compact local model can answer from targeted canonical data rather than improvise from memory.

## Hybrid Retrieval

`retrieve_hybrid()` wraps the deterministic local retrieval stack and combines
Scripture, category, phrase, fuzzy alias, keyword, and SQLite FTS5/BM25 scoring
without requiring an external vector store. It stays fully offline and
deterministic. The JSON backend retains deterministic keyword fallback but does
not promise result-for-result parity with SQLite on low-signal searches because
it has no FTS5 index.

Broad SQLite queries prefilter keyword rows to the actual query terms, cache
validated object hydration, and cache immutable field normalization. This keeps
the ranking formula stable while avoiding repeated scans and validation of
irrelevant index data.

## Retrieval Benchmarks and Golden Cases

The checked-in benchmark corpus at
`framework/canonical_library/benchmarks/retrieval_latency.json` covers ten
broad, multi-term queries. Run it against a built database with:

```bash
python tools/benchmark_ckl_retrieval.py \
  --database .bhf/ckl.sqlite \
  --iterations 5 \
  --warmups 1
```

The report includes per-query samples, median and p95 latency, anchor failures,
and a result fingerprint. Optional `--max-median-ms` and `--max-p95-ms` values
turn local or CI expectations into explicit gates without embedding
machine-specific timing limits in the corpus.

Object-ranking goldens remain in `tests/fixtures/ckl_golden_queries.json`.
Claim-ranking goldens in `tests/fixtures/ckl_claim_golden_queries.json` also
assert selected claim IDs, minimum scores, hydrated source IDs, and Scripture
references.

## Future Semantic Search

The retrieval layer still exposes `retrieve_semantic()` as the explicit future hook. It currently raises `NotImplementedError`, which keeps the contract honest while leaving room for a future embedding index or other semantic retrieval engine.

An optional semantic system can already be evaluated without becoming a
runtime dependency. Produce a JSON mapping from case ID to ranked CKL object
IDs, then compare it with the deterministic SQLite baseline:

```bash
python tools/evaluate_ckl_semantic.py \
  --database .bhf/ckl.sqlite \
  --candidate-results /path/to/candidate-results.json
```

The evaluator reports recall@k, reciprocal rank, and NDCG for both systems plus
candidate-minus-baseline deltas. It imports no embedding or model SDK; candidate
generation stays optional and outside the deterministic runtime.

## Cultural-Background Review Candidates

The cultural-background inventory includes source-backed candidates for
kinship/inheritance/redemption, patronage/hospitality/debt, ritual purity,
synagogue life, and Roman citizenship. They reuse explicit Scripture records
and academic sources already curated in the richer book records. Their
governance state is intentionally `in_review` with `human_review_required:
true`; an AI-authored synthesis is not represented as human scholarly review.

## Public Answer Cache

`public_cache.py` provides a small JSON-backed cache for reviewed answers. New
runtime lookups use the unified answer-format key; the stored answer-mode field
remains temporarily for compatibility with existing cache entries.

- `lookup()` returns a reviewed answer only when the cache entry is still current.
- `store()` persists the approved answer, object dependency IDs, review state, quality score, and fingerprints.
- `increment_usage()` tracks how often an answer is reused.
- `update_review_status()` lets the review state move forward or be retired later.

Expired, invalidated, or fingerprint-mismatched entries stay on disk for traceability but are not served.

## Versioning

Three version fields keep the CKL stable:

- `framework_version` identifies the CKL framework line.
- `schema_version` identifies the manifest/schema contract.
- `object_version` identifies the object payload shape.

The public answer cache stores the repository framework version fingerprint, the CKL inventory fingerprint, and the object dependency IDs for each approved answer so stale cache hits can be rejected when the source material changes.

The loader validates these values so old or incompatible inventory files fail fast.

## Packaging and Release

The release artifact now bundles the CKL inventory and the committed agent data
needed to resolve it in an installed environment.

- `framework/canonical_library/manifest.json`
- `framework/canonical_library/objects/**/*.json`
- `bhf_agent/data/*.json`

The installed distribution exposes a `ckl-version` command
(also `python -m framework.canonical_library`) that reports:

- The BHF release version and fingerprint.
- The CKL manifest framework/schema version.
- The CKL object count.
- The CKL inventory fingerprint.

CI builds the source and wheel artifacts and smoke-tests the installed wheel so
packaging regressions show up before release.

The current stable CKL release is tagged `v0.2.0`.

## Adding New Objects

Safe contributor workflow:

1. Create a new JSON file under the correct folder in `framework/canonical_library/objects/`.
2. Use a lowercase kebab-case `id` that matches the filename.
3. Add retrieval aliases, but keep them as phrases, not answers.
4. Validate the file with the CKL schema and tests.
5. Update or regenerate `manifest.json`.
6. Run the CKL test suite.

## Authoring Tools

The CKL tooling under `tools/` removes most of the manual JSON friction:

- `python tools/ckl_create.py --type person --id abraham --write`
- `python tools/ckl_validate.py --path framework/canonical_library/objects/people/abraham.json`
- `python tools/ckl_manifest.py --root framework/canonical_library --write --stamp`
- `python tools/ckl_report.py --root framework/canonical_library`
- `python tools/ckl_expansion_backlog.py --root framework/canonical_library
  --lane people --limit 25`
- `python tools/ckl_migrate.py --root framework/canonical_library --write`

`ckl_create.py` generates a fresh template, `ckl_validate.py` checks either a
single file or the whole library, `ckl_manifest.py` rebuilds the inventory
counts, `ckl_report.py` summarizes status, `ckl_expansion_backlog.py` ranks
people/place/thing expansion candidates, and `ckl_migrate.py` rewrites legacy
JSON into the normalized schema. None of the scripts write to disk unless
`--write` or `--output` is supplied.

## Populating Scholarship Later

Future scholarship must be curated, sourced, and reviewed before it is written into the CKL. Interpretive rules and canonical facts should remain separate so that the hermeneutical framework can guide interpretation without collapsing into the knowledge store itself.

Approved objects should use structured source entries rather than legacy strings, and they should carry substantive source support plus review metadata before they are treated as publishable.

For the current CKL request path and evidence boundary, see
[`docs/architecture.md`](architecture.md#answer-flow).
