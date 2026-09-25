# CKL Typed Evidence Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add validated typed evidence targets and a non-mutating geography-candidate transaction that can bootstrap defensible entities and preserve canonical evidence identity while merging compatible provenance.

**Architecture:** `evidence_models.py` becomes the sole owner of the typed target union and its legacy-field-presence serialization behavior. `expansion.py` stages objects and evidence in memory, delegates semantic equality to a structural-fingerprint helper, and produces an auditable result without writing production CKL. The geography converter remains a source-lock-driven adapter; it emits the new shapes only after the model and transaction can preserve every required identity, anchor, temporal, and source value.

**Tech Stack:** Python 3, dataclasses, JSON Schema, pytest/unittest, existing CKL JSON/SQLite builder and source-lock tooling.

**Spec:** `docs/superpowers/specs/2026-09-24-ckl-typed-evidence-targets-design.md`

## Global Constraints

- Do not modify `framework/canonical_library/objects/**`, the source-lock queue, production Commentary artifacts, or production databases.
- Do not invoke candidate apply mode; bootstrap-bearing transactions reject `write=True`.
- Preserve the 20 existing accepted candidate payload hashes exactly; regenerate derived candidate/report artifacts only from `docs/ckl-geography-pilot-source-lock.json`.
- Legacy evidence that omitted `evidence_targets` must serialize without that field and retain its canonical payload hash; an explicitly supplied empty list remains explicit.
- Reuse existing temporal scope, sources, source IDs, Scripture links, external references, confidence, and library validation. Unknown vocabulary, unresolved identities, identity collisions, incompatible targets, and provenance conflicts fail closed.
- Existing canonical evidence identity wins over a staged structural duplicate. Multiple loaded canonical items with one structural fingerprint produce `canonical-structural-duplicate-conflict`, never an automatic merge.
- Keep the work additive: no broad migration of legacy `related_objects`, no Commentary v1.2 selection/rendering/prose behavior change, and no production entity creation.

## Review Focus

- A legacy evidence mapping without `evidence_targets` must not acquire `[]` during JSON, SQLite payload, retrieval, or dry-run round trips.
- A value target with an unknown type, vocabulary item, qualifier kind, mixed qualifier value/entity form, or incompatible relationship must be rejected before staging.
- A valid entity target or qualifier entity ID that does not resolve in the staged library must fail full-library validation.
- A staged evidence ID that sorts earlier than an equivalent loaded canonical ID must retain the loaded ID and merge both complete source locators.
- A shared source ID whose complete normalized source mapping differs must fail as `provenance-conflict`; multiple loaded canonical matches must fail as `canonical-structural-duplicate-conflict`.

## File Structure

- Modify: `framework/canonical_library/evidence_models.py` — typed target dataclasses, strict parser, compatibility registry, and presence-aware evidence serialization.
- Modify: `framework/canonical_library/schema/base.schema.json`, `framework/canonical_library/schema.py`, `framework/canonical_library/__init__.py` — JSON contract, cross-library resolution/subject checks, and public exports.
- Modify: `framework/canonical_library/evidence_retrieval.py` — add typed targets to retrieved evidence without changing ranking behavior.
- Modify: `framework/canonical_library/semantic_deduplication.py` — canonical structural fingerprints and deterministic canonical JSON merge primitives.
- Modify: `framework/canonical_library/expansion.py` — staged bootstrap validation, structural deduplication, provenance merge, survivor selection, and transaction reporting.
- Modify: `framework/canonical_library/geography_candidates.py`, `tools/ckl_geography_candidate_dry_run.py` — registry-driven source-lock conversion and detailed dry-run classification/reporting.
- Modify: `tests/canonical_library/test_evidence_architecture.py`, `tests/canonical_library/test_schema.py`, `tests/canonical_library/test_expansion.py`, `tests/canonical_library/test_geography_candidates.py`, `tests/canonical_library/test_sqlite_storage.py` — focused regressions and end-to-end dry-run checks.
- Create: `tests/canonical_library/test_typed_evidence_targets.py` — compact target-model, schema, serialization, and retrieval contract tests.
- Modify generated: `docs/ckl-geography-pilot-candidates.json`, `docs/ckl-geography-pilot-candidates.md` — regenerated dry-run output only after all validation passes.

