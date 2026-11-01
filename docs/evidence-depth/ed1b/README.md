# ED-1B Scholarly Evidence Enrichment Pilot

ED-1B starts from `origin/master` at `d528c8c8` (ED-1A merge; ED-1A commit `0e9453c9` is an ancestor). The pilot adds one source-grounded evidence item to each requested passage. It leaves NE-9C curation and NE-10 bridge records unchanged and adds no archaeological catalog records.

## Reader-visible before and after

The counts below come from the Narrative Explorer projection adapter using the CKL snapshot at `origin/master` and the working CKL after enrichment. The same projector and full Scripture retrieval were used for both snapshots.

| Passage | Before: directly scoped evidence | Existing reader-visible claims before | After: directly scoped evidence | New evidence ID, exact anchor, and projection section |
| --- | ---: | --- | ---: | --- |
| [Psalm 72](psalm-72.md) | 0 | `psalms-five-book-anthology` (72:18–20); `psalms-superscription-collections` (72:1) | 1 | `ckl:psalms#evidence:psalm-72-royal-justice-setting` — Psalm 72:1–14 — `themes_biblical_connections` |
| [2 Chronicles 30](2-chronicles-30.md) | 0 | `second-chronicles-hezekiah-passover` (30:1–27); `second-chronicles-judah-focus` (30:1–27) | 1 | `ckl:2-chronicles#evidence:second-chronicles-30-northern-invitation` — 2 Chronicles 30:6–12 — `biblical_narrative`, `themes_biblical_connections` |
| [Ezekiel 40](ezekiel-40.md) | 0 | `ezekiel-historical-horizon` (40:1–4); `ezekiel-practical-outline` (40:1–49); `ezekiel-temple-vision` (40:1–49) | 1 | `ckl:ezekiel#evidence:ezekiel-40-vision-measuring-sequence` — Ezekiel 40:1–16 — `biblical_narrative`, `themes_biblical_connections` |

The existing claims remain unchanged. In each after-projection, the new item is a separate evidence record with its direct passage anchor, certainty, dispute status, confidence rationale, text observation, scholarly interpretation, passage relevance, and resolved source records. The API projection exposes each source’s bibliographic details and locator; the projection itself validated against the current v1 contract.

## Acceptance results

| Passage | Pilot decision | Acceptance result |
| --- | --- | --- |
| Psalm 72 | Accepted: one item | Exact anchor is Psalm 72:1–14; primary observation is separated from Human’s Ancient Near Eastern and royal-psalm interpretation; the court-event setting is explicitly provisional; date and historical king remain unresolved. The article identity and pinpoint pages were verified. |
| 2 Chronicles 30 | Accepted: one item | Exact anchor is 2 Chronicles 30:6–12; the invitation and mixed response are distinguished from Knoppers’s postmonarchic reading; the composition horizon is stated as a proposal and separated from Hezekiah’s narrative setting. The publisher’s article identity, page range, DOI, and passage-specific abstract/notes locator were verified. |
| Ezekiel 40 | Accepted: one item | Exact anchor is Ezekiel 40:1–16; the relative date and measuring sequence are separated from Lyons’s literary-genre and composition proposals; no built structure or archaeological identification is asserted. The published chapter metadata and the accepted-version manuscript locator were verified, with their edition difference disclosed. |

“Accepted” means accepted for this bounded CKL pilot insertion. The book objects retain their existing `human_review_required: true` state and are not marked as human-reviewed or approved.

## Validation and integrity

Results are recorded after the final validation run:

- CKL schema and integrity validation: 687 objects valid, 0 errors, 14 warnings. The same 14 warning records were present on the ED-1A base.
- CKL manifest: a generated manifest was compared with the committed manifest; all values match. The committed file remains unchanged because ED-1B changes no manifest count or category.
- Source locks: the checked-in source-lock queue and its source records were validated; the queue was not changed.
- NE-9C: validation passed against the ED-1A snapshot with 3,925 reviewed records; the curation input was not changed. Against the enriched CKL, the validator rejects the unchanged checkpoint because it pins the CKL object-tree fingerprint; the checkpoint was not refreshed or edited.
- NE-10: verified and held registry hashes match the recorded baseline; neither registry was changed. The held `ezekiel-40-48-revelation-21-22-temple` bridge remains held.
- Narrative Explorer regressions and targeted passage projections: passed; details are in the final verification log below.

## Limitations and deferred research

- Psalm 72’s exact date, original occasion, and historical king remain disputed. The evidence item uses the royal-event setting only as Human’s qualified proposal and does not treat the idealized universal reign as a historical report.
- For 2 Chronicles 30, this pilot supports a literary and community-context reading. It adds no contemporary independent attestation of Hezekiah’s described Passover, and it does not use Sennacherib’s campaign as proof of the event.
- For Ezekiel 40, the relative date belongs to the vision’s narrated frame. The date of the chapter’s composition and the composition history of Ezekiel 40–48 remain uncertain. No construction, site identification, or archaeological catalog record is added.
- ED-1B does not revise the existing broad claims, source identities outside these additions, source-lock queue, NE-9C decisions, or NE-10 dispositions.

## Verification log

Final verification results:

- `python3 tools/ckl_validate.py --root framework/canonical_library` — PASS: 687 valid objects, 0 errors, 14 warnings; warning set matches the ED-1A base.
- Generated CKL manifest semantic comparison — PASS. Manifest values match; the committed manifest remains byte-for-byte unchanged because object and category counts did not change.
- Source-lock and manifest regression tests — PASS within the test run below. The source-lock queue hash is unchanged (`ebed284f492a60f438c2503eefbc591fd2a56795c4bba1e2021c34c9bc335fc8`).
- NE-9C baseline validation against the ED-1A snapshot — PASS: 3,925 decisions validated. A current-tree check returns the protected CKL fingerprint error expected when the CKL changes; the reviewed checkpoint was not refreshed or altered.
- NE-10 registry checks — PASS: verified bridge registry hash `8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b` and held candidate registry hash `15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3` match the baseline.
- `.venv/bin/pytest -q tests/test_narrative_explorer_*.py tests/canonical_library/test_source_locks.py tests/canonical_library/test_manifest.py` — PASS: 638 passed, 13 subtests passed.
- Targeted passage projections — PASS for all three exact evidence IDs. Each v1 projection contains its precise passage anchor, qualification fields, and resolved bibliography with source locator.
- Local Markdown-link check — PASS: all 3 relative links resolve across the 4 ED-1B Markdown files. `git diff --check` — PASS.
