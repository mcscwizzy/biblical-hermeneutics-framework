# BHF Commentary v1.1 Canary Report

Status: development candidate only. Production remains `commentary-v1.0.1`; no
release tag, selection change, merge, or deployment was made.

## Evidence result

The canary EvidenceBundle batch is `LOCKED`.

- 25 chapters certified: 10 DATA_GAP, 10 THIN, 5 AVAILABLE.
- New CKL evidence added: 0. No source-supported new claim was available in
  this batch without risking an overbroad anchor.
- Existing CKL evidence reused: 10 THIN and 5 AVAILABLE chapters. The exact
  evidence IDs, source IDs, anchors, confidence, and per-record CKL audit are
  in `evidence-certification-commentary_canary.json`.
- DATA_GAP chapters that remained DATA_GAP: Numbers 5, Luke 8, Numbers 8,
  Numbers 7, Numbers 3, 1 Kings 7, Luke 5, Ezekiel 7, 2 Chronicles 8, and
  Luke 13.
- Availability transitions in this evidence batch: DATA_GAP → THIN: 0;
  DATA_GAP → AVAILABLE: 0; THIN → AVAILABLE: 0. Targeting a chapter did not
  promote it.
- Source gaps: the ten DATA_GAP chapters had no source-addressable evidence
  surviving strict Scripture-anchor validation.

## Retrieval certification

- JSON/SQLite result-ID disagreements: 0.
- JSON/SQLite EvidenceBundle-hash disagreements: 0.
- Unexpected retrieval leakage: 0 chapters, 0 evidence IDs.
- All locked EvidenceBundle hashes are recorded in
  `.bhf-data/bhf-commentary-candidates/commentary-v1.1/evidence-certification-commentary_canary.json`.
- Retrieval scores remain visible for diagnostics, but are excluded from the
  EvidenceBundle identity hash because score representation is backend ranking
  metadata rather than evidence state.

## Commentary candidate validation

The 25 separate candidates under
`.bhf-data/bhf-commentary-candidates/commentary-v1.1/chapters/` all pass the
deterministic commentary validator.

- Valid candidates: 25; invalid: 0.
- Verse references: 52 valid; 0 invalid or out of chapter.
- Unknown evidence IDs: 0.
- Section kinds present: `chapter_overview`, `historical_context`,
  `archaeology_geography`, and `chronology`.
- DATA_GAP candidates contain transparent gap wording only. Contextual sections
  for THIN and AVAILABLE candidates are built only from locked evidence claims.
- Candidate metadata records the provider-independent boundary and future
  inputs: canonical chapter text, locked EvidenceBundle, allowed section kinds,
  and grounding constraints.

## Required follow-up

1. Review the prioritized 132-chapter true DATA_GAP list before adding any new
   CKL records.
2. Obtain source-addressable material for the DATA_GAP chapters that are worth
   pursuing; otherwise preserve the gap.
3. Review the candidate prose structure before any Luna prose pass or future
   Terra pass.

The machine-readable plan, priority lists, high-confusion ranking, genre
guidance, batch audits, hashes, and validation output are stored beside the
candidate artifacts.
