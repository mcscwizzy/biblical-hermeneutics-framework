# Canonical Knowledge Library

The Canonical Knowledge Library (CKL) is a version-controlled store of curated biblical knowledge that lives alongside, but separate from, the LLM. Its job is to return structured facts first so the model can act as a narrator and synthesizer rather than the primary source of biblical information.

## Purpose

CKL stores canonical facts, retrieval metadata, and future scholarship in a deterministic format. The current phase deliberately stops at the retrieval foundation: it does not infer theology, generate explanations, or call an LLM.

## Architectural Role

The long-term flow is:

1. User question
2. Canonical Knowledge Retrieval
3. Hermeneutical Framework
4. Prompt Context Builder
5. LLM
6. Final response

CKL supplies the curated object layer. The hermeneutical framework decides how those objects should be interpreted. The LLM then explains and synthesizes the already-retrieved material.

## Directory Structure

The CKL lives under `framework/canonical_library/` and is intentionally self-contained.

- `schema.py` defines the canonical object dataclass and validation rules.
- `loader.py` discovers JSON files, validates them, and builds in-memory indexes.
- `normalization.py` provides deterministic text and ID normalization.
- `retrieval.py` defines exact and future retrieval interfaces.
- `context_builder.py` assembles structured prompt context from retrieved objects.
- `public_cache.py` holds a placeholder interface for future approved-answer reuse.
- `manifest.json` records the library version and inventory counts.
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

The object `type` field stays singular even when the folder name is plural.

## Object Schema

Every canonical object uses the same base schema.

| Field | Type | Current phase | Intended purpose |
| --- | --- | --- | --- |
| `id` | string | populated | Canonical lowercase kebab-case identifier. |
| `type` | string | populated | Supported category such as `person` or `place`. |
| `title` | string | populated | Human-readable display name. |
| `aliases` | array of strings | populated | Retrieval phrases and alternate names. |
| `summary` | string | empty | Short curated summary in later phases. |
| `historical_context` | string | empty | Historical background when scholarship is added. |
| `ancient_near_east_context` | string | empty | Ancient Near East comparison and setting. |
| `literary_context` | string | empty | Literary observations and genre framing. |
| `covenantal_significance` | string | empty | How the object relates to covenant themes. |
| `intertextuality` | array of strings | empty | Cross-book and canonical links. |
| `timeline` | array of strings | empty | Ordered historical or canonical timeline points. |
| `maps` | array of strings | empty | Geographic references and map anchors. |
| `archaeology` | array of strings | empty | Archaeological references and artifacts. |
| `hebrew_words` | array of strings | empty | Hebrew word-study anchors. |
| `greek_words` | array of strings | empty | Greek word-study anchors. |
| `related_people` | array of strings | empty | Related canonical people. |
| `related_places` | array of strings | empty | Related canonical places. |
| `related_events` | array of strings | empty | Related canonical events. |
| `cross_references` | array of strings | empty | Internal reference pointers for later use. |
| `new_testament_connections` | array of strings | empty | NT connection pointers for later use. |
| `interpretive_notes` | array of strings | empty | Future interpreter notes and cautions. |
| `common_questions` | array of strings | empty | Future question prompts and FAQs. |
| `sources` | array of strings | empty | Future source citations and bibliography. |
| `importance` | integer | zero | Deterministic ranking hint for retrieval. |
| `framework_version` | string | `1.0` | CKL framework version gate. |
| `object_version` | string | `1` | Per-object schema version. |

## Placeholder Rules

The current inventory is intentionally thin. Each placeholder object contains:

- `id`
- `type`
- `title`
- `aliases`
- `importance`
- `framework_version`
- `object_version`

All other string fields are empty strings, and all collection fields are empty arrays. That means the library can be tested, indexed, and queried without pretending scholarship exists where it does not.

## Retrieval Flow

The deterministic retrieval path is:

1. Normalize the incoming question.
2. Try exact ID lookup.
3. Try exact alias lookup.
4. Try exact title lookup.
5. Fall back to keyword matching.
6. Package the results into structured context.
7. Hand that context to the downstream prompt builder and, later, to the LLM.

This keeps lookups predictable. For example, `shechem` can be retrieved without the caller knowing that it lives in the places category.

## Token Reduction

CKL reduces prompt size by retrieving only the objects that matter for a question instead of asking the LLM to reconstruct broad biblical knowledge on every turn. The result is less prompt bloat, less duplication, and better use of limited context windows.

## Smaller Local Models

Smaller models usually improve when they are given high-quality structure instead of raw open-ended prompts. CKL is designed to provide that structure so a compact local model can answer from targeted canonical data rather than improvise from memory.

## Future Semantic Search

The retrieval layer already exposes `retrieve_semantic()` and `retrieve_hybrid()` as explicit future hooks. They currently raise `NotImplementedError`, which keeps the contract honest while leaving room for a future embedding index or other semantic retrieval engine.

## Future Public Cache

`public_cache.py` defines the shape of a future approved-answer cache. The intended workflow is normalized-question lookup, approved answer storage, quality scoring, usage counting, and review status tracking. Nothing is persisted yet.

## Versioning

Three version fields keep the CKL stable:

- `framework_version` identifies the CKL framework line.
- `schema_version` identifies the manifest/schema contract.
- `object_version` identifies the object payload shape.

The loader validates these values so old or incompatible inventory files fail fast.

## Adding New Objects

Safe contributor workflow:

1. Create a new JSON file under the correct folder in `framework/canonical_library/objects/`.
2. Use a lowercase kebab-case `id` that matches the filename.
3. Add retrieval aliases, but keep them as phrases, not answers.
4. Validate the file with the CKL schema and tests.
5. Update or regenerate `manifest.json`.
6. Run the CKL test suite.

## Populating Scholarship Later

Future scholarship must be curated, sourced, and reviewed before it is written into the CKL. Interpretive rules and canonical facts should remain separate so that the hermeneutical framework can guide interpretation without collapsing into the knowledge store itself.
