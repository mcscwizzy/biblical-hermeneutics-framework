# CKL Typed Evidence Targets and Transactional Entity Bootstrap Design

## Goal

Add the smallest reusable CKL capability that can represent verified evidence
whose target is either a canonical entity or a structured non-entity value,
while preserving relationship semantics, provenance, temporal scope, and
deterministic deduplication. Extend the geography candidate transaction so it
can stage independently defensible entity bootstraps for validation without
mutating production CKL.

The design is additive. Existing canonical JSON remains valid, the existing 20
accepted geography-pilot candidate payloads remain byte-semantically identical,
legacy evidence payloads round-trip without introducing empty target fields, and
Commentary v1.2 synthesis behavior does not change.

## Binding constraints

- Do not modify `framework/canonical_library/objects/**`, the authoritative
  source-lock queue, production Commentary artifacts, or production databases.
- Do not run candidate apply mode.
- Do not weaken source, Scripture-anchor, temporal, referential, leakage, or
  full-library validation.
- Do not encode a structured target only in `description`, `display_value`,
  `notes`, or another opaque prose field.
- Do not create canonical entities for terrain, direction, physical setting,
  sequence roles, entitlements, or unnamed textual features.
- Reuse `CanonicalTemporalScope`, evidence confidence, evidence source IDs,
  Scripture links, and external references. Do not create parallel temporal or
  provenance models.
- Preserve the current 20 accepted `candidate_payload` hashes exactly when the
  complete queue is regenerated.
- Preserve legacy `CanonicalEvidenceItem` canonical payloads exactly across a
  mapping-to-model-to-mapping round trip. In particular, deserializing an item
  which lacks `evidence_targets` must not add `"evidence_targets": []` or
  otherwise change its canonical JSON/hash when it is serialized again.
- Generate every new result from
  `docs/ckl-geography-pilot-source-lock.json`; do not patch generated candidate
  records by source-lock ID.
- A safe final result may retain one or more rejections. Acceptance count is not
  a success criterion.

## Diagnostic classification

| Source-lock ID | Primary classification | Entity/value decision |
|---|---|---|
| `1samuel-17-socoh-azekah-encampment` | `ENTITY_BOOTSTRAP_REQUIRED` | Socoh 1 and Azekah are canonical place entities. `encamped-between` remains relationship data. |
| `2kings-5-damascus-river-comparison` | `ENTITY_BOOTSTRAP_REQUIRED` | Abana and Pharpar are canonical place entities with river identity evidence. The comparison role remains relationship data. |
| `acts-27-sidon-crete-maritime-itinerary` | `ENTITY_BOOTSTRAP_REQUIRED` | The named locations are entities. Intended, reached, passed, nearby, and ordinal position are typed relationship metadata, never entities. |
| `john-4-sychar-well-near-jacob-field` | `TYPED_VALUE_REQUIRED` | Sychar is a canonical place entity; the unnamed field is a typed geographic-feature value with Jacob/Joseph entity qualifiers. |
| `matthew-2-archelaus-judea-administration` | `ENTITY_BOOTSTRAP_REQUIRED` | Archelaus is a canonical person entity. |
| `numbers-18-levites-no-territorial-inheritance` | `TYPED_VALUE_REQUIRED` | The negative territorial entitlement is a typed value, not a territory entity. |
| `numbers-18-levites-tithe-as-inheritance` | `TYPED_VALUE_REQUIRED` | The tithe entitlement is a typed value, not an economic entity. |
| `ruth-1-bethlehem-judah-territory` | `ENTITY_BOOTSTRAP_REQUIRED` | Judah territory is a canonical place entity distinct from persons, tribes, or an opaque label. |

No blocked record is currently classified as `EXISTING_SCHEMA_MISUSE` or
`CLAIM_SHOULD_REMAIN_BLOCKED`. Conversion must nevertheless leave any record
blocked if its grammar, identity, collision, relationship compatibility, or
provenance cannot be proven deterministically.

## Unified evidence-target model

`CanonicalEvidenceItem` gains one optional field:

```python
evidence_targets: list[CanonicalEvidenceTarget] = field(default_factory=list)
```