### Task 1: Define typed target values and preserve legacy serialization

**Files:**
- Modify: `framework/canonical_library/evidence_models.py`
- Modify: `framework/canonical_library/__init__.py`
- Create: `tests/canonical_library/test_typed_evidence_targets.py`

**Interfaces:**
- Produces: `CanonicalEntityEvidenceTarget`, `CanonicalValueEvidenceTarget`, `CanonicalEvidenceTarget`, `CanonicalEvidenceQualifier`, `validate_evidence_targets(value)`, and `CanonicalEvidenceItem.evidence_targets`.
- Consumes: existing `normalize_id`, `CanonicalTemporalScope`, `EvidenceValidationError`, and canonical evidence serializers.

- [ ] **Step 1: Write failing model and legacy-wire-format tests**

```python
def test_legacy_evidence_targets_are_empty_in_memory_but_omitted_on_output() -> None:
    raw = evidence_mapping_without_targets()
    item = CanonicalEvidenceItem.from_mapping(raw)

    assert item.evidence_targets == []
    assert "evidence_targets" not in item.to_dict()
    assert canonical_json_hash(item.to_dict()) == canonical_json_hash(raw)


def test_entity_and_value_targets_have_canonical_shapes() -> None:
    item = CanonicalEvidenceItem.from_mapping(
        evidence_mapping(
            evidence_targets=[
                {"kind": "entity", "relationship": "near", "entity_id": "sychar"},
                {
                    "kind": "value",
                    "relationship": "territorial-inheritance",
                    "value_type": "entitlement",
                    "normalized_value": "none",
                    "display_value": "No inheritance among Israel",
                    "qualifiers": [
                        {"kind": "domain", "normalized_value": "territorial"},
                        {"kind": "contextual-addressee", "entity_id": "aaron"},
                    ],
                },
            ]
        )
    )

    assert [target.to_dict() for target in item.evidence_targets] == [
        {"kind": "entity", "relationship": "near", "entity_id": "sychar"},
        {
            "kind": "value",
            "relationship": "territorial-inheritance",
            "value_type": "entitlement",
            "normalized_value": "none",
            "display_value": "No inheritance among Israel",
            "qualifiers": [
                {"kind": "domain", "normalized_value": "territorial"},
                {"kind": "contextual-addressee", "entity_id": "aaron"},
            ],
        },
    ]
```

- [ ] **Step 2: Run the focused tests and confirm the expected RED failure**

Run: `.venv/bin/pytest -q tests/canonical_library/test_typed_evidence_targets.py`

Expected: FAIL because the target classes/parser and `evidence_targets` field do not yet exist.

- [ ] **Step 3: Implement the smallest strict typed-target model**

Add frozen dataclasses for entity targets, value targets, and qualifiers. Parse only the two discriminator forms; normalize IDs and normalized values with the existing canonical kebab-case rule. Enforce exactly one qualifier payload (`normalized_value` xor `entity_id`), deduplicate canonical targets/qualifiers, and hard-code the approved registry:

```python
VALUE_TARGET_REGISTRY = {
    "entitlement": {
        "values": {"none", "tithe"},
        "qualifiers": {"domain", "scope", "source", "basis", "contextual-addressee"},
    },
    "geographic-feature": {
        "values": {"field"},
        "qualifiers": {"attributed-giver", "attributed-recipient"},
    },
}
```

Extend `CanonicalEvidenceItem` with `evidence_targets` plus a private, non-dataclass-output presence marker. `from_mapping()` records whether the wire field was present; `to_dict()` serializes the normal dataclass payload but removes `evidence_targets` only when it is empty and was absent/defaulted. Export the target types and validator from `__init__.py`.

- [ ] **Step 4: Add negative and round-trip tests**

Cover invalid discriminator, unknown field, bad kebab case, invalid registry value, invalid qualifier kind, both qualifier forms, neither qualifier form, duplicate targets, explicit empty list preservation, and non-empty JSON round trip. Add a test constructing a new default `CanonicalEvidenceItem` to prove it also omits the empty wire field.

