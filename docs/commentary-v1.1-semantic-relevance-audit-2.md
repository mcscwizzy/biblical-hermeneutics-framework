# BHF Commentary v1.1 Semantic-Relevance Audit 2

This deterministic pass hardens the 25-chapter candidate evidence boundary on `feat/commentary-v1.1-expansion`. Production `commentary-v1.0.1` was not modified, and Terra was not run.

## Result

- Chapters audited: 25
- Evidence items examined: 158
- Word-study records examined: 10
- Word-study anchors removed: 7
- Word-study anchors reclassified: 2
- Candidate validation: 25 valid, 0 invalid
- JSON/SQLite result-ID disagreements: 0
- JSON/SQLite hash disagreements: 0
- Retrieval leakage: 0 chapters

## Word-study decisions

The audited generated records did not prove a source-language lexical occurrence merely by carrying a thematic Scripture anchor. `parakletos`, `pneuma`, `katabole`, `phos`, `skotia`, `sarx`, and `shema` had the confirmed bad canary anchors removed. `makarios` and `nomos` remain as comparative Greek translation evidence; `torah` remains direct Psalm 1 lexical evidence.

## Required controls

- **Genesis 1**: AVAILABLE; 58 evidence items; overview `genesis-literary-movement`; sections `chapter_overview, historical_context, chronology, dig_deeper`.
- **Luke 1**: AVAILABLE; 26 evidence items; overview `luke-prologue`; sections `chapter_overview, historical_context, language_literary, dig_deeper`.
- **Leviticus 1**: AVAILABLE; 26 evidence items; overview `leviticus:interpretive_note:0`; sections `chapter_overview, historical_context, language_literary, chronology`.
- **Zephaniah 1**: AVAILABLE; 17 evidence items; overview `zephaniah-superscription`; sections `chapter_overview, historical_context, language_literary`.
- **1 Samuel 28**: THIN; 2 evidence items; overview `first-samuel-literary-movement`; sections ``.
- **Numbers 3**: DATA_GAP; 0 evidence items; overview `None`; sections `chapter_overview`.

Genesis 1 has no reachable `parakletos`, `katabole`, or `pneuma` word-study item, no Arad/Caesarea evidence, and retains Pauline reuse only in `dig_deeper`. Luke 1 routes `luke-acts-relation` to `language_literary`. Leviticus 1 routes sacrifice background to `historical_context`. Zephaniah 1 replaces textual witnesses with Josiah-era superscription context as overview. 1 Samuel 28 remains THIN with the apparition disputed. Numbers 3 remains an honest DATA_GAP with zero evidence.

## Overview and section routing

Overview ranking now uses explicit reader-usefulness priority before semantic relationship, presentation role, category, anchor specificity, confidence, and only then the evidence ID. The section budget reserves a `dig_deeper` slot when useful evidence exists and never forces one without evidence.

## Hash and regeneration semantics

Candidate EvidenceBundle version 1.1 continues to use evidence hash version 2. Retrieval score remains excluded as volatile backend ranking metadata. Presentation role is included because it changes which section may ground a candidate. Evidence content, provenance, and semantic relationship metadata remain identity inputs. Regeneration eligibility is semantically filtered; the overall canary audit remains 935 eligible and 153 insufficient, with Psalms 24 the pass-1 change from eligible to insufficient.

## Unresolved concerns

The template-generated word-study pattern may exist outside the 25-chapter canary and should be a future CKL-authoring cleanup. Broad legacy category labels remain in CKL, but the deterministic presentation-role layer prevents the audited canary from treating them as section instructions.