`CanonicalEvidenceTarget` is a discriminated union. It does not replace legacy
`related_objects`, `related_evidence`, or `geography_ids`; existing records need
no migration. New candidate families use `evidence_targets` when target
semantics matter.

### Legacy-field serialization invariant

`evidence_targets` has distinct in-memory and wire semantics. In memory, an
absent legacy field is represented as an empty target collection so consumers
can use it without a null check. Its *field-presence state* is retained as
non-canonical serializer state; it is not an additional JSON field and is not
part of structural identity.

`CanonicalEvidenceItem.to_dict()` emits `evidence_targets` exactly under these
rules:

- An item deserialized from a mapping that omitted the field omits it again,
  even though its in-memory collection is empty.
- An item deserialized from a mapping that explicitly contained
  `"evidence_targets": []` emits that explicit empty array again.
- A non-empty target collection always emits the field.
- A newly constructed item whose targets use the default empty collection omits
  the field; a caller that intentionally needs an explicit empty array must
  construct from, or otherwise mark, an explicit empty field.

Thus an absent legacy field is never materialized solely by validation,
retrieval, database serialization, or a no-op candidate transaction. This is a
canonical-payload compatibility guarantee, not merely an API convenience. The
presence marker must remain private to the model/serializer and must not appear
in JSON, SQLite payload JSON, fingerprints, or retrieval output.

### Entity target

```json
{
  "kind": "entity",
  "relationship": "narrated-navigation-markers",
  "entity_id": "myra",
  "role": "reached",
  "sequence": 3
}
```

Required fields are `kind`, `relationship`, and `entity_id`. `role` and
`sequence` are optional generally and required only by compatibility rules.
Entity targets must resolve to a canonical object during full-library
validation.

### Value target

```json
{
  "kind": "value",
  "relationship": "territorial-inheritance",
  "value_type": "entitlement",
  "normalized_value": "none",
  "display_value": "No inheritance among Israel",
  "qualifiers": [
    {"kind": "domain", "normalized_value": "territorial"},
    {"kind": "scope", "normalized_value": "among-israel"},
    {"kind": "contextual-addressee", "entity_id": "aaron"}
  ]
}
```

Required fields are `kind`, `relationship`, `value_type`, `normalized_value`,
`display_value`, and `qualifiers`. A qualifier contains `kind` plus exactly one
of `normalized_value` or `entity_id`. Normalized strings use canonical
kebab-case; display text is presentation only and is excluded from structural
identity.

The initial value-type registry is deliberately narrow:

- `entitlement`: current normalized values are `none` and `tithe`; allowed
  qualifier kinds are `domain`, `scope`, `source`, `basis`, and
  `contextual-addressee`.
- `geographic-feature`: current normalized value is `field`; allowed qualifier
  kinds are `attributed-giver` and `attributed-recipient`.

Adding a value type, normalized vocabulary item, or qualifier kind requires an
explicit registry change and tests. Arbitrary dictionaries and unknown value
types fail closed.

Per-target temporal scope, confidence, sources, and locators are intentionally
absent. Those properties belong to the containing `CanonicalEvidenceItem`,
which already validates and serializes them.

## Relationship compatibility

Compatibility is explicit for every relationship emitted by the new converter.
The validator examines the complete set of targets for one evidence item.

| Relationship | Allowed target | Additional constraints |
|---|---|---|
| `encamped-between` | entity | Exactly two targets; role `boundary`; no sequence |
| `river-water-context` | entity | Exactly two targets; role `compared-river`; no sequence |
| `narrated-navigation-markers` | entity | Roles limited to `intended-destination`, `reached`, `passed`, `nearby`; every target has a unique positive sequence |
| `ruled-by` | entity | Exactly one person target; no role or sequence |
| `located-in` | entity | Exactly one place target; no role or sequence |
| `near` | entity or `geographic-feature` value | Exactly one target; no sequence |
| `territorial-inheritance` | `entitlement` value | Exactly one value; `domain=territorial`; non-empty temporal scope required |
| `tithe-as-inheritance` | `entitlement` value | Exactly one value; `domain=economic`; non-empty temporal scope required |