- [ ] **Step 5: Run the focused tests and confirm GREEN**

Run: `.venv/bin/pytest -q tests/canonical_library/test_typed_evidence_targets.py`

Expected: PASS.

- [ ] **Step 6: Commit the model slice**

```bash
git add framework/canonical_library/evidence_models.py framework/canonical_library/__init__.py tests/canonical_library/test_typed_evidence_targets.py
git commit -m "feat: add typed CKL evidence targets"
```

### Task 2: Enforce relationship and library compatibility

**Files:**
- Modify: `framework/canonical_library/evidence_models.py`
- Modify: `framework/canonical_library/schema/base.schema.json`
- Modify: `framework/canonical_library/schema.py`
- Modify: `tests/canonical_library/test_typed_evidence_targets.py`
- Modify: `tests/canonical_library/test_schema.py`

**Interfaces:**
- Consumes: `validate_evidence_targets`, existing object/source/claim reference validation, and `CanonicalObject.type`.
- Produces: `validate_evidence_target_compatibility(item, parent, object_index)` invoked by `validate_library` after all staged objects are known.

- [ ] **Step 1: Write failing compatibility tests**

```python
@pytest.mark.parametrize(
    ("relationship", "targets", "message"),
    [
        ("encamped-between", [entity("socoh-1", role="boundary")], "exactly two"),
        ("narrated-navigation-markers", [entity("myra", role="reached", sequence=1), entity("crete", role="passed", sequence=1)], "unique positive sequence"),
        ("territorial-inheritance", [entitlement("none", domain="economic")], "domain=territorial"),
    ],
)
def test_target_relationship_compatibility_fails_closed(
    relationship: str, targets: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(CanonicalValidationError, match=message):
        validate_library([object_with_evidence_targets(relationship, targets)])


def test_library_rejects_unresolved_target_or_qualifier_entity() -> None:
    with pytest.raises(CanonicalValidationError, match="missing-place"):
        validate_library(
            [
                object_with_evidence_targets(
                    "near",
                    [{"kind": "entity", "relationship": "near", "entity_id": "missing-place"}],
                )
            ]
        )
```

Also test valid `encamped-between`, `river-water-context`, `narrated-navigation-markers`, `ruled-by`, `located-in`, `near`, `territorial-inheritance`, and `tithe-as-inheritance` cases, including the Levites institution subject and required non-empty temporal scope.

- [ ] **Step 2: Run the targeted test files and confirm RED**

Run: `.venv/bin/pytest -q tests/canonical_library/test_typed_evidence_targets.py tests/canonical_library/test_schema.py`

Expected: FAIL because the JSON schema and library validator do not recognize or validate `evidence_targets`.

- [ ] **Step 3: Implement the schema and two-level validation**

Add JSON Schema definitions for `evidenceTarget`, `entityEvidenceTarget`, `valueEvidenceTarget`, and `evidenceQualifier`, with `additionalProperties: false` and a `oneOf` discriminator. Add `evidence_targets` to `evidenceItem.properties`, but not its `required` list.

In `evidence_models.py`, validate per-item cardinality/role/sequence rules. In `schema.py`, after the complete object index exists, resolve entity targets and qualifier entity IDs, check parent subject/object types, and enforce relationship-specific target combinations. Do not apply the new registry to legacy `related_objects`.

- [ ] **Step 4: Run the targeted tests and confirm GREEN**

Run: `.venv/bin/pytest -q tests/canonical_library/test_typed_evidence_targets.py tests/canonical_library/test_schema.py`

Expected: PASS.

- [ ] **Step 5: Commit the validation slice**

```bash
git add framework/canonical_library/evidence_models.py framework/canonical_library/schema/base.schema.json framework/canonical_library/schema.py tests/canonical_library/test_typed_evidence_targets.py tests/canonical_library/test_schema.py
git commit -m "feat: validate CKL evidence target relationships"
```

### Task 3: Carry typed targets through retrieval and SQLite payloads

**Files:**
- Modify: `framework/canonical_library/evidence_retrieval.py`
- Modify: `tests/canonical_library/test_evidence_architecture.py`
- Modify: `tests/canonical_library/test_sqlite_storage.py`

