# NE-11E5: Companion history and consolidated final gates

## Browser Back restoration

The original regression entered a selected passage in `peek`, opened Explore to reach the `study` overview, and opened Maps. Back should close Maps while leaving the overview in `study`; a second Back should return to `peek`. Maps had become visible before its history entry was pushed, so Back could skip the overview and return to `peek` too early.

Commit `b8828d3f` records the Maps history entry synchronously after showing the resource. The exact browser test passes with Back and Forward, and confirms the selected Scripture reference remains unchanged. The companion browser test for translation comparison Back navigation and focus also passes. The frontend history tests preserve the Narrative Explorer trail, its origin selection, and route-handoff history behavior.

## Consolidated phase results

Counts below are per test command and can overlap; they are not additive. **FAIL** and **BLOCKED** identify the remaining CKL provenance issue, not a retrieval or Companion regression.

| Phase | Original issue | Final result |
| --- | --- | --- |
| **E1 — Structured output/provider validation** | Six presentation/adapter contract failures | **PASS:** 133 structured-output, response parsing, pipeline, provider, bundle, and integrity tests. |
| **E2 — CKL governance** | The reviewed `genesis-abraham-call-covenant-context` object has no authoritative generator identity | **FAIL / BLOCKED:** the full integrity batch passed 571 tests and failed one manifest assertion; the manifest suite independently reproduced 7 passes and that same 1 failure. No provenance or CKL content was fabricated. |
| **E3 — Release-path sanitization** | The scanner initially flagged 24 retained paths | **PASS:** sanitizer and Vercel startup tests, 7 passed; Vercel package/provider tests, 19 passed. The sanitizer distinguishes machine paths from scholarly URLs. |
| **E4 — Retrieval remediation** | Three First Corinthians ranking failures and three golden-query failures | **PASS:** 44 retrieval-matrix tests and 215 subtests, including 17 retrieval-service tests. JSON/SQLite storage and alias parity passes 27 tests and 4 subtests; question-driven entity disambiguation passes 7 tests. Evidence, scores, and contract decisions are in [the E4 diagnostic](04-first-corinthians-retrieval.md). |
| **E5 — Companion history** | First Back returned to `peek` instead of unwinding Maps to the `study` overview | **PASS:** 2 browser Back/focus tests and all 14 frontend tests. Back, Forward, selection, keyboard focus, and Narrative Explorer origin history checks pass. |

Additional consolidated checks:

- `python3 tools/validate.py framework/` — **PASS**, 94 framework modules.
- `tools/ckl_validate.py --root framework/canonical_library --json` — **PASS**, 687 valid objects, 0 validation errors, and 14 existing warnings.
- Source locks, schema, Scripture-reference integrity, NE-9C curation, NE-10 passage identity, Narrative Explorer API/projection, and parity batch — **571 passed, 1 failed**; the sole failure is the E2 manifest assertion above. A separate Narrative Explorer/NE-9C/NE-10 integration batch passed **113 tests**.
- `npm test` — **PASS**, 14 frontend tests.
- Release-path, packaging, and startup verification — **PASS**, 7 sanitizer/startup tests plus 19 packaging/provider tests.
- Full 2 Corinthians, Galatians, Romans, and Philippians retrieval suites — **PASS**, 32 tests and 608 subtests. The Romans 11:29 query remains specialist-first because it names no book; the explicit Philippians 1:27 query ranks the book above the homonymous city.
- The complete retrieval matrix includes First Corinthians, golden and claim-level golden queries, precision retrieval, query analysis, named and implicit book references, and retrieval-service controls. The JSON/SQLite alias tests cover Abram → Abraham.
- Question-driven retrieval entity-disambiguation controls — **PASS**, 7 tests. The explicit Philippians 1:27 book/place collision and implicit Pauline topic controls remain separate.
- `git diff --check` and local Markdown-link validation — **PASS**.

## Original failure register

| Original failure | Final result |
| --- | --- |
| Who are weaker members and what is conscience? | **PASS, contract clarified:** the query combines 1 Cor 8 and 1 Cor 12 without naming the book; `1-corinthians` must remain within five, not rank first over the partial conscience match. |
| What do weakness, illness, and death mean at the Corinthian meal? | **PASS, contract clarified:** the direct meal/conscience record leads with 1 Cor 11:17–34 evidence; `1-corinthians` remains retrievable. “Corinthian meal” is not treated as an explicit book-name constraint. |
| What does one body and many members mean? | **PASS, contract clarified:** the passage-focused 1 Cor 12 Spirit/gifts source leads; no book-first constraint is imposed on the implicit query. |
| What is the significance of Joseph's bones? | **PASS, evidence correction:** the Gen 50:24–26 bone-oath source is inserted after primary subject `joseph`; the expected sequence now distinguishes explanation from burial location and broad event matches. |
| What does baptism have to do with new creation? | **PASS, contract clarified:** the first four expected records remain; `new-jerusalem` replaces the unsupported fifth-place `image-of-god-theme`, based on the explicit new-creation relationship. |
| temple symbol | **PASS, contract clarified:** the exact `temple-symbol` anchor leads, followed by `temple`, `new-temple-theme`, the contextual `tabernacle`, and `second-temple-administration`. |
| Browser Back after opening Maps from the Companion overview | **PASS:** Maps history is recorded when the resource opens, so Back restores `study` before `peek` and preserves the selected Scripture. |

The retrieval changes did not lower relevance thresholds, create query-specific ranking rules, or edit CKL content. The golden fixture changes are documented evidence-contract corrections, not silent relaxations.

## Release status and remaining review

**NOT READY FOR RELEASE.** E2 needs a governance owner to establish the actual generator identity for `genesis-abraham-call-covenant-context` from authoritative records, or to decide a truthful schema-compliant treatment that preserves the global provenance invariant. Its current `in_review` status and empty `generated_by` value must not be guessed or filled with the commit author. The exact outstanding assertion is `CanonicalInventoryTests.test_all_inventory_json_files_validate_and_receive_governance_defaults` in `tests/canonical_library/test_manifest.py`.

**SKIPPED:** no Vercel Preview was built because deployment was explicitly out of scope; the checked-in packaging and startup tests pass. A manual spoken screen-reader run was not performed; the automated keyboard-focus checks passed. Do not treat either skipped acceptance activity as verified.

The five phase commits remain on `fix/ne11e-consolidated-release-hardening`; the SQLite fuzzy person-name correction `25d2e42d` remains in history. This branch has not been merged or deployed, and no pull request was opened.

## Manual spoken screen-reader protocol

With a supported screen reader and keyboard, navigate headings in the reader and Companion; select a passage and open its discovery. Confirm that the action is announced as “Explore this connection,” and that selecting a route announces its selection. Navigate to a related passage and confirm its name and context are spoken. Use Escape and Return to leave the detail, checking that focus returns to the invoking control and its name is announced. Record browser, screen reader, platform, observed announcements and any failures.
