# G5B review digest — Jacob/Esau return evidence expansion

Transaction: `GENESIS_G5B_JACOB_ESAU_RETURN_EVIDENCE_EXPANSION`
Branch: `feat/genesis-g5b-jacob-esau-return`
Base master: `f752f9841a0ffc32e167afe7b79a4ecd62e475e4`
Final commit identity is reported after commit/push verification; this digest and the validation report are included in that commit.

## Scope and architecture

Added one isolated `cultural_background` CKL object, `genesis-jacob-esau-return-context`, at `framework/canonical_library/objects/cultural_background/genesis-jacob-esau-return-context.json`. Direct Scripture applicability is limited to Genesis 31–36. Comparative texts and later reception (including Genesis 28, Genesis 49, and Hosea 12) remain contextual; there is no reverse applicability, no reciprocal link write, and no modification to shared objects. The object uses 14 local source records, including identity-preserving aliases. Candidate replay accepted all 68 evidence items, rejected none, and all candidates were synthesized.

Object count: 684 → 685. Evidence count: 1,069 → 1,137. Source count: 5,181 → 5,195. Historical source-owner rows changed: **0**. New object schema, provenance, source-owner isolation, typed targets, relationship integrity, Scripture references, and whole-CKL checks passed.

## G0 outcomes

- **Genesis 31:** GAP (3 evidence / 3 synthesis) → GOOD (15 / 9).
- **Genesis 32:** GAP (5 evidence / 3 synthesis) → GOOD (17 / 11).
- **Genesis 33:** GAP (12 evidence / 3 synthesis) → GOOD (20 / 8).
- **Genesis 34:** SPARSE (5 evidence / 5 synthesis) → GOOD (17 / 12).
- **Genesis 35:** GAP (10 evidence / 3 synthesis) → GOOD (23 / 11).
- **Genesis 36:** SPARSE (4 evidence / 4 synthesis) → GOOD (15 / 11).

The established dimensional classifier was used. Each target reached GOOD; no chapter remained below GOOD. Raw evidence totals were not used as a proxy for coverage.

## Interpretive and ethical dispositions

- **Teraphim:** Rachel’s motive is not stated. Domestic/household cult, ancestral or domestic functions, divination, and inheritance-related proposals are represented as debated possibilities. No one theory is asserted as proven, and the objects are neither reduced to decoration nor used to claim Rachel rejected YHWH.
- **Covenant heap and Mizpah:** Galeed/Jegar-sahadutha’s Hebrew/Aramaic naming, pillar, heap, boundary/witness function, oath, and meal/sacrifice context are retained. “Mizpah” is not converted into a sentimental friendship blessing.
- **Wrestling, Israel, and Peniel:** Genesis begins with a “man”; Jacob interprets the meeting as seeing God face-to-face. Divine manifestation, messenger, intentionally mysterious man, and later reception are distinguished. Hosea 12 is not an applicability anchor, and no immediate-text Christological identification is forced. Israel’s striving/God/human wordplay remains lexically open. Peniel/Penuel and the face-of-God explanation are treated narratively; the injury receives no modern diagnosis.
- **Dietary etiological note:** Genesis 32:32 is discussed through its Hebrew anatomical term and etiological role; later halakhic specification is not read back as fully stated in Genesis.
- **Reconciliation:** Seven bows are treated as diplomacy/kinship prostration without assuming worship. Esau’s running, embrace, kiss, and tears are the immediate narrative response. The dotted “kissed” tradition does not prove murderous intent. Jacob’s gift/“blessing” and face-like-God statement are read with Peniel without divinizing Esau.
- **Dinah and Shechem:** The Hebrew and narrative sequence is presented as sexual violation; “rape/sexual assault,” coercive violation, and illicit-relation translation discussions are handled with lexical care, without inventing details or softening the episode into consensual romance. Shechem’s later attachment does not undo the violation. Jacob’s silence is recorded without invented psychology.
- **Circumcision and violence:** Simeon and Levi’s condition is deception, not legitimate covenant conversion. The third-day killing, rescue of Dinah, and plunder of livestock, property, women, and children are not sanitized. Genesis 34 does not say God commanded the massacre and is not used to authorize later ethnic hostility; Genesis 49 is context only.
- **Bethel and family transition:** Household gods, earrings, purification, garment change, tree burial, and Bethel rites are read in their scene; earrings are not inherently idolatrous. The “terror of God” does not license invented military events. Deborah, Rachel’s difficult labor and Ben-oni/Benjamin, uncertain burial-location traditions, Reuben/Bilhah’s household power implications, the twelve-son transition, and Isaac’s death/burial are included. No modern Rachel’s Tomb identification is asserted as certain.
- **Edom:** Genesis 36 is treated as a family record and clan, territorial, and political ethnography. `alluf` is cautiously rendered as chief/leader; Seir/Horite material is not racialized. Place identifications carry confidence limits, and no modern coordinates are manufactured. Anah’s `yemim` remains textually/lexically uncertain.
- **Genesis 36:31:** The king sequence and Israelite comparison raise real chronology/composition questions. Multiple responsible readings remain open; the verse alone does not prove a late date for all Genesis. Archaeological and historical comparanda contextualize political organization but do not prove patriarchal events.
- **Literary arc:** Separation from Laban → fear of Esau → divine encounter → reconciliation → settlement → Shechem crisis → Bethel return and household purification → Rachel/Isaac deaths → Esau/Edom genealogy is represented without repeating one literary observation across every chapter.