**Interfaces:**
- Produces: `RetrievedEvidenceItem.evidence_targets` as an immutable sequence of target mappings and a list form from `RetrievedEvidenceItem.to_dict()`.
- Preserves: current score, ordering, source hydration, and database schema version; serialized object `payload_json` is the authoritative SQLite preservation path.

- [ ] **Step 1: Write failing retrieval/storage regression tests**

```python
def test_retrieved_evidence_exposes_structured_targets_without_parsing_prose() -> None:
    item = library.retrieve_evidence_items("inheritance", ["levites"], scripture_references=["Numbers 18"])["levites"][0]
    assert item.evidence_targets == (
        {
            "kind": "value",
            "relationship": "territorial-inheritance",
            "value_type": "entitlement",
            "normalized_value": "none",
            "display_value": "No inheritance among Israel",
            "qualifiers": [{"kind": "domain", "normalized_value": "territorial"}],
        },
    )
    assert item.to_dict()["evidence_targets"] == list(item.evidence_targets)


def test_sqlite_payload_round_trip_preserves_absent_and_present_target_fields() -> None:
    database = build_database(root_with_legacy_and_typed_evidence(), tmp_path / "ckl.sqlite")
    stored = sqlite3.connect(database.path).execute(
        "SELECT payload_json FROM canonical_objects WHERE id = 'levites'"
    ).fetchone()[0]
    assert json.loads(stored)["evidence_items"][0]["evidence_targets"][0]["kind"] == "value"
    assert "evidence_targets" not in json.loads(stored)["evidence_items"][1]
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `.venv/bin/pytest -q tests/canonical_library/test_evidence_architecture.py tests/canonical_library/test_sqlite_storage.py`

Expected: FAIL because retrieved evidence has no `evidence_targets` field.

- [ ] **Step 3: Implement additive retrieval output**

Add the tuple field to `RetrievedEvidenceItem`, convert each target with `to_dict()` in `rank_evidence_items()`, and include it in the existing tuple-to-list conversion loop. Do not add a normalized SQL table or bump the database version: `database_builder.py` already serializes `CanonicalObject.to_dict()` into `canonical_objects.payload_json`, so rebuilding preserves both absent and emitted fields with the model's presence-aware serializer.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run: `.venv/bin/pytest -q tests/canonical_library/test_evidence_architecture.py tests/canonical_library/test_sqlite_storage.py`

Expected: PASS.

- [ ] **Step 5: Commit the retrieval slice**

```bash
git add framework/canonical_library/evidence_retrieval.py tests/canonical_library/test_evidence_architecture.py tests/canonical_library/test_sqlite_storage.py
git commit -m "feat: expose typed evidence targets in retrieval"
```

### Task 4: Implement structural fingerprints and provenance-safe survivor selection

**Files:**
- Modify: `framework/canonical_library/semantic_deduplication.py`
- Modify: `framework/canonical_library/expansion.py`
- Modify: `tests/canonical_library/test_expansion.py`

**Interfaces:**
- Produces: `evidence_structural_fingerprint(parent_id, evidence) -> str`, `CanonicalStructuralDuplicateConflict`, and a transaction result exposing `simulated_objects`, `classification`, `survivor_evidence_id`, and contributing provenance identities.
- Consumes: canonical evidence target serializer, `CanonicalSource` validation, canonical JSON serialization, and loaded-vs-staged provenance.

- [ ] **Step 1: Write failing structural-deduplication tests**

```python
def test_staged_duplicate_preserves_loaded_canonical_evidence_id_and_merges_provenance(tmp_path):
    library = library_with_evidence(
        evidence_id="z-canonical", source=_source("existing", locator="Ruth 1:1")
    )
    result = apply_candidate_queue(
        library.root,
        [candidate(evidence_id="a-staged", source=_source("new", locator="Ruth 1:2"))],
        write=False,
    )

    merged = result.simulated_objects["bethlehem"]["evidence_items"]
    assert [item["id"] for item in merged] == ["z-canonical"]
    assert merged[0]["source_ids"] == ["existing", "new"]
    assert {source["id"]: source["locator"] for source in result.simulated_objects["bethlehem"]["sources"]} == {
        "existing": "Ruth 1:1", "new": "Ruth 1:2"
    }
    assert result.decisions[0].classification == "duplicate-existing-provenance-merged"
    assert result.decisions[0].survivor_evidence_id == "z-canonical"


