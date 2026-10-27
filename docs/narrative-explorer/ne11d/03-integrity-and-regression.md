# NE-11D integrity and regression results

## Protected research baselines

| Check | Result |
|---|---|
| CKL inventory | 687 objects; fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` |
| CKL object/source tree | `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766` |
| CKL validation | 687 valid objects, zero errors, 14 existing warnings |
| NE-10 | 44 verified bridge identities; 7 held candidates remain held |
| NE-9C | 3,925 reviewed: 408 curated, 1,895 held, 1,622 excluded |
| Worktree | No CKL, source-lock, registry, or curation input was changed |

The current NE-9C curation tree and active identity fingerprints remain `691c9201d50eb0cceccac1b1a6d1beaa58f65b96cac54241cc856c8e2bc87a31` and `528f6a36dd729a90d16beaa023400bb80821f021f25417076d3b8f831e016dd0`. NE-10 registry tree, active-identity, and held-candidate fingerprints remain `6dfe864406a2b28fa2ec7c997f7cb66decabf645f483706d25c76058512649b6`, `c0c329dd1002a5519a1bc5301975b7821a81802b98eec6ebd837e473c97e919f`, and `ad1a754affefdcb5bfe7aff0b7c059d0624521b85ecd42c7cda7f870656608d3`.

`python3 -m framework.canonical_library --root framework/canonical_library --json` and `python3 tools/ckl_validate.py --root framework/canonical_library --json` completed without errors. The NE-9C validator passed with the counts above. NE-10 integrity/projection coverage validated all 44 bridges against exact CKL records and attached sources. Current projection checks retained Genesis/John and Jonah/Matthew support identities, excluded the held Psalm 110 / Acts 2 candidate, and returned no confirmed Psalm 22 / Mark 15 or Deuteronomy 32 / Psalm 82 handoff. Comparative evidence, later reception, source identities, and uncertainty remained distinct in the projection and serialized route details.

## Regression matrix

- `npm test`: 14 frontend test files passed. Coverage includes discovery identity matching, wrong parent/kind/local ID, source-only and topic-only matches, duplicate route IDs, incomplete/failed projection, flag-off behavior, stale-selection abort/invalidation, routing/history, Maps focus, Locations paging, and offline worker cache/error behavior. Separate automated cases for two rapid activations of different connections and closing Companion during pending verification were not found; those cases remain unverified.
- Targeted backend/package/regression suite: **691 passed, 8 skipped, 11 subtests passed**. It included Study Companion, Narrative Explorer projection/API/passage/curation, presentation evidence integrity, Locations, Maps/Archaeology, Tyndale Open Study Notes, retired Commentary 410 behavior, Vercel startup/packaging, and CKL index tests.
- CKL source-lock, Scripture-reference, typed-evidence, and schema suite: **135 passed**.
- Selenium regression `test_companion_discovery_handoff_highlights_verified_route_and_returns_to_origin`: **1 passed, 13 deselected**. This test injects a fixture Companion context, so it is supporting UI regression evidence only, not actual CKL browser acceptance.
- Actual CKL-backed Firefox Genesis handoff: passed twice. Other live browser scenarios timed out and are left incomplete; see [reader acceptance](01-integrated-reader-acceptance.md).
- Offline: service-worker unit tests simulate cached-resource and network-failure cases. No genuine offline browser session, installed-pack inventory, reconnection flow, or pending-action outage was exercised. No offline availability is claimed beyond tested cache behavior.

## Baseline failures reproduced on clean merged master

The clean archive at `2ea868abce02a47bc2fdc403d83f9d083b500cb0` reproduced each failure below with the same result as the current branch. None was introduced by NE-11C2. They remain repository CI/release issues; the governance and sanitizer gates must not be weakened.

### Presentation structured-output tests

Six failures remain:

| Test | Exact failure | Reader / deployment impact | Corrective action / release effect |
|---|---|---|---|
| `test_presentation_provider_sends_response_format_when_supported` | `AttributeError`: `CaptureAdapter` has no `presentation_response_format_capability` (`providers.py:220`) | Presentation provider test path; no observed NE-11 route impact | Repair test/provider capability contract separately; baseline CI gate remains red |
| `test_presentation_provider_omits_response_format_when_not_supported` | Same `AttributeError` | Same | Same |
| `test_response_format_includes_required_fields` | Same `AttributeError` | Same | Same |
| `test_response_format_is_strict` | Same `AttributeError` | Same | Same |
| `test_json_object_response_validation_not_weakened` | Expected `PresentationResponseParseError`; no exception raised | Structured output validation coverage | Fix validation/test contract separately; release gate remains red |
| `test_ordinary_openrouter_request_unchanged` | `NameError: ChatRequest is not defined` (test line 683) | Test code only | Fix missing test import separately; release gate remains red |

All six reproduce on clean master; introduced by NE-11: **no**. No direct reader behavior or production packaging impact was demonstrated, but the failing CI checks remain unresolved.

### CKL manifest governance

`CanonicalInventoryTests.test_all_inventory_json_files_validate_and_receive_governance_defaults` fails because the test expects at least one `generated_by` entry, but `genesis-abraham-call-covenant-context` has `review_status=in_review` and an empty `generated_by` list. The same failure occurs on clean master. This is a CKL governance/CI issue, not a reader regression; retain the record and gate unchanged. Correct through separately reviewed governance work before treating the governance gate as green.

### Release-path sanitizer

`tests/test_release_path_sanitization.py::test_release_and_audit_artifacts_contain_no_machine_absolute_paths` reports the same **24** paths on clean master and this branch. No new violation was added by NE-11C2 or these reports. Exact current violations:

1. `docs/narrative-explorer/ne7r1/02-cold-initialization-profile.md`
2. `docs/narrative-explorer/ne7r1/04-integration-regression-results.md`
3. `docs/narrative-explorer/coverage-audit/methodology-validation.json`
4. `docs/narrative-explorer/ne6/04-map-focus-and-database-validation.md`
5. `docs/narrative-explorer/ne7/06-performance-and-regressions.md`
6. `docs/superpowers/plans/2026-09-16-assistant-handoff.md`
7. `.bhf-data/bhf-commentary-candidates/genesis-g0-evidence-census/genesis-evidence-census.json`
8. `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-existing-evidence-audit.json`
9. `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-final-ckl-identities.json`
10. `.bhf-data/bhf-commentary-candidates/genesis-g5b-jacob-esau-return-evidence-expansion/g5b-runtime-db-preparation-verification.json`
11. `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/g4a-final-ckl-identities.json`
12. `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/g4a-source-lock.json`
13. `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/g4a-candidate-evidence.json`
14. `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/g4a-validation-report.json`
15. `.bhf-data/bhf-commentary-candidates/genesis-g4b-abraham-late-cycle-evidence-expansion/g4b-existing-evidence-audit.json`
16. `.bhf-data/bhf-commentary-candidates/genesis-g4b-abraham-late-cycle-evidence-expansion/g4b-final-ckl-identities.json`
17. `.bhf-data/bhf-commentary-candidates/genesis-g1-primeval-origins-evidence-expansion/g1-validation-report.json`
18. `.bhf-data/bhf-commentary-candidates/genesis-g6a-joseph-descent-testing-evidence-expansion/g6a-joseph-descent-testing-evidence-plan.json`
19. `.bhf-data/bhf-commentary-candidates/genesis-g6a-joseph-descent-testing-evidence-expansion/g6a-validation-report.json`
20. `.bhf-data/bhf-commentary-candidates/genesis-g6a-joseph-descent-testing-evidence-expansion/g6a-existing-evidence-audit.json`
21. `.bhf-data/bhf-commentary-candidates/genesis-g5a-isaac-jacob-transition-evidence-expansion/g5a-runtime-db-preparation-verification.json`
22. `.bhf-data/bhf-commentary-candidates/genesis-g5a-isaac-jacob-transition-evidence-expansion/g5a-final-ckl-identities.json`
23. `.bhf-data/bhf-commentary-candidates/genesis-g6b-joseph-reconciliation-conclusion-evidence-expansion/g6b-existing-evidence-audit.json`
24. `.bhf-data/bhf-commentary-candidates/genesis-g4a-abraham-call-covenant-evidence-expansion/staging/new-object.json`

These baseline failures block an all-green repository release gate even though the targeted NE-11 behavior tests pass.
