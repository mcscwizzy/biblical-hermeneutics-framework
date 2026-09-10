# Commentary v1.2 reader provenance binding v1

Status: `REPLICATION_PASS`

This diagnostic prototypes `reader-provenance-binding-v1` for the four
chapters that failed the immutable v1.2 scale-pilot Batch 001. It preserves the
failed pilot namespace and does not address the separate Galatians 3 core
omission.

The repository was verified at starting SHA
`b5e132f464e7cdde9f5c4ec4b5643bc12cd66a8b` on
`feat/commentary-v1.2-enrichment`. The immutable source pilot manifest records
source head `07778940c159449443fd8d47ffeeca00b2732483`; that source identity is
preserved exactly in the diagnostic rather than rewritten.

## Original forensic finding

All four failures had the same boundary defect. The response was structurally
valid and the emitted synthesis/evidence pairs were valid pairs in the broader
compiled chapter packet, but those units were not in the projected
`reader-level-idea-ancestry-envelope-v1`. The existing validator therefore
had no selected envelope path that could own the evidence. No original failure
was an arbitrary evidence ID paired with the wrong synthesis unit inside a
selected path.

| Chapter | Invalid blocks | Exact emitted pairing(s) | Failure classification |
| --- | ---: | --- | --- |
| Romans 3 | 1, 2 | `syn_cultural_context_8c1669577161` → `what-is-justification:ancient_near_east_context:0`; `syn_historical_context_fb8be01f878c` → `what-is-justification:historical_context:0`; `syn_why_it_matters_4dc0bf04228d` → the three `sacrifice-theme:*` records | Full-packet units absent from the envelope; each listed pair is internally owned, but no projected path owns it. |
| Joshua 10 | 1 | `syn_cultural_context_2f72cd314568` → `gezer-excavations:ancient_near_east_context:0`; `syn_historical_context_95240b302141` → `gezer-excavations:historical_context:0` | Full-packet Gezer units absent from the envelope. |
| Leviticus 1 | 2, 3, 4 | `syn_cultural_context_49b31e5bc21c` → `what-is-sacrifice-in-the-bible:ancient_near_east_context:0`; `syn_cultural_context_d9ff44d67539` → `sacrificial-system:ancient_near_east_context:0`; `syn_historical_context_167e48ffb96e` → `what-is-sacrifice-in-the-bible:historical_context:0`; `syn_cultural_context_03b0b7b957a9` → the two `tabernacle:*` cultural records; `syn_archaeology_geography_c7624aec1055` → `tabernacle:archaeology:0`, `tabernacle:archaeology:1` | Three full-packet families absent from the envelope. Each emitted synthesis retained its own evidence ancestry. |
| Genesis 5 | 1, 2 | `syn_cultural_context_8eef7c51735f` → `image-of-god-theme:ancient_near_east_context:0`, `image-of-god-theme:hebraic_worldview:0`; `syn_historical_context_96ed179e29c4` → `image-of-god-theme:historical_context:0`; `syn_cultural_context_6f86312d094a` → `why-are-genealogies-included:ancient_near_east_context:0`; `syn_historical_context_089897c1316e` → `why-are-genealogies-included:historical_context:0` | Full-packet image-of-God and genealogy units absent from the envelope. |

The model did not mix IDs from the same projected idea, neighboring projected
ideas, or multiple valid envelope paths in these four original failures. It
selected material from another available source of ambiguity: the flat,
full-packet synthesis/citation surface remained manually addressable even
though the relational envelope exposed a smaller reader-level selection.

The valid paths that were available to the renderer were:

* Romans 3: 17 paths: `syn_interpretive_questions_09e4bdb9c363` →
  `romans-justification-pistis-christou:passage-relevance`;
  `syn_interpretive_questions_96eb7f62caf2` and
  `syn_why_it_matters_da699cecd85f` → the five
  `romans-boasting-law-faith*`, `romans-jewish-advantage-oracles*`, and
  `romans-justification-pistis-christou` records;
  `syn_interpretive_questions_2ed5753a8993` and
  `syn_why_it_matters_0e2c0068d0d6` → notes 13, 14, 22, and 23;
  `syn_interpretive_questions_9489d624c71e` and
  `syn_why_it_matters_bee215f783c4` → `romans-hilasterion`,
  `romans-pistis-christou`, `romans-righteousness`, and
  `romans-works-law`; `syn_interpretive_questions_fef1c161fa0a` → note 24;
  eight surrounding-passage paths → the letter-level notes, codices, papyri,
  and justification records; and
  `syn_surrounding_passages_10c109369ce2` → `james:interpretive_note:17`.
* Joshua 10: `syn_interpretive_questions_5b8d611d4e87` → note 1;
  `syn_surrounding_passages_333285c958d1` and
  `syn_surrounding_passages_facc7f6e6ddb` → notes 2 and 3;
  `syn_surrounding_passages_5f5a40a4da31` → note 0; and
  `syn_surrounding_passages_d6df05112dbe` → `joshua-literary-movement`.
* Leviticus 1: `syn_cultural_context_cf933b98be06` → note 0;
  `syn_historical_context_ab6cb0655069` → `leviticus-called-from-tent`;
  `syn_surrounding_passages_22699ef4d482` → note 2; and
  `syn_surrounding_passages_32dab3494fa3` → `leviticus-literary-movement`.
* Genesis 5: `syn_surrounding_passages_20aed11f4418` and
  `syn_surrounding_passages_f65e58d68f5b` → the comparative-context record
  and notes 0–2; `syn_surrounding_passages_7b40a731c38d` →
  `genesis-literary-movement`.

## Binding design

`build_provenance_binding()` reads the already validated envelope and creates
one record for every existing idea/path pair. A path ID is content-derived
from the chapter identity, reader-idea ID, and canonical serialization of the
complete existing path, including its synthesis ID, evidence IDs, path scope,
uncertainty, anchors, and immutable evidence/synthesis hashes. IDs are scoped
and recognizable as:

```text
reader_path_{book_slug}_{chapter:03d}_{first_24_hex_chars_of_path_hash}
```

The binding artifact stores the exact path definition, path hash, reader idea,
synthesis ID, evidence IDs, envelope identity, and binding hash. It creates no
new parentage and cannot invent a synthesis/evidence relationship.

For a block, the renderer now selects:

```json
{"provenance_refs": ["reader_path_romans_003_..."]}
```

The resolver deterministically performs:

```text
provenance_refs
→ selected complete paths
→ ordered unique synthesis IDs
→ ordered unique evidence IDs descended from those paths
```

When multiple paths are selected, the resolver unions only those selected
paths. The raw response remains preserved; a staged normalization copy removes
`provenance_refs` and writes the existing canonical `synthesis_ids` and
`evidence_ids` fields before the unchanged validator and scorer run. Binding
metadata retains the path-level relationship in the diagnostic artifact.

The resolver rejects malformed, duplicate, unknown, out-of-chapter, and
identity-tampered references. The new failure codes are bounded to:

* `MALFORMED_PROVENANCE_REFERENCE`
* `DUPLICATE_PROVENANCE_REFERENCE`
* `MISSING_PROVENANCE_REFERENCES`
* `UNKNOWN_PROVENANCE_PATH`
* `OUT_OF_CHAPTER_PROVENANCE_PATH`
* `PROVENANCE_PATH_IDENTITY_MISMATCH`

`SYNTHESIS_ANCESTRY_MISMATCH` remains unchanged and remains a hard validator
failure. The normalization assertion also proves that an evidence ID cannot
enter the canonical block unless it descends from one of the selected paths.

## Compatibility impact

The following contracts remain unchanged:

* renderer prompt `1.7` and its system-prompt bytes;
* `reader-level-idea-projection-v1` and reader-level idea grouping;
* `reader-level-idea-ancestry-envelope-v1`;
* synthesis semantics and CKL records;
* `essential-passage-context-v2`, `reader-relevance-eligibility-v1`,
  `commentary-richness-clusters-v2`,
  `commentary-richness-policy-v3-reader-relevance`, and
  `commentary-richness-gate-v2.1`;
* canonical Commentary schema `1.2`, validator behavior, scorer behavior, and
  richness thresholds.

No prompt 1.8 was created. The only prompt change is an additive user-input
adapter appended after the frozen prompt-1.7 input. It changes only the
machine-readable selection format; prose-generation, breadth, uncertainty,
and reader-facing rules remain prompt-1.7-equivalent.

## Four-chapter replication

Diagnostic namespace:
[`reader-provenance-binding-v1-6bceab0758ee36f2c176`](../.bhf-data/bhf-commentary-candidates/reader-provenance-binding-v1-6bceab0758ee36f2c176)

| Chapter | Structural | Path valid | Ancestry mismatches | Hard provenance | Weighted | Core | Eligible | Category | Dump | Gate | Readability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Romans 3 | PASS | PASS | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS |
| Joshua 10 | PASS | PASS | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS |
| Leviticus 1 | PASS | PASS | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS |
| Genesis 5 | PASS | PASS | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | NONE | PASS | PASS |
| **Aggregate** | **4/4** | **4/4** | **0** | **0** | **mean 1.0000; median 1.0000** | **100%** | **mean 1.0000** | **100%** | **0 HIGH** | **100%** | **100%** |

All four fresh responses were syntactically valid, generated exactly once, and
classified `CLEAN_PASS`. The normalized blocks represented all projected ideas
in each chapter. Fresh prose word counts were 369, 181, 163, and 129; the
simple mean was 210.5 words. No internal provenance vocabulary, evidence-dump
signal, repeated sentence, or readability failure was detected by the frozen
qualitative checks.

The original-to-replication ancestry mismatch counts were:

```text
Romans 3:     2 → 0
Joshua 10:    1 → 0
Leviticus 1:  3 → 0
Genesis 5:    2 → 0
```

## Tests and artifacts

Focused binding tests: `8 passed`.

They cover deterministic IDs and serialization, chapter scoping,
unknown/malformed/duplicate rejection, exact resolution, no cross-synthesis
leakage, canonical normalization, immutable path tampering, artifact
reproducibility, prompt/projection immutability, and the unchanged validator
contract. The diagnostic stores source failed-response hashes, path catalogs
and audits, prompt/input identities, raw responses, normalized responses,
validator outputs, scorer outputs, comparisons, and final checksums in the
immutable namespace above.

Binding hashes:

```text
Romans 3:     a5b643175cb91d11b39675bd67bf9960e308114a39256eec74c1a1a63b277313
Joshua 10:    45130f714a80f8fa367ccce6f87891ef0967ef7241e12cce99bd7ef9e5f7fa9c
Leviticus 1:  6674e91818d5233be7ff71d6e7d8eb0e01f033b6535965890ee7255e02788250
Genesis 5:    98490d26d663e539e91436c7b19997d0bf0068999ff631691531a9ddc8b70c37
```

The first renderer launch was blocked before response creation by the
sandboxed Codex runtime's read-only app-server initialization. It produced no
bytes and wrote no response. The required identical command was then run with
the runtime permission needed to initialize that state; the recorded
diagnostic still contains exactly one successful generation per chapter and
zero retries.

## Recommendation

The four-chapter replication is promising and meets the primary ancestry
criterion. Resume or cleanly restart the frozen 75-chapter scale pilot from
Batch 001 in a new immutable namespace under this binding contract. Do not
generate the remaining pilot chapters as part of this diagnostic.

Galatians 3 remains an unresolved secondary core-coverage omission and was not
changed, rescored, or used to tune this remediation.