## Isolation and validation

- Whole-corpus comparison: 1,189 chapter preparation/synthesis identities compared; exact changed set is Genesis 31–36 only.
- The 24 requested representative controls remained exact to base, including Genesis 37/38 as read-only controls.
- Runtime SQLite was rebuilt and verified against JSON CKL; all six target chapters and controls matched.
- Commentary v1.2 frozen identities are exact; Commentary was not regenerated or modified. Genesis 31–36 are recorded as stale future Commentary inputs.
- Scripture-reference integrity: 15 passed. G5B isolation and dedicated fallback selection: 6 passed.
- Prior Genesis transaction suites: 17 passed and 2 stale Genesis 12 snapshot failures; the identical two failures reproduce on clean base. No G5B-introduced failure occurred. The historical snapshots were left intact; see `g5b-regression-reconciliation.json`.
- `git diff --check`: PASS. No merge or deployment performed.

## Claim dispositions

- Rachel stole teraphim solely to inherit Laban estate: REJECTED_AS_PROVEN; represent multiple responsible interpretations.
- Mizpah as originally a sentimental friendship blessing: REJECTED; explain boundary/witness context.
- Jacob explicitly wrestled Jesus in Genesis: REJECTED_AS_IMMEDIATE_TEXT.
- Hosea 12 angel language projected into Genesis as its own wording: REJECTED_AS_APPLICABILITY; later reception context only.
- Jacob injury assigned a modern medical diagnosis: WITHHELD_UNSUPPORTED.
- Esau’s seven bows as worship: REJECTED_AS_AUTOMATIC; diplomacy/kinship prostration context cautiously described.
- Masoretic dots over kissed prove Esau intended murder: REJECTED_AS_PROOF; document textual tradition cautiously if sources justify.
- Dinah’s assault sanitized as consensual romance: REJECTED; lexical and narrative agency carefully distinguished.
- Simeon and Levi massacre divinely commanded: REJECTED; no command appears in Genesis 34.
- Circumcision deception as legitimate covenant conversion: REJECTED.
- Genesis 34 authorizes hostility toward later ethnic groups: REJECTED.
- Earrings inherently idolatrous: REJECTED_AS_UNSUPPORTED; assess household context.
- A modern Rachel’s Tomb site is certainly the Genesis burial place: REJECTED_AS_CERTAIN.
- Genesis 36:31 alone proves a late Pentateuchal date: REJECTED_AS_AUTOMATIC; preserve composition debate.
- Genesis 36:24 yemim has one certain lexical meaning: REJECTED; retain textual/lexical alternatives.
- Specific patriarchal events are archaeologically proven: WITHHELD_UNSUPPORTED.
- Every divine/messenger scene encodes a divine-council system: REJECTED_AS_FORCED.

## Exact changed paths

- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-candidate-evidence.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-candidate-replay-final.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-chapter-impact.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-comparative-applicability-audit.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-existing-evidence-audit.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-final-ckl-identities.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-g0-target-results.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-jacob-esau-return-evidence-plan.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-post-apply-validation.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-production-apply-manifest.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-regression-reconciliation.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-review-digest.md`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-runtime-db-preparation-verification.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-source-lock.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-source-ownership-audit.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-validation-report.json`
- `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/staging/new-object.json`
- `docs/superpowers/plans/2026-10-10-genesis-g5b-jacob-esau-return.md`
- `framework/canonical_library/manifest.json`
- `framework/canonical_library/objects/cultural_background/genesis-jacob-esau-return-context.json`
- `tests/test_genesis_g5b_jacob_esau_return_isolation.py`

## Independent review

The first read-only whole-diff review found one Important audit issue: the production apply manifest listed 685 before and 686 expected after, inconsistent with verified counts. It was corrected to 684 / 685 / 685. The reviewer independently rechecked the fix and reported no remaining Critical, Important, or Minor issues; review assessment is ready to merge.

## Gate state

All G5B content, isolation, runtime, Commentary-freeze, and regression-reconciliation gates pass. The independent whole-diff review found no critical issues and one important count inconsistency in the production apply manifest. That manifest was corrected to 684 objects before apply and 685 expected/after; this now agrees with the frozen base and final CKL identities. The reviewer confirmed that no Critical, Important, or Minor issues remain. Commit/push verification is the final branch-completion step. No merge or deployment is authorized or performed.
