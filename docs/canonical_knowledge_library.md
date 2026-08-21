# Canonical Knowledge Library

## Archaeology boundary

CKL is not the authoritative home of archaeological catalog or media data. It stores
curated biblical context, people, places, events, themes, claims, and
passage-specific evidence relationships.
The Archaeology subsystem owns material evidence and its media/licensing.
Legacy CKL objects in `objects/archaeology/` remain compatibility records for
stable historical IDs during migration. New artifact/site catalog content and
rights-aware media must be authored in the archaeology domain. CKL evidence
items may point to those records with `external_references`; they add an
auditable passage relationship and relevance explanation without copying media.

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
python -m framework.canonical_library migrate-db --database .bhf/ckl.sqlite
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
references. Evidence items, chronology, passage links, evidence-to-claim/source
links, object/geography/evidence relationships, and external-domain references
are normalized into indexed tables. An FTS5 index covers high-signal object,
claim, and evidence text. Runtime
retrieval fuses deterministic exact/keyword/scripture scoring with bounded BM25
candidates, then ranks claims inside the selected objects and hydrates only the
sources linked to those claims. The BHF agent still controls query analysis,
guarded one-hop relationship expansion, context package construction, and
language-model prompting. The model does not query SQLite directly.

The current generated database schema is version 4 and the retrieval index is
version 3. The additive `3 -> 4` migration creates evidence and temporal tables,
preserves existing rows, and writes a versioned backup by default. It derives
default object chronology from the stored payload. Rebuild after authoring new
JSON evidence because a version 3 artifact cannot contain the new normalized
evidence rows. Versions without a supported migration fail with a rebuild
instruction rather than being opened silently. The build records both the semantic inventory fingerprint and a cheap
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

## Architecture audit (2026-08-15)

The evidence expansion began with a read-only inventory and contract audit:

- The authoritative inventory contains 646 validated objects across 18 object
  categories. JSON remains the reviewable source of truth; the manifest carries
  counts and framework/schema versions.
- `schema.py` already provided a typed canonical object, claims, structured
  sources, Scripture anchors, governance, knowledge layers, and object
  relationships. The evidence work extends that model rather than replacing it.
- `loader.py` and `authoring.py` own JSON discovery, default migration,
  validation, indexing, fingerprints, templates, reports, and manifest checks.
- The generated SQLite store already normalized objects, aliases, keywords,
  relationships, Scripture references, claims, sources, FTS5 documents, and
  lexicon tables. Schema v4 adds evidence tables without changing JSON
  authority or deleting legacy tables.
- Retrieval already combined exact ID/title/alias, Scripture, weighted fields,
  category and governance signals, guarded object relationships, and optional
  SQLite BM25. Evidence ranking is now a bounded second stage inside those
  selected subjects.
- `context_builder.py` already budgeted and packaged claims, sources, context
  layers, cautions, relationships, and coverage metadata. It now packages
  selected evidence and its relevance/chronology labels before model synthesis.
- Passage linking existed at object and claim levels. Evidence links add an
  explicit relationship, weight, temporal relation, and relevance rationale;
  both JSON and SQLite reverse passage lookup include those links.
- Archaeology was already a mature peer domain with sites, items, Scripture
  links, details, confidence, stable CKL links, and rights-aware media. It is
  preserved rather than folded into CKL.
- Historical/cultural coverage remains broad but uneven. Twenty focused
  evidence clusters now span Genesis/ANE through first-century Galilee and
  Judea while remaining in explicit human-review state.
- Temporal information previously lived mostly in prose, book date ranges, and
  timeline entries. It could not reliably distinguish artifact date, narrative
  setting, source composition, or comparative chronological distance.
- Sources and claims were structured and normalized, but a passage-specific
  evidence unit had no required “why this matters” field or confidence
  explanation. The new evidence contract supplies both.
- FastAPI search/detail routes and prompt packets are additive consumers of the
  canonical payload. New `temporal_scope`, `evidence_items`,
  `selected_evidence`, counts, resolved sources, and coverage fields preserve
  existing keys and older JSON defaults.

