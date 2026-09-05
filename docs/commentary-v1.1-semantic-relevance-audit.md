# BHF Commentary v1.1 Semantic-Relevance Audit

This is a development audit for `feat/commentary-v1.1-expansion`. Production
selection remains `commentary-v1.0.1`; no released artifact, release variable,
deployment, merge, or Terra prose pass was changed.

## Result

The 25-chapter canary was rebuilt with candidate EvidenceBundle version `1.1`
and locked successfully.

- Chapters audited: 25
- Evidence items examined after repair: 172
- Direct first-audience context: 28
- Book context: 20
- Later/intertextual reuse: 13
- Comparative context: 2
- Generic background: 109
- Remaining semantically misanchored items: 0
- Candidate validation: 25 valid, 0 invalid
- JSON/SQLite result-ID disagreements: 0
- JSON/SQLite hash disagreements: 0
- Retrieval leakage: 0 chapters, 0 evidence IDs

The machine-readable item-level audit is
`.bhf-data/bhf-commentary-candidates/commentary-v1.1/semantic-relevance-audit.json`.

## Semantic model

Evidence now receives deterministic relationship metadata: `DIRECT_CONTEXT`,
`BOOK_CONTEXT`, `INTERTEXTUAL_REUSE`, `LATER_RECEPTION`,
`COMPARATIVE_CONTEXT`, `GENERIC_BACKGROUND`, `WEAKLY_RELATED`, or
`SEMANTICALLY_MISANCHORED`.

Later and comparative material remains available to `dig_deeper` and
`interpretive_questions`, but cannot drive first-audience overview, historical
context, or archaeology/geography sections. Generic archaeology is not treated
as passage-specific archaeology without direct materially relevant evidence.

## Confirmed CKL edits

Each record below had only the synthetic `Genesis 1:1-2` Scripture anchor
removed. Its other content and Scripture links were preserved.

| Record | Old anchor | New anchor | Relationship | Affected chapter |
|---|---|---|---|---|
| `arad-ostraca` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `caesarea-maritima-excavations` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `ein-gedi-scroll` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `herodium-excavations` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `kurkh-monolith` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `masada-excavations` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `pool-of-bethesda-excavation` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `samaria-ostraca` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `samaria-palace` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |
| `shiloh-excavations` | Genesis 1:1-2 | none | semantically misanchored | Genesis 1 |

Reason: these site-specific archaeological records were connected to Genesis 1
through a broad theological/context tag, not through materially relevant
Genesis 1 geography or first-audience historical evidence. The record titles,
summaries, periods, and archaeology source metadata support later or otherwise
specific material contexts. No broad automated CKL deletion was performed.

## Genesis 1 negative control

- `2-corinthians:interpretive_note:21`: anchor `Genesis 1:3` is textually
  valid, but the claim is later Pauline reception. It remains in the bundle as
  `LATER_RECEPTION`, is available for `dig_deeper`, and is excluded from
  overview, historical context, and archaeology/geography.
- Arad Ostraca and Caesarea Maritima: confirmed bad `Genesis 1:1-2` anchors
  removed; neither appears in the repaired bundle.
- The other eight records with the identical synthetic anchor were repaired by
  the same individually documented CKL edit.
- Cross-testament and canonical reuse remains accessible as reception or
  intertextual evidence. It is no longer allowed to masquerade as Genesis 1
  first-audience history.
- Comparative creation material remains available as comparative context and
  is routed to `dig_deeper`, not selected as the overview when direct textual
  context exists.

Genesis 1 changed from 90 to 70 evidence items. Its overview is now the direct
textual observation `genesis-ordered-worldview-observation:passage-relevance`.
The candidate preserves its compiler-clipped chapter overlap as
`Genesis 1:1-31`; exact item anchors such as `Genesis 1:3` and
`Genesis 1:26-27` remain exact in their blocks.

## Required controls

- Zephaniah 1 remains `AVAILABLE` with 17 source-addressable items. Its
  overview is directly anchored to `Zephaniah 1:1`; Day of the LORD evidence
  remains available for contextual sections. No verse-count/opening/closing
  boilerplate or provider prose was introduced.
- 1 Samuel 28 remains `THIN` with two evidence items. The apparition note is
  still disputed and later theological readings are not promoted to historical
  fact.
- Numbers 3 remains `DATA_GAP` with zero evidence items.
- Leviticus 1 remains `AVAILABLE` with 26 items; Psalms 1 remains `AVAILABLE`
  with 15; Deuteronomy 21 remains `THIN` with 3.

## Compiler and eligibility changes

Overview selection is deterministic and semantic-role aware. It prefers direct
chapter/verse context, then book context, then relevant high-confidence
background. It is independent of bundle array order.

Commentary blocks preserve exact evidence anchors. Multi-chapter anchors are
clipped only to their actual overlap with the requested chapter for validation;
single-verse and verse-range anchors are never broadened.

Interpretation mapping now uses assertion type and dispute status together:
explicit factual/textual assertions remain `fact`, inference remains
`inference`, disputed claims remain `disputed`, and unclear metadata defaults
conservatively to `inference`.

Low-information regeneration eligibility now requires semantically relevant,
source-addressable, role-suitable evidence. Eligibility changed from 936 to
935 chapters; `Psalms 24` is the one chapter that moved from eligible to
insufficient after semantic filtering. Availability labels were not changed by
this audit.

## Genre and hash semantics

Canonical genre coverage now resolves all 66 BHF book names. `Song of Songs`
resolves to poetry; no canonical book silently falls through to narrative or an
unknown bucket.

Candidate EvidenceBundle identity uses version `1.1`. The v1 hash included
`retrieval_score`; candidate v1.1 excludes that volatile backend ranking value.
Evidence content, provenance, and semantic relevance metadata remain hashed.
Released v1.0.1 artifacts are not rewritten or invalidated.

## Boundary

The deterministic compiler remains an evidence-structure validation tool. It
does not generate final prose. A future Terra/Luna pass must receive canonical
chapter text, the locked v1.1 EvidenceBundle, allowed sections, and grounding
constraints.
