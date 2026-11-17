# CKL Explanation Enrichment Progress

This directory tracks the library-wide explanation review requested for the
CKL. The machine-readable inventory in `progress.json` has one row for every
CKL object. Rows remain `pending_review` until all applicable explanatory fields
in that object have been examined. `in_progress` marks a record with a reviewed
and validated field batch but unfinished object-level coverage. It is not
counted as a fully enriched, unchanged, or skipped object.

## Baseline

- Branch: `feat/ckl-explanation-enrichment`
- Base: `origin/master` at `0c9c78afeccc210d7e81f55e32a980c1c4673df4`
- Inventory: 687 objects
- CKL validation: 687 valid, 0 errors, 14 pre-existing warnings
- Protected-field hashes are compared with the fetched base revision.
- ED-7 currently classifies 71 evidence records as withheld from reader
  promotion. Those classifications, NE-9C curations, NE-10 bridges, and held
  candidates remain protected inputs.

## Current checkpoint

At this checkpoint, **1 object is enriched**, **2 are unchanged because they
are already sufficient**, **4 are skipped pending source research**, and **680
remain pending review**.

Batch 001 clarified four existing Genesis 5 claim rationales: the genealogy's
repeated pattern, its mortality refrain, Enoch's distinct ending, and the
transition toward Noah. Batch 002 completed the Genesis object review. It
strengthened the book summary, clarified additional claim rationales, and
replaced repetitive wording in nine Genesis 2 passage-relevance explanations.
The detailed historical and literary contexts were already careful and were
left intact. The ancient Near Eastern comparison claim and Genesis 5 textual
variant evidence were not expanded because their source arguments were not
independently rechecked.

Both Genesis validation runs passed with 1 valid object, 0 errors, and 0
warnings. The full CKL validator reports 687 valid objects, 0 errors, and the
same 14 warnings as baseline. CKL schema, packaging, retrieval, service, and
precision regressions passed 107 tests and 4 subtests. Source-lock and claim
scope checks passed 35 tests; NE-9C/NE-10 projection and curation regressions
passed 73 tests. API test collection remains unavailable because `fastapi` is
not installed. Per-batch results and protected-field fingerprints are in
`progress.json`.

The first archaeology record, Arad Ostraca, was reviewed and left unchanged.
Its CKL summary and literary context refer to Lachish, Jerusalem, and Joshua;
its Scripture references do not establish an Arad artifact connection; and its
four source entries lack bibliographic locators and claim support. A reliable
explanation needs new source research identifying the artifact, excavation,
publication, and any relevant biblical connection. The object has 10 existing
section-status warnings, unchanged from baseline.

The Babylonian Chronicles object was also reviewed and left intact: it already
explains the 597 BCE notice, the limits of what BM 21946 records, its
Babylonian chronicle setting, and the qualified identification of the city of
Judah. The Balaam Inscription object was skipped for the same source-integrity
reason as Arad: its title and generic text do not match its source records and
biblical anchors. Research must establish which inscription the entry intends
before any explanatory prose can be safely written.

The Bronze Snake record was also held. Its title points to the serpent in
Numbers 21, while its summary and historical context describe the Merneptah
Stele and its reference to Israel. Its source records do not resolve that
subject mismatch. The CKL needs a reviewed correction or separate records
before either topic can be enriched safely.

Beth Shean was skipped because its source entries lack bibliographic details
and its brief summary does not identify the excavation contexts behind its
period labels. The Black Obelisk explanation was left unchanged: it already
connects the tribute register with Jehu's reign while distinguishing the
Assyrian imperial display from the biblical account and preserving uncertainty
about the figure and the designation "House of Omri."

## Reader reachability

Canonical object detail responses serialize summaries and evidence items.
Retrieval indexes evidence title, description, primary observation, scholarly
interpretation, passage relevance, and confidence rationale. Claim rationales
are serialized in canonical object detail, but the standard canonical browser
modal does not render them, and retrieval indexes claim text rather than
rationale. This batch improves the CKL research layer without claiming direct
reader display. Evidence presentation depends on the Narrative Explorer
evidence packet.

## Resume and validation

Refresh the inventory while preserving existing progress, then validate it:

```sh
python3 tools/ckl_enrichment_progress.py --sync
python3 tools/ckl_enrichment_progress.py --check
```

Validate the full CKL after each content batch:

```sh
python3 tools/ckl_validate.py
```

The next work unit is `objects/archaeology/caesarea-maritima-excavations.json`.
Record field paths, actual outcomes, validation evidence, and checkpoint commit
IDs in `progress.json`.