This audit also found stale inventory expectations and a golden-claim test
coupled to an old local schema-v3 database. The current tests assert the
regenerated manifest and build a fresh database for schema-sensitive checks.

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
4. Contextual Evidence
5. Immediate Literary Context
6. Historical Context
7. Ancient Near Eastern Context
8. Hebraic Worldview
9. Second Temple Context
10. Covenant and Canonical Context
11. Intertextual Connections
12. New Testament Connections
13. Interpretive Disputes and Cautions
14. Later Christian Reception
15. Sources

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
- `evidence_models.py` defines evidence, chronology, passage-link, and cross-domain types.
- `evidence_retrieval.py` ranks evidence inside selected subjects.
- `evidence_graph.py` projects graph-shaped audit edges from the authored records.
- `evidence_audit.py` emits future-review signals without rewriting evidence.
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
| `temporal_scope` | object | Signed BCE/CE range, named periods, narrative setting, and separate source-composition range. |
| `evidence_items` | array of evidence objects | Auditable evidence, provenance, confidence rationale, passage relevance, chronology, and relationships. |
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

The `context_applicability` map defaults every dimension to `false`. Context is
opt-in: authors enable a layer only when its corresponding field contains
specific, useful material. Explicit legacy flags remain readable, while the
corpus audit rejects enabled-but-empty layers and reports suspiciously broad
template-driven applicability.

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

## Evidence architecture

CKL remains an evidence system rather than an answer system. JSON is the
authoritative record and SQLite is a normalized projection. The conceptual
chain is:

```text
Passage -> Subject -> Claim -> Evidence -> Source
                        |         |
                        |         +-> Location / period / related evidence
                        +------------> certainty and dispute state
```

`evidence_graph_edges()` exposes that chain deterministically for audit and
tooling. Object-local evidence, claim, and source IDs are namespaced in the
projection so identifiers from different objects cannot collide. No graph
database, embedding service, or LLM is required.

Evidence types cover artifacts, sites, inscriptions, ancient texts,
manuscripts, historical events and periods, people and groups, institutions,
cultural practices, geography/environment, literary conventions, worldview
concepts, primary and secondary sources, and material culture. A single item
must not blur observation and interpretation:

```json
{
  "id": "cyrus-cylinder-restoration-context",
  "title": "Cyrus Cylinder imperial restoration rhetoric",
  "evidence_type": "inscription",
  "description": "A Babylonian foundation inscription from Cyrus's reign.",
  "assertion_type": "primary-evidence",
  "confidence": "high",
  "confidence_rationale": "The artifact and setting are secure; policy scope requires qualification.",
  "passage_relevance": "It supplies Persian imperial context for Ezra 1 but is not Ezra's decree.",
  "certainty": "strong_consensus",
  "dispute_status": "minor_scholarly_disagreement",
  "primary_observation": "The inscription reports cult restoration in its Babylonian setting.",
  "scholarly_interpretation": "Historians compare this rhetoric with wider Achaemenid policy.",
  "temporal_scope": {
    "start_year": -539,
    "end_year": -538,
    "approximate": false,
    "periods": ["early Achaemenid period"],
    "narrative_setting": "Cyrus's conquest of Babylon",
    "source_composition_start_year": -539,
    "source_composition_end_year": -538,
    "source_composition_approximate": false,
    "notes": ""
  },
  "geography_ids": ["babylon-1", "persia"],
  "related_objects": [],
  "related_evidence": [],
  "scripture_references": [{
    "reference": "Ezra 1:1-11",
    "relationship": "comparative",
    "temporal_relation": "near-contemporary",
    "relevance_rationale": "The sources share an imperial horizon but are not the same decree.",
    "weight": 8
  }],
  "source_ids": ["cyrus-cylinder"],
  "claim_ids": ["cylinder-babylon-restoration-rhetoric"],
  "external_references": [{
    "domain": "archaeology-item",
    "id": "cyrus-cylinder",
    "relationship": "same-evidence",
    "notes": "Media remains in the archaeology domain."
  }],
  "metadata": {"archaeological_period": "early Achaemenid period"},
  "notes": "No modern translation or image is stored."
}
```

### Authoring examples by evidence class

These checked-in records show the intended pattern. Reuse the pattern, not the
conclusion or confidence label:

| Evidence class | Corpus example | What makes it well formed |
| --- | --- | --- |
| Archaeology | `lachish-relief-royal-siege-rhetoric` | Identifies the museum object and installation date, links the archaeology domain, and treats royal imagery as rhetoric rather than a neutral event transcript. |
| Cultural practice | `exodus-brickmaking-and-quota` | Starts with the actions in Exodus 5, then keeps Egyptian material comparison in a separate item. |
| Primary ancient text | `gilgamesh-tablet-xi-flood-comparison` | Cites tablet K.3375 and a critical edition, distinguishes the surviving tablet date from the older tradition, and does not claim direct Genesis dependence. |
| Geography | `thessalonian-politarch-inscription` | Uses the specific city and Roman Macedonian region, not a vague “Mediterranean” association; the evidence is linked to Acts 17 because the title is locally attested. |
| Literary convention | `parousia-apantesis-civic-arrival-proposal` | Labels civic-reception imagery a scholarly reconstruction and does not turn a proposed social script into a lexical definition. |
| Worldview concept | `psalm-82-assembly-language` | Records the Psalm's wording first, lists competing identifications separately, and gives no reconstructed ontology canonical status. |
| Disputed evidence | `deuteronomy-32-8-manuscript-variant` | Names the textual witnesses, uses `textual_variant`, and separates the extant readings from their theological implications. |
| Later comparative evidence | `later-thessalonian-funerary-comparison` | Uses `later-comparative`, states the century gap, and ranks below contemporary or direct evidence unless later reception is requested. |

For geography/environment evidence authored as its own item, name the actual
route, site, water system, ecological zone, or boundary; record location
uncertainty; cite a map, gazetteer, survey, or excavation source; and explain
why that physical constraint matters for the linked passage. Shared membership
in a broad region is not enough.

Every evidence item requires a local `source_id`, at least one structured
Scripture relationship, an explanation of passage relevance, and an explained
confidence. Claim and source IDs must resolve inside the containing object;
geography and related-object IDs must resolve globally. Related-evidence IDs
must resolve inside the same object.

### Chronology and contamination protection

Signed years use negative values for BCE and positive values for CE; year zero
is rejected. Narrative setting and source composition are independent because
a text may describe an earlier setting. Each passage relationship labels its
chronology as `contemporary`, `near-contemporary`, `earlier-comparative`,
`later-comparative`, `diachronic`, or `unknown`.

For a passage-scoped evidence query, an item without an authored overlapping
Scripture link is excluded. That means Johannine material does not enter a
Genesis packet merely through shared creation vocabulary. Legitimate later
rabbinic, Second Temple, New Testament, or reception evidence remains eligible
only when its authored passage link identifies it as later/comparative (or
another accurate relation) and explains why it matters. Object-level guarded
relationship expansion likewise requires direct passage overlap or an explicit
cross-period/intertextual relationship.

Within eligible evidence, ranking is deterministic: query overlap, exact
passage link and weight, requested evidence dimension, source availability,
source-type quality, confidence, assertion type, explained rationale, parent relevance, and
chronological relation contribute bounded signals. Later comparisons are
retained as labeled comparisons, not silently promoted to contemporary data.

### Provenance, confidence, and disputes

`assertion_type` distinguishes `primary-evidence`, `secondary-evidence`,
`scholarly-reconstruction`, and `inference`. `primary_observation` records what
the artifact, text, or excavation actually presents; `scholarly_interpretation`
records how its significance is reconstructed. Confidence must be one of
`unrated`, `low`, `medium`, or `high` and must have a rationale. Certainty and
dispute fields provide a separate scholarly-status vocabulary, so “high
confidence that an artifact is authentic” need not imply “one uncontested
interpretation.”

`audit_evidence()` and the `evidence_audit` section of `ckl_report.py` flag
missing or unknown chronology, weak source types, high-confidence/dispute
mismatches, possible duplicate evidence, questionable temporal alignment, and
image URLs without licensing or attribution. They also flag missing source
locators, high-confidence items supported only by secondary literature,
internal-only evidence, worldview reconstructions resting on one modern
source, repeated observation/interpretation text, unsupported cross-period
links, generic legacy prose, and overbroad context applicability. These are
review signals, not automatic conclusions or destructive fixes.

## Worldview Evidence Policy

CKL may represent reconstructed ancient worldview concepts, but it does not
prescribe a worldview model as the meaning of a passage or as mandatory
theology. A worldview evidence item must:

- begin with identifiable primary textual, inscriptional, iconographic, or
  material evidence;
- keep `primary_observation`, `scholarly_interpretation`, and
  `passage_relevance` genuinely distinct;
- cite primary ancient evidence where available and use more than one modern
  scholarly voice for substantive reconstructions;
- document textual, historical, and interpretive disagreement rather than
  flattening it into a high-confidence conclusion;
- state whether evidence is contemporary, near-contemporary, earlier
  comparative, later comparative, or diachronic;
- avoid projecting Ugaritic, Mesopotamian, Second Temple, rabbinic, or later
  Christian material into a biblical passage without an authored comparison;
- avoid treating one scholar's synthesis as the canonical divine-council,
  cosmic-geography, sacred-space, kingship, purity, or heavenly-being model;