Library-level validation also checks subject/target compatibility using the
parent canonical object type. A place may be `located-in` another place; a
place may be `ruled-by` a person; the Levites institution may carry the two
typed entitlement relationships. This replaces the current Numbers-specific
exception that infers negation from prose in `related_objects.notes`.

Relationships not registered for unified evidence targets are rejected. This
does not retroactively constrain legacy `related_objects` records.

## Conservative entity bootstrap

Candidate payloads may include an `entity_bootstraps` list containing complete
canonical-object mappings. The expansion transaction aggregates all requested
bootstraps before validating evidence, resolves identical duplicates, and
rejects ID, title, alias, type, or source-identity collisions.

A bootstrap is independently defensible only when all of these conditions hold:

1. The source lock directly names or designates the entity; descriptive values
   and narrative roles are ineligible.
2. At least one substantive locked Scripture source overlaps the entity's
   Scripture occurrence anchor.
3. A place using OpenBible identity has an exact imported record ID from the
   lock, and an `entity-identification-and-occurrence` lock must overlap the
   passage anchor in that imported record.
4. The stable canonical ID derives from the exact OpenBible atlas slug or from
   an unambiguous typed canonical label, never from a source-lock ID.
5. The canonical name, entity type, aliases, confidence, sources, occurrence
   anchors, identity locator, and source-lock provenance are present.
6. The entity does not already resolve by canonical ID, normalized title, or
   alias. Existing entities are reused.
7. The complete staged library passes normal object, filename/category,
   reference, alias-collision, and manifest validation.

The proposed stage contains fourteen new entities if every gate passes:

- Places: `socoh-1`, `azekah`, `abana`, `pharpar`, `italy`, `myra`, `cyprus`,
  `cnidus`, `crete`, `fair-havens`, `lasea`, `sychar`, and `judah-territory`.
- Person: `archelaus`.

Sidon, Jacob, Joseph, Aaron, Bethlehem, Judea, and the Levites resolve to
existing objects and are not bootstrapped. The count is diagnostic rather than
normative: any collision or insufficient identity evidence removes the affected
entity and leaves its claim rejected.

Each staged object is `draft`, `unreviewed`, human-review-required, and carries
an identity evidence item. That evidence item retains the source-lock ID,
Scripture anchors, copied CKL Scripture source record, temporal scope,
confidence, exact locator, and OpenBible external reference where applicable.
No coordinates, territorial borders, hydrology, political history, or modern
site assertions are inferred from identity-only data.

Bootstrap staging participates in the same all-or-nothing simulated transaction
as child evidence. In this task, `write=False` is mandatory. Calling the
transaction with `write=True` while any bootstrap is present fails closed; a
later production-apply task must separately authorize and implement the
multi-file/manifest write boundary.

## Deterministic source-lock conversion

The authoritative source-lock file remains byte-for-byte unchanged. Conversion
uses a registry keyed by target type and relationship family, never by
source-lock ID.

- Named entity pairs resolve exact OpenBible records and emit entity targets
  with relationship roles.
- `maritime-narrative-sequence` parses its semicolon-delimited role clauses,
  resolves every name against the locked OpenBible records or existing CKL,
  and requires each record and name to be consumed exactly once. Roles and
  sequence positions are normalized data.
- `textual-field` accepts the constrained “field [giver] gave to [recipient]”
  grammar, resolves giver and recipient entities, and emits one
  `geographic-feature` value. Any unmatched or ambiguous grammar remains
  rejected.
- `territorial-entitlement` emits `entitlement:none` with territorial, scope,
  and contextual-addressee qualifiers only when its constrained source-lock
  grammar matches.
- `economic-entitlement` emits `entitlement:tithe` with economic, source, and
  service-basis qualifiers only when its constrained grammar matches.
- New person and territory labels bootstrap only through the independent entity
  gate above.

The current conversion branch for the original 20 accepted candidates is not
rewritten. A regression fixture stores their existing canonical JSON hashes and
requires all 20 payloads to match exactly after regeneration.