def test_multiple_loaded_matches_fail_closed_for_review(tmp_path):
    root = library_with_two_matching_loaded_evidence_items(tmp_path).root
    with pytest.raises(ValueError, match="canonical-structural-duplicate-conflict"):
        apply_candidate_queue(root, [], write=False)
```

Add tests for queue-order independence; no-loaded-survivor lexicographic staged selection; identical-source merge; source-ID/different-source-map `provenance-conflict`; non-provenance identity conflict; and structurally distinct evidence remaining complementary.

- [ ] **Step 2: Run the focused expansion tests and confirm RED**

Run: `.venv/bin/pytest -q tests/canonical_library/test_expansion.py`

Expected: FAIL because the current transaction appends evidence and rejects duplicates using prose-based semantic fingerprints.

- [ ] **Step 3: Implement fingerprints and canonical merge helpers**

In `semantic_deduplication.py`, derive a stable JSON fingerprint from parent ID, evidence type, normalized/sorted typed targets, and `temporal_scope.to_dict()`. Retain the current conservative prose fingerprint only for evidence without typed targets. Keep display value, prose fields, source IDs, source locators, Scripture rationale prose, and external-reference notes out of structural identity.

In `expansion.py`, group accepted typed evidence by `(target object ID, structural fingerprint)` before mutating the staged mapping. Partition each group into loaded canonical evidence and staged candidates. Enforce this precedence exactly:

```python
if len(canonical_matches) > 1:
    raise CanonicalStructuralDuplicateConflict(
        f"canonical structural duplicate: {parent_id}:{fingerprint}"
    )
if len(canonical_matches) == 1:
    survivor = canonical_matches[0]       # never compare its ID to staged IDs
else:
    survivor = min(staged_matches, key=lambda item: item["id"])
```

Validate complete `CanonicalSource` mappings by normalized source ID before merging. Merge source records, source IDs, passage links, and external references by their canonical JSON representations; sort every merged list by that representation; then validate the resulting parent/object. Return classifications and survivor IDs in `CandidateValidation`/`CandidateApplication` without weakening existing source or anchor gates.

- [ ] **Step 4: Run the focused expansion tests and confirm GREEN**

Run: `.venv/bin/pytest -q tests/canonical_library/test_expansion.py`

Expected: PASS.

- [ ] **Step 5: Commit the structural-deduplication slice**

```bash
git add framework/canonical_library/semantic_deduplication.py framework/canonical_library/expansion.py tests/canonical_library/test_expansion.py
git commit -m "feat: preserve canonical evidence identity during dedup"
```

### Task 5: Stage entity bootstraps in the all-or-nothing dry-run transaction

**Files:**
- Modify: `framework/canonical_library/expansion.py`
- Modify: `tests/canonical_library/test_expansion.py`

**Interfaces:**
- Candidate input: optional `entity_bootstraps: list[dict[str, Any]]`.
- Produces: a validated simulated object mapping and deterministic bootstrap decisions; `write=True` raises when a bootstrap is present.

- [ ] **Step 1: Write failing bootstrap transaction tests**

```python
def test_dry_run_stages_defensible_bootstrap_before_evidence_resolution(tmp_path):
    result = apply_candidate_queue(root, [candidate_with_bootstrap("socoh-1")], write=False)
    assert result.wrote is False
    assert "socoh-1" in result.simulated_objects
    assert result.changed_object_ids == ["1-samuel", "socoh-1"]


def test_bootstrap_collisions_and_write_mode_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="bootstrap.*alias.*collision"):
        apply_candidate_queue(root, [colliding_bootstrap_candidate()], write=False)
    with pytest.raises(ValueError, match="write=True.*bootstrap"):
        apply_candidate_queue(root, [candidate_with_bootstrap("socoh-1")], write=True)
