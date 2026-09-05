# BHF Commentary v1.1 — Context Expansion

This is development/candidate work on `feat/commentary-v1.1-expansion`. `commentary-v1.0` and `commentary-v1.0.1` remain immutable, and production selection remains `commentary-v1.0.1`.

## Baseline and scope

Strict baseline: 827 AVAILABLE, 210 THIN, 152 DATA_GAP across 1189 chapters.
The strict DATA_GAP set contains 152 chapters. 20 are object-only structural cases, leaving 132 likely true CKL DATA_GAP chapters for expansion.
Prioritization signals are deterministic text/search factors only; they are not evidence and do not promote availability.

## Initial batches

DATA_GAP batch (10): Numbers 5, Luke 8, Numbers 8, Numbers 7, Numbers 3, 1 Kings 7, Luke 5, Ezekiel 7, 2 Chronicles 8, Luke 13
THIN batch (20): Numbers 16, Jeremiah 2, Psalms 106, Numbers 19, Numbers 31, Deuteronomy 26, Isaiah 28, Deuteronomy 21, Judges 20, Leviticus 22, Leviticus 21, 1 Chronicles 29, 2 Chronicles 26, Ezekiel 8, 2 Chronicles 29, Isaiah 62, Jeremiah 19, 1 Chronicles 16, Leviticus 7, Deuteronomy 15
25-chapter canary (25): Numbers 5, Luke 8, Numbers 8, Numbers 7, Numbers 3, 1 Kings 7, Luke 5, Ezekiel 7, 2 Chronicles 8, Luke 13, Numbers 16, Jeremiah 2, Psalms 106, Numbers 19, Numbers 31, Deuteronomy 26, Isaiah 28, Deuteronomy 21, Judges 20, Leviticus 22, Leviticus 1, Psalms 1, Zephaniah 1, Luke 1, Genesis 1

## High-confusion pass

The ranked list is stored in `data-gap-priority.json`. 1 Samuel 28 is explicitly retained as a known context-thin example; the list does not decide whether the apparition was Samuel.

## Genre-aware evidence guidance

- **narrative** — prefer history, culture, archaeology, geography, politics, institutions, chronology. Ask: What setting, institution, custom, or sequence does the scene assume? Which claims are tied to this episode rather than the whole book?
- **law** — prefer ritual and purity, priesthood, sacrifice, social order, covenant setting, language. Ask: What function does the instruction have inside Israel's covenant life? Is the claim anchored to the law unit rather than generalized across the book?
- **poetry** — prefer literary form, parallelism, worship context, royal imagery, temple imagery, language, superscription when sourced. Ask: How do paired lines and images work together? What is textual observation, and what is later interpretation?
- **wisdom** — prefer literary form, household instruction, education, rhetoric, parallelism, metaphor, social and economic context, language. Ask: Is this a maxim, reflection, dialogue, or rhetorical challenge? Does the supporting evidence clarify the social setting without turning a saying into a guarantee?
- **prophecy** — prefer historical setting, politics, geography, symbolic actions, temple context, covenant/law background, literary structure, sourced ANE context. Ask: Who is addressed and what pressure is visible in the passage? Which symbolic or historical claims are actually source-supported?
- **gospel** — prefer Second Temple setting, geography, social custom, politics, literary structure, chronology. Ask: What does this scene assume about its social setting? How does the Gospel's own narrative design constrain the contextual claim?

## Evidence-first lock boundary

Each batch must be audited against existing CKL first, then Scripture anchors are validated, JSON and SQLite are rebuilt/compared, EvidenceBundles are hashed, availability is classified, and leakage is checked before commentary candidates are generated. A source gap remains a DATA_GAP.

## Reports

- Machine-readable prioritization: `.bhf-data/bhf-commentary-candidates/commentary-v1.1/data-gap-priority.json`
- Certified batch reports are written beside it as `evidence-certification-<batch>.json`.
- Low-information audit: `.bhf-data/bhf-commentary-candidates/commentary-v1.1/low-information-commentary.json`
- Low-information human report: `docs/commentary-v1.1-low-information-audit.md`