## Validation and serialization

Validation occurs at four layers:

1. `evidence_models.py` validates discriminators, required/forbidden fields,
   controlled vocabularies, qualifier shape, normalized forms, cardinality,
   roles, and sequence positions.
2. The base JSON schema describes the same discriminated union and rejects
   unknown fields.
3. Library validation resolves entity targets and qualifier entity IDs and
   checks target object types.
4. Expansion validation checks parent-subject compatibility, temporal
   requirements, source records, locators, anchors, leakage, and the complete
   staged library.

`CanonicalEvidenceItem.from_mapping()` accepts an absent `evidence_targets`
field as an empty in-memory collection while retaining its absence for output.
`to_dict()` follows the legacy-field serialization invariant above and preserves
every emitted target and qualifier. Tests perform mapping-to-model-to-mapping
and JSON serialization round trips, including temporal scope and source
provenance on the containing evidence item.

Canonical object payload JSON in generated SQLite databases retains the new
field when it is emitted, without a corpus migration; it does not materialize
the field for legacy absent-field items. `RetrievedEvidenceItem` exposes
structured targets additively so later EvidenceBundle work can consume them
without parsing prose. This task does not make Commentary v1.2 select, render,
or synthesize those targets and does not change current prose behavior.

## Structural deduplication

Evidence with unified targets receives a structural fingerprint containing:

- parent object ID;
- evidence type;
- sorted entity targets by relationship, entity ID, role, and sequence;
- sorted value targets by relationship, value type, normalized value, and
  normalized qualifiers;
- canonical temporal scope.

`display_value`, descriptions, notes, and locator prose do not determine
identity. Legacy evidence without unified targets retains the existing
conservative text fingerprint.

Consequently, two `physical-setting=hill-country` records with the same scope
can deduplicate, while `physical-setting=hill-country` and
`elevation-context=elevated` remain complementary. The new algorithm must
prefer false negatives to collapsing semantically distinct evidence.

### Provenance-preserving structural deduplication

A structural fingerprint identifies an equivalent semantic claim; it is not a
provenance-record identity. When two unified-target evidence records (whether
already staged or newly converted) have the same structural fingerprint, the
transaction must first determine whether their provenance is compatible. It
must never discard an independently useful source, locator, Scripture link, or
external reference merely because the semantic claim is equivalent.

For compatible records, the transaction produces one deterministic surviving
evidence item and merges provenance into the existing CKL representation. The
survivor rule preserves production referential stability:

- If exactly one structurally equivalent evidence item is already present in
  the loaded canonical CKL, that existing evidence ID is always the survivor.
  A staged candidate with an earlier lexicographic ID must never replace it.
- Compatible provenance from every structurally equivalent staged candidate is
  merged into that existing evidence item.
- Only when no structurally equivalent canonical item exists may the
  transaction choose among structurally equivalent staged candidates. In that
  case it selects the lexicographically smallest canonical evidence ID as the
  survivor.
- If multiple existing canonical evidence items share a structural fingerprint,
  the transaction must report a `canonical-structural-duplicate-conflict` and
  fail closed for human review. It must not collapse, select among, or merge
  those existing items or any staged candidate into them. The existing dedup
  model supplies no safer explicit resolution rule.

An equal-ID collision is resolved only if all non-provenance canonical fields
are identical; otherwise it is a conflict. It then:

- merge parent `sources` by source ID, preserving every distinct complete
  `CanonicalSource` mapping (and therefore each source locator);
- merge the survivor's `source_ids`, `scripture_references`, and
  `external_references` as de-duplicated canonical collections; and
- order every merged collection by its canonical serialized representation so
  the same input set produces the same payload irrespective of queue order.

The merged evidence item must cite every merged source ID. Its parent must
contain the corresponding complete source records, including their locators;
the merged Scripture links and external references remain independently
inspectable. The transaction report labels a newly converted merge as
`duplicate-pilot-provenance-merged` and a merge into one loaded canonical
survivor as `duplicate-existing-provenance-merged`. Each merge report includes
the retained survivor evidence ID and all contributing candidate/source
identities. This report is audit material only; the retained canonical source
records and evidence associations are the durable provenance representation.

