# NE-11B reconciliation: Psalm 110 and Acts 2

## Decision

The active NE-9C route already provides navigation between Acts 2:22–36 and Psalm 110:1–7. The held candidate `psalm-110-acts-2-enthronement` would overlap that destination and has no materially distinct evidence attached to its exact pair. Keep it held; do not add a second bridge or change either registry in NE-11B.

This is a reconciliation decision, not a new passage-relationship approval. The held candidate remains unchanged.

## Exact active curation identities

The relevant active NE-9C decisions are in `framework/canonical_library/curations/narrative-explorer/ne9c/wave-legacy/batch-001.json`:

1. `ckl:messiah-theme` → `ckl:resurrection-theme`, classification `later_canonical_reception`, applicable passage `Acts 2:22-36`, supporting passages `Psalm 16:8-11`, `Psalm 110:1-7`, and `Acts 2:22-36`. Supporting records: `messiah-theme#source:luke-24`, `messiah-theme#source:psalm-110`, and `resurrection-theme#source:1-corinthians-15`.
2. The separately authored reciprocal decision `ckl:resurrection-theme` → `ckl:messiah-theme`, also classified `later_canonical_reception`, with the same applicable passage and supporting passage set. Its supporting-record order is `resurrection-theme#source:1-corinthians-15`, `messiah-theme#source:luke-24`, and `messiah-theme#source:psalm-110`.

The current Narrative Explorer projection from Acts 2:22–36 includes Psalm 110:1–7 as a destination. It emits two authored route rows because both theme directions are separately represented; their route identities are:

- `authored:connection:59c1b3b951cc53e00cec5a2037b65b99ad0d5991261a8aa4de75803d16ed6dd4:Psalm 110:1-7`
- `authored:connection:f1c643292a4efd904e36b0ee6609e76f83fbb49c1728089fff8aa2625ad7fefc:Psalm 110:1-7`

The route is broad at the Psalm endpoint, but it includes Psalm 110:1. Acts 2:34–35 quotes Psalm 110:1 specifically, while Acts 2:22–36 also gives the broader resurrection-and-exaltation argument. The active route is a later-reception navigation, not a separate exact-quotation bridge.

## Held candidate identity and evidence

The NE-10 held record `psalm-110-acts-2-enthronement` proposes endpoints `Psalm 110:1` and `Acts 2:22-36`. Its observed CKL record is `psalms#new_testament_connections[2]`, with content hash `9a0dc0eaed0808153a558e203460374d90033288b53d259e0ddeacd49afcf98a`. That parent-level list says Acts applies several Psalms, including Psalm 110, to Jesus and enthronement. It does not specify the Psalm 110 / Acts 2:34–36 pair or attach source discussion to that exact claim. The held reason remains valid.

The active NE-9C route has record-attached evidence for the broader Acts 2:22–36 / Psalm 110:1–7 reception connection. The held NE-10 row does not add an independently reviewed source or a new textual relation. Narrowing its Psalm endpoint to verse 1 would make the displayed scope more precise, but the destination is already present and there is no distinct evidence that warrants another runtime edge. A future proposal could refine the active authored route’s passage display after a separate review, but that is outside this reconciliation and must not be inferred as permission to edit NE-9C.

## Textual observation and limits

Acts 2:34–35 explicitly quotes Psalm 110:1 in Peter’s argument; Acts 2:22–36 connects Jesus’ resurrection, exaltation, and Davidic language. Psalm 110’s original setting and the scope of its later messianic readings remain interpretive questions. The present route reports Acts’ reception without presenting that reading as the only possible original meaning of the Psalm.

## Required state

- Keep active NE-9C identities and their provenance unchanged.
- Keep held NE-10 candidate `psalm-110-acts-2-enthronement` held.
- Do not insert a second Psalm 110 / Acts 2 bridge.
- Preserve existing Psalm 110 and Acts 2 curated pathways.