```

Cover exact duplicate coalescing, different mapping/same ID conflict, normalized title/alias/type/source-identity collision, unresolved target before bootstrap, complete-library/manifest validation, and source/anchor/occurrence gate failures.

- [ ] **Step 2: Run the focused expansion tests and confirm RED**

Run: `.venv/bin/pytest -q tests/canonical_library/test_expansion.py`

Expected: FAIL because the current transaction accepts only children for already-loaded targets and can write any accepted queue.

- [ ] **Step 3: Implement isolated bootstrap staging**

Collect and normalize all bootstrap mappings before evidence validation; validate each with the normal object validator; compare against loaded and already-staged IDs, titles, aliases, types, and source identity. Build the simulated object index first, then resolve evidence targets/qualifiers against it and run the existing full `validate_library()` with a simulated manifest count. Keep paths and write operations unresolved for new objects and reject `write=True` immediately when bootstraps are present.

- [ ] **Step 4: Run the focused expansion tests and confirm GREEN**

Run: `.venv/bin/pytest -q tests/canonical_library/test_expansion.py`

Expected: PASS.

- [ ] **Step 5: Commit the bootstrap slice**

```bash
git add framework/canonical_library/expansion.py tests/canonical_library/test_expansion.py
git commit -m "feat: stage CKL entity bootstraps in dry runs"
```

### Task 6: Convert the locked geography queue through explicit target registries

**Files:**
- Modify: `framework/canonical_library/geography_candidates.py`
- Modify: `tests/canonical_library/test_geography_candidates.py`
- Modify: `tests/canonical_library/test_source_locks.py`

**Interfaces:**
- Consumes: unchanged `docs/ckl-geography-pilot-source-lock.json`, loaded CKL, and staged bootstrap support.
- Produces: deterministic candidate records with `entity_bootstraps`, typed `evidence_targets`, retained lock provenance, and explicit rejection reasons.

- [ ] **Step 1: Write failing conversion/hash tests**

```python
def test_converter_emits_typed_targets_and_bootstraps_only_for_registered_families(result):
    sychar = record(result, "john-4-sychar-well-near-jacob-field")
    assert sychar["candidate_payload"]["evidence_item"]["evidence_targets"] == [expected_field_target]
    assert {item["id"] for item in sychar["candidate_payload"]["entity_bootstraps"]} == {"sychar"}


def test_original_twenty_payload_hashes_are_unchanged(result):
    assert accepted_payload_hashes(result) == json.loads(FIXTURE_PATH.read_text())
```

Also assert malformed maritime clauses, ambiguous textual-field grammar, missing OpenBible occurrence records, unsupported relationships, invalid bootstrap identity evidence, and unregistered vocabulary remain rejected rather than coerced.

- [ ] **Step 2: Run converter/source-lock tests and confirm RED**

Run: `.venv/bin/pytest -q tests/canonical_library/test_geography_candidates.py tests/canonical_library/test_source_locks.py`

Expected: FAIL because the current converter only emits legacy `related_objects` and rejects bootstrap/value-required records.

- [ ] **Step 3: Implement registry-based conversion with no source-lock mutation**

Replace readiness special-casing with a relationship/target-family registry. Implement only the specified grammar families: named entity pairs, maritime sequence, constrained textual field, territorial entitlement, economic entitlement, person, and territory bootstrap. Consume each locked identity/name exactly once, retain every lock/source/anchor/temporal value verbatim, and use exact imported OpenBible record IDs for place bootstraps. Preserve the legacy conversion branch for the original 20 accepted payloads byte-semantically.

- [ ] **Step 4: Run converter/source-lock tests and confirm GREEN**

Run: `.venv/bin/pytest -q tests/canonical_library/test_geography_candidates.py tests/canonical_library/test_source_locks.py`

Expected: PASS.

- [ ] **Step 5: Commit the converter slice**

```bash
git add framework/canonical_library/geography_candidates.py tests/canonical_library/test_geography_candidates.py tests/canonical_library/test_source_locks.py
git commit -m "feat: convert locked geography evidence targets"
```

### Task 7: Produce auditable dry-run output and complete verification

**Files:**
- Modify: `tools/ckl_geography_candidate_dry_run.py`
- Modify: `tests/canonical_library/test_geography_candidates.py`
- Modify generated: `docs/ckl-geography-pilot-candidates.json`
- Modify generated: `docs/ckl-geography-pilot-candidates.md`

**Interfaces:**
- Produces: report rows that distinguish new, complementary, duplicate pilot, duplicate existing, provenance-merged duplicate pilot, provenance-merged duplicate existing, conflict, and canonical structural duplicate conflict.
- Preserves: no-write dry-run behavior and zero production CKL/Commentary artifact changes.

- [ ] **Step 1: Write failing report and non-mutation tests**

```python
def test_dry_run_reports_canonical_survivor_and_never_writes_production(tmp_path):
    root = library_with_evidence(evidence_id="z-canonical", source=_source("existing", "Ruth 1:1")).root
    before = snapshot_ckl_object_bytes(root)
    dry_run = run(source_lock_path=duplicate_source_lock(tmp_path), ckl_root=root)
    duplicate = record(dry_run["queue"], "fixture-existing-duplicate")

    assert duplicate["dedup_result"] == "duplicate-existing-provenance-merged"
    assert duplicate["survivor_evidence_id"] == "z-canonical"
    assert snapshot_ckl_object_bytes(root) == before
    assert dry_run["report"]["dry_run"]["wrote"] is False
