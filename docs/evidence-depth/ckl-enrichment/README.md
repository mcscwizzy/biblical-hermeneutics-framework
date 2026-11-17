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

At this checkpoint, **1 object is enriched**, **8 are unchanged because they
are already sufficient**, **41 are skipped pending source or identity
research**, and **637 remain pending review**.

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

The Mount Ebal Altar Discovery entry was held because its content instead
describes Qumran and the Dead Sea Scrolls, including unrelated Scripture
anchors and source IDs. The entry needs object identity reconciliation before
any archaeological explanation can be written.

The Nimrud Reliefs record was held because its summary describes the Lachish
relief cycle, while the title and generic source IDs point to Nimrud/Nineveh.
It needs the relief cycle identified precisely before the record can be
expanded.

The Pool of Bethesda entry was held because its current references and sources
point to unrelated creation/City of David material rather than John 5 and the
pool. Site identification and relevant excavation publications need to be
verified before any connection is written.

The Pool of Siloam Discovery entry was also held: its explanatory notes and
source IDs describe the tunnel inscription, while the title names the pool.
The pool and inscription need distinct, verified evidence and passage links.

The Siloam Inscription and Taylor Prism entries were held because their source
records lack artifact identifiers, locators, and source-supported claims. The
Siloam entry needs a verified inscription text and tunnel connection; Taylor
Prism should be reconciled with the better-supported Sennacherib Prism record.

The Tel Dan Stele and Tel Rehov Honey Workshop entries were both held because
their source records and Scripture links instead describe the Tel Dan Stele.
The named objects need separate, site-specific records and verified excavation
sources before contextual prose can be added.

Tell Dan Excavations, Tell es-Safi Excavations, Temple Mount Area Finds, and
Wadi Murabba'at Scrolls were held because their records respectively repeat
stele material, mix site identities, describe Qumran material, or lack
site-specific manuscript evidence. The Temple Warning Inscription entry was
left unchanged; it already explains the warning's placement, its relation to
the temple boundary, and the limited connection to Acts 21 with a museum source.
All five records passed object validation with zero errors and the same ten
pre-existing section-status warnings.

The Merneptah Stele and Jerusalem Stepped Street explanations were left intact.
Their recorded inscription, scholarly volume, and Israel Antiquities Authority
excavation report support the existing descriptions, contextual connections,
and interpretive limits. The Moabite Stone and Pilate Stone entries were held:
their explanatory notes refer to significant inscriptions, but the recorded
source lists are title-only placeholders without locators, URLs, or support
links. All four objects passed validation with zero errors and ten existing
section-status warnings each.

Shiloh Excavations was held because its sources and Scripture links point to
Jerusalem and general creation texts rather than site-specific Shiloh evidence.
The record needs excavation phases and relevant biblical anchors reviewed.

Qumran Archaeological Site, Qumran Caves, and Samaria Ostraca were also held:
their records lack manuscript/site-specific evidence or contain mismatched
source and Scripture links. The Sennacherib Prism entry was left unchanged
because it already explains the annals and Lachish reliefs as separate Assyrian
royal presentations, distinguishes artifact dates from the 701 BCE campaign,
and qualifies comparison with Kings and Isaiah.

Beth Shean was skipped because its source entries lack bibliographic details
and its brief summary does not identify the excavation contexts behind its
period labels. The Black Obelisk explanation was left unchanged: it already
connects the tribute register with Jehu's reign while distinguishing the
Assyrian imperial display from the biblical account and preserving uncertainty
about the figure and the designation "House of Omri."

Seven more archaeology records were held for research because their source
entries lack locators or claim support, or their titles, summaries, and
Scripture anchors identify different subjects. These include Caesarea,
Caiaphas, City of David, Dead Sea Scrolls, Ein Gedi, Elephantine, and Gezer.
The Cyrus Cylinder record was left unchanged because its object identity,
inscription setting, comparison with Ezra, and policy limits are already
explained with source-linked qualifications. All eight objects validated with
zero errors and the same ten pre-existing section-status warnings each.

Eight additional archaeology objects were held: Gibeon wine jars, Hazor,
Herodium, Hezekiah's tunnel inscription, the James Ossuary, the Ketef Hinnom
silver scrolls, the Kurkh Monolith, and the Lachish city gate. Their records
either use generic or mismatched sources, omit the relevant excavation or
inscription evidence, or lack a verified link between the artifact and the
passages. Each passed single-object validation with zero errors and the same
ten pre-existing section-status warnings.

In the next review group, the Lachish Reliefs explanation was already
sufficient: it describes the Assyrian visual account and its royal purpose,
then distinguishes that evidence from Kings and Isaiah. Lachish Ostraca,
Masada, Megiddo, and the Mesha Stele were held because the current CKL entries
lack specific artifact or stratigraphic references tied to their biblical
anchors. Their source details need repair or review before expansion.

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

The next work unit is `objects/archaeology/samaria-palace.json`.
Record field paths, actual outcomes, validation evidence, and checkpoint commit
IDs in `progress.json`.