- explain exactly why the evidence helps with the linked passage without
  continuing into “therefore the passage teaches.”

For divine-assembly material in particular, author the chain as separate
records or fields: biblical textual observation, ancient comparative evidence,
historical reconstruction, major interpretations, and dispute status. Psalm
82, Deuteronomy 32, Job 1-2, Ugaritic council texts, and later witnesses must
retain their separate genres and dates.

### Archaeology, ancient sources, and image licensing

Ancient texts should normally be stored as bibliographic metadata, concise
paraphrase, and primary observation. Do not copy modern copyrighted
translations. Archaeological evidence should record artifact/site name,
discovery and present location when known, period, culture, geography,
confidence, source, and a passage-relevance explanation. Detailed catalog and
media ownership remains in the archaeology domain through stable
`external_references`.

An internet URL is not a reusable-image license. If an evidence item includes
`image_source_url`, it must also record `image_license` and
`image_attribution`; the evidence audit fails those omissions. Prefer public
domain, CC0, compatible Creative Commons, museum open-access, government, or
academic open-access material. Link-only non-free media must not be copied or
cached as CKL content.

### Contributor checklist for evidence

Before adding an item, answer all twelve questions in the record or its review
notes:

1. What exactly is the evidence: artifact, text, practice, geography, literary convention, or reconstruction?
2. Where does it come from, including artifact, manuscript, site, corpus, edition, or catalog identifier?
3. When does the artifact, event, or practice belong, and when was the textual source composed or copied?
4. Where does it belong geographically, and what part of that location is certain or disputed?
5. Which exact passage is it relevant to?
6. Why does it matter for that passage without deciding the passage's theology?
7. Is the relationship direct, contextual, comparative, contrastive, or disputed—and is it contemporary, earlier, later, or diachronic?
8. What is the primary observation, and what is the separate scholarly interpretation?
9. How strong is the evidence, and what explains the chosen confidence and certainty?
10. Where do scholars disagree about date, identification, reconstruction, or interpretation?
11. Which resolvable source supports the item, and does it include the best available locator and edition metadata?
12. Is human review required, and is AI/import provenance kept separate from human approval?

Then verify that every local source and claim ID resolves, archaeology/media is
linked through a stable external ID, any image has rights metadata, and
AI-authored material remains `in_review` with
`human_review_required: true`. Run validation, the quality report, database
build/verification, and focused retrieval tests. An accurate empty field is
preferable to unsourced “Bible trivia.”

`sources` are now stored as structured source objects with this shape:

```json
{
  "id": "gilgamesh-flood-tablet-k3375",
  "title": "The Flood Tablet: Epic of Gilgamesh, Tablet XI",
  "author": "",
  "publisher": "British Museum",
  "year": -650,
  "locator": "Museum number K.3375; Neo-Assyrian, seventh century BCE",
  "url": "https://www.britishmuseum.org/collection/object/W_K-3375",
  "source_type": "museum-collection",
  "supports": ["genesis-gilgamesh-flood-comparison"],
  "notes": "Artifact date is not treated as the origin date of the flood tradition."
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

- `context_applicability` defaults to `false`; every emitted context layer must be explicitly enabled and authored.
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

The structured evidence corpus deliberately favors depth over count. It now
includes David/Goliath weapon language and Tell es-Safi metallurgy; the Taylor
Prism and Lachish reliefs; the Cyrus Cylinder; Genesis creation and flood
comparisons; Psalm 82, Deuteronomy 32, Job, and Ugaritic divine-assembly
evidence; Egyptian brickmaking, royal titulary, and offering-practice
comparisons; the Exodus-to-Sinai itinerary and water constraints; and
Thessalonian civic, funerary, and arrival-imagery evidence. The Judges-era pass
adds the regional settlement pattern of Judges 1, the Merneptah people
reference, Iron I highland village growth and regional continuity/change,
Micah's household cult, the Danite shrine installation, Shiloh's sanctuary and
festival setting, and a bounded Bull Site comparison. The sacred-space pass
adds the tabernacle's dwelling purpose, graded access, instruction-construction
correspondence, and cloud-governed mobility, followed by bounded comparisons
with Mari M.6873, Ramesses II's Qadesh camp, Timna Site 200, and an Egyptian
processional bark shrine. The Assyrian imperial pass adds the staged reduction
and fall of Samaria, Sargon II's conquest and deportation claim, forced
resettlement policy, provincial counter-resettlement, the differentiated tribute
sequence in Kings, Jehu's Black Obelisk register, Sennacherib's Hezekiah annals,
and the Lachish royal victory display. These 48 items are chronology-controlled,
passage-linked, and source-resolvable, but AI-authored additions remain drafts
until human review.

The Babylonian and Persian pass adds the staged 597 and 587/586 BCE conquest
sequence, the Babylonian Chronicle's bounded 597 notice, Jehoiachin's palace
ration records, the Al-Yahudu diaspora archive, Ezra's multi-reign restoration
sequence, the Cyrus Cylinder's Babylonian scope and limits, Yehud stamp
administration, and the later-comparative Elephantine petition. These 56 items
are chronology-controlled, passage-linked, and source-resolvable, but
AI-authored additions remain drafts until human review.

The Second Temple institutions pass adds passage-bounded evidence for temple
leadership under Herodian and Roman power, Josephus's later account of
high-priestly appointments, the temple warning inscription, and the cautious
Caiaphas ossuary identification. A companion cluster adds synagogue reading
and instruction, the pre-70 Theodotus inscription, Ben Sira's learned-scribe
ideal, Josephus's selective descriptions of Pharisees, Sadducees, and Essenes,
and 4QMMT as evidence for legal disagreement without assigning its authors to a
named group. These 65 items are chronology-controlled, passage-linked, and
source-resolvable, but AI-authored additions remain drafts until human review.

The first-century Galilee and Judea pass adds passage-bounded evidence for
Galilean households and farming, Capernaum domestic remains, an Early Roman
Nazareth dwelling, Jewish stone-vessel production, Magdala's harbor and fishing
evidence, the Ginosar boat, Jerusalem pilgrimage and commerce, differentiated
tax systems, Josephus's census chronology, Pilate's prefectural office, Roman
execution, and Jewish burial. These 80 items are chronology-controlled,
passage-linked, and source-resolvable, but AI-authored additions remain drafts
until human review.

The Roman Corinth pass adds passage-bounded evidence for Acts 18's work,
synagogue, household, and Gallio scenes; the Delphi chronological control;
Roman colonial public space; Cenchreae and Lechaeum travel; the disputed
Erastus pavement identification; sanctuary, market, and household idol-food
settings; associations and status-ordered meals; slavery and household
hierarchy; and Isthmian athletic comparison. These 90 items are
chronology-controlled, passage-linked, and source-resolvable, but AI-authored
additions remain drafts until human review.

The Roman Ephesus pass adds passage-bounded evidence for Apollos, Prisca,
Aquila, Tyrannus, ritual specialists, and burned books; Artemis-linked craft
income; the Artemision; the theater's phase history; Asiarchs, the town clerk,
and civic assembly procedure; the harbor and Roman Asian travel network;
imperial cult and public honor; the Ephesians 1:1 destination variant; First
Timothy's narrated setting; and bounded household, slavery, association,
benefaction, and office comparisons. These 102 items are chronology-controlled,
passage-linked, and source-resolvable, but AI-authored additions remain drafts
until human review.

The Roman Philippi pass adds passage-bounded evidence for the Neapolis and Via
Egnatia route; veteran-colony foundations and the phase-controlled forum; the
riverside Sabbath prayer gathering; Lydia's trade, household, and hospitality;
the unnamed enslaved diviner's religious and economic exploitation; colonial
magistrates, lictors, punishment, custody, and citizenship; the later
traditional prison; civic honor and imperial divine honors; bounded
`politeuesthe` and `politeuma` comparisons; women benefactors and the named
coworkers Euodia and Syntyche; gift partnership across varied economic levels;
and the inability of `praetorium` or Caesar's household to settle the letter's
provenance. These 114 items are chronology-controlled, passage-linked, and
source-resolvable, but AI-authored additions remain drafts until human review.

The next focused Pauline-city expansion should prioritize Rome.
Cultural practices, historical institutions, literary conventions,
geography/environment, and worldview concepts already have controlled types;
they need source-backed, human-reviewed depth rather than generated volume.

A future AI-assisted evidence audit should concentrate on: inherited generic
or internal-only sources; exact artifact/site identification; absolute and
relative chronology; narrative-setting versus composition-date claims;
passage-link strength; claims whose confidence exceeds their dispute status;
duplicate or contradictory evidence; source quality and edition/locator
precision; geographic overreach; modern translations or images with unclear
rights; one-position worldview reconstructions; and any relevance statement
that crosses from context into a prescribed theological conclusion. Automated
findings must remain review candidates until a qualified human resolves them.

For the current CKL request path and evidence boundary, see
[`docs/architecture.md`](architecture.md#answer-flow).