```

- [ ] **Step 2: Run the dry-run test file and confirm RED**

Run: `.venv/bin/pytest -q tests/canonical_library/test_geography_candidates.py`

Expected: FAIL because the report currently derives dedup status from a prose `semantic-duplicate` reason and cannot expose survivor metadata.

- [ ] **Step 3: Implement report classification and regenerate only derived artifacts**

Map structured transaction classifications and conflicts into `_apply_decisions()` and `_report()`; include survivor ID plus contributing source/candidate identities for merged duplicates. Retain all rejected records and report full-library validation, staged manifest/object counts, changed references, and zero writes. Run the dry-run tool against the locked source file to rewrite only its generated JSON/Markdown outputs; do not edit source locks or objects by hand.

- [ ] **Step 4: Run focused end-to-end checks and inspect generated diffs**

Run:

```bash
.venv/bin/pytest -q tests/canonical_library/test_typed_evidence_targets.py tests/canonical_library/test_schema.py tests/canonical_library/test_evidence_architecture.py tests/canonical_library/test_sqlite_storage.py tests/canonical_library/test_expansion.py tests/canonical_library/test_geography_candidates.py tests/canonical_library/test_source_locks.py
.venv/bin/python tools/ckl_geography_candidate_dry_run.py
git diff --check
git diff -- framework/canonical_library/objects docs/ckl-geography-pilot-source-lock.json
git status --short framework/canonical_library/objects docs/ckl-geography-pilot-source-lock.json
```

Expected: all focused tests pass; generated candidates/report reflect the complete classification; the final diff is whitespace-clean and the final `git status` command prints no object or source-lock changes.

- [ ] **Step 5: Run the repository suite before completion**

Run: `.venv/bin/pytest -q`

Expected: PASS. If any test fails, record its exact name and output, fix it within the responsible task, and rerun the full suite.

- [ ] **Step 6: Commit the dry-run/report slice**

```bash
git add tools/ckl_geography_candidate_dry_run.py tests/canonical_library/test_geography_candidates.py docs/ckl-geography-pilot-candidates.json docs/ckl-geography-pilot-candidates.md
git commit -m "feat: report typed geography dry-run decisions"
```

## Plan Self-Review

- Spec coverage: Tasks 1–3 cover the union, strict schema, legacy payload stability, library resolution, retrieval, and SQLite payload persistence. Tasks 4–5 cover structural identity, canonical survivor precedence, provenance-safe merging, conflicts, bootstrap staging, and non-write boundaries. Tasks 6–7 cover locked conversion, 20-payload stability, audit output, and full verification.
- Placeholder scan: complete; no open placeholders, implicit error handling, or cross-task-only interfaces remain.
- Type consistency: `CanonicalEvidenceTarget` is the model collection; mappings are emitted only at serializer/retrieval/transaction boundaries; transaction reports expose `classification` and `survivor_evidence_id` consistently.
- Review focus: every listed risk is assigned to Tasks 1–4 and verified again in the end-to-end dry-run task.