If two candidates reuse a source ID with non-identical normalized
`CanonicalSource` mappings, or any provenance reference cannot be validated or
merged without overwriting a distinct value, they are not compatible duplicates.
The transaction fails that candidate as `provenance-conflict` (with both
provenance mappings in the report) rather than choosing one locator or source
definition. Semantic equality never authorizes provenance loss. Non-provenance
prose may be selected only after this merge succeeds and is not treated as a
substitute for a source record.

## Transaction and dry-run reporting

The transaction builds a fully in-memory simulated library containing existing
objects, staged entity bootstraps, staged evidence, merged source records, and a
simulated manifest with updated object/category counts. It then runs normal
full-library validation and computes changed references and Commentary v1.2
rebuild dependencies.

The report distinguishes:

- existing objects that would change;
- new entities that would be created;
- previously accepted and hash-identical;
- previously blocked and now representable;
- still blocked;
- newly rejected;
- duplicate existing, duplicate pilot, provenance-merged duplicate existing,
  provenance-merged duplicate pilot, complementary, and conflicting;
- direct/dependent anchors and chapters;
- production files and Commentary artifacts modified, which must both be zero.

The dry-run command snapshots production CKL inputs before execution and proves
they are byte-identical afterward. It never invokes apply mode.

## Test strategy

Implementation follows test-driven development.

1. Schema/model tests first demonstrate that valid entity and value targets do
   not yet deserialize and that malformed discriminators, free-form values,
   invalid qualifiers, incompatible roles, duplicate sequences, and unresolved
   entity IDs fail. A legacy evidence fixture with no `evidence_targets` must
   round-trip mapping-to-model-to-mapping and through canonical JSON with no
   added field and an identical payload hash; a fixture with an explicit empty
   array must retain that explicit array.
2. Transaction tests first demonstrate that a defensible bootstrap cannot yet
   be staged, then cover collision detection, duplicate bootstrap coalescing,
   simulated manifest counts, full-library validation, and byte-for-byte
   non-mutation.
3. Converter tests cover each target family through the unchanged source-lock
   queue, including malformed/ambiguous grammar failures and OpenBible
   occurrence checks.
4. A fixed hash map proves all original 20 candidate payloads are unchanged.
5. Complete regeneration classifies all 28 eligible records and reports every
   transition. No assertion requires 28 acceptances.
6. The real dry-run transaction validates changed objects, the simulated full
   library, structural deduplication, leakage, temporal preservation, source
   locators, changed references, and Commentary v1.2 rebuild previews without
   writes. A structural-deduplication regression fixture supplies two
   source-backed unified-target evidence candidates with identical targets and
   temporal scope but different valid source IDs and locators. It must produce
   one semantic survivor whose `source_ids` and parent source records retain
   both trails, and whose report records the provenance merge. A second
   regression fixture loads one canonical unified-target evidence item and
   stages a structurally equivalent candidate whose evidence ID sorts earlier
   and whose valid source ID and locator are new. It must retain the loaded
   canonical evidence ID, merge both valid source/locator trails into that
   item, omit the staged candidate ID from the resulting evidence collection,
   and report `duplicate-existing-provenance-merged` with the canonical survivor
   ID. A fixture with multiple loaded canonical items sharing one structural
   fingerprint must fail closed with
   `canonical-structural-duplicate-conflict`, without choosing a survivor. A
   same-source-ID / different-normalized-source fixture must fail as
   `provenance-conflict`, never silently select one locator.
7. The focused schema, expansion, source-lock, converter, retrieval, database,
   and Commentary compatibility tests run before the complete repository test
   suite.

## Out of scope

- Production CKL apply or entity-file creation.
- Editing or re-certifying the authoritative source-lock queue.
- Rewriting the original 20 accepted candidates into the new target model.
- Broad conversion of existing `related_objects` records.
- A first-class claim graph or corpus-wide schema migration.
- Commentary v1.2 selection, rendering, synthesis, or prose changes.
- New geographic, historical, political, or hydrological assertions beyond the
  locked evidence.
