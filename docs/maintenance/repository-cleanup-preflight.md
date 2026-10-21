# Repository cleanup preflight

## Baseline and prerequisite

- Repository: `mcscwizzy/biblical-hermeneutics-framework`
- Confirmed NE-10 merged in PR #42; base is `4260e1efdac3d2795b8599b22d837cbb8267e74d` on fetched `origin/master`.
- Isolated branch: `chore/bhf-repository-modernization`.
- The branch was clean when created. The inventory and this report are the only audit files added before cleanup; the internal execution plan is untracked and will not be part of the deliverable.
- Baseline: 19,993 tracked files; 661,068,202 tracked content bytes (630.44 MiB). `.bhf-data`: 18,021 files; 500,678,989 bytes (477.48 MiB). Relationship inventory CSV: 53,638,723 bytes.
- Git objects: 4,308 loose objects / 47.31 MiB; 34,995 packed objects / 91.50 MiB pack size. Tree cleanup does not rewrite historical objects.

## Baseline checks

- `python3 tools/validate.py framework/`: PASS, 94 modules.
- `node --test tests/frontend/*.test.js`: PASS, 12/12.
- Active CI-focused pytest set (`test_commentary_retirement`, Narrative Explorer UI config, packaging, CKL manifest count, release): PASS, 17 tests.
- `python -m build`: PASS after declared build/dev dependencies were installed in the isolated `.venv`; initial attempt was blocked by unavailable package-index DNS. Existing setuptools license metadata deprecation warnings were emitted.
- A full `pytest -q` baseline process produced partial progress but its terminal session expired before a final summary could be recovered. It is recorded as inconclusive, not passing.

## Dependency and retention decisions

The file-level decisions are in [repository-cleanup-inventory.csv](repository-cleanup-inventory.csv). Basis IDs map to these verified boundaries:

- **K01 — current source and data:** default retention for current BHF runtime, CKL source objects/schema/manifests/curations, tests not specifically retired, active packaging, governance, attribution, licenses, and documentation. CKL methodology and hermeneutical classification rules remain authoritative.
- **K02 — Genesis evidence:** keep the complete G0 census and G1–G6C evidence-expansion directories. Source locks, manifests, replay inputs, reports, and corresponding isolation tests retain CKL research decisions.
- **K03 — promotion attestation:** preserve `genesis1-corrective-refresh/operator-promotion-authorization-attestation.json` as an authorization record.
- **K04 — active Tyndale and retirement contracts:** preserve the Tyndale service/CLI/API tests, stable retired-route 410 checks, and Tyndale reader search test. `framework.commentary` contains both active Tyndale functions and retired BHF generation modules; it must be pruned selectively.
- **K05 — CKL content assertion:** keep the structured-claims test and change it to read CKL records directly rather than importing an obsolete Commentary enrichment utility.
- **H01 — frozen release reference:** retain the v1.2 freeze workflow. It checks out immutable commit `f02122eed9642f173e2be3ad39ac5b979a23b898`; that Git object tree contains its original code and verification inputs. Current master does not need to ship those inputs in runtime packages.
- **H02 — retirement history:** keep the NE7R3 retirement acceptance/rationale and CKL/NE-9C/NE-10 methodology. Other generation reports can be consolidated to a short history index while their full source remains reachable in Git history and release tags.
- **I01 — branch-triggered Sol handoff:** retain the exact renderer-qualification-v1 `chatgpt-handoff` subtree and `export-sol-qualification-artifact.yml` pending external verification. The remote branch reference could not be checked because GitHub DNS was unavailable. Do not remove or rewrite this input on inference alone.
- **R01 — generated artifact trees:** other `.bhf-data/bhf-commentary*` data are retired generation outputs and candidates. Their source and provenance remain available from the base commit and immutable Commentary release tags; none are CKL authority. The explicit G0–G6C, attestation, and I01 exceptions above are preserved.
- **R02–R06 — retired generation implementation:** old root generation status/resume files, generated reader package, generated modules under `framework.commentary`, generator experiments, and their generation-only tests have no active runtime or product consumers after the runtime edges are removed. Keep `framework.commentary` Tyndale modules, the Tyndale CLI/API/UI/reader, and 410 compatibility routes.
- **C01 — redundant generation records:** consolidate the 84-page/file generated Commentary documentation set into a historical index; retain NE7R3 decision and CKL research methodology.
- **R07 — reproducible export:** `scripts/audit_ckl_connection_coverage.py` regenerated the CSV byte-for-byte to `/tmp` before any deletion: 53,097 data rows, 53,638,723 bytes, SHA-256 `b03b5ce267e415b997e6d1cfbe8fe69049731b3a4b10262f1e77d8e395aedef4`; CKL count 687, canonical inventory fingerprint `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6`, manifest SHA-256 `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4`, CKL tree SHA-256 `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`. Retain the exporter and methodology, remove only the checked-in derived CSV after another verification.
- **R08 — stale generation verification:** remaining Luna/Terra batch tests, CKL scope census code/tests, the pre-NE7R3 transition plan, and old Vercel bundle audit files depended on or described retired generation. Their source and outputs are historical Git material; current CKL and Narrative Explorer checks remain active.

## Runtime and build graph

- Narrative Explorer consumes authoritative CKL objects and read-only NE-9C/NE-10 curation/bridge records under `framework/canonical_library`; preserve those records byte-for-byte.
- Tyndale is separate from generated BHF Commentary: `framework.commentary` schema/importer/repository/service/evidence provider/CLI and `bhf_web.routes.commentary` back the Tyndale reader and Ask BHF evidence retrieval. The Tyndale database build uses a pinned source digest in `framework.commentary.vercel_build`; Docker builds the seed DB; Vercel explicitly packages the DB resource.
- `bhf_web.routes.retired_commentary` and retirement acceptance tests maintain HTTP 410 compatibility. `bhf_web.services.commentary_coverage` is a retired generated-corpus endpoint and can be removed after source references and tests are updated.
- The active Validate workflow includes package, CKL/release, Narrative Explorer configuration, and retirement gates. Preserve its checks.
- `pyproject.toml`, `MANIFEST.in`, Docker, Vercel, and offline pack inputs must be checked against active resources after the source/data cleanup. `.bhf-data` is not a runtime input to Docker/Vercel; the Sol workflow exception is an artifact export input only.
- The freeze workflow is a historical CI job pinned to an immutable ref. The Sol export trigger remains unresolved due unavailable remote access.

## Hash and license boundaries

- The CKL source-object tree, schema, manifest, source-lock files, NE-9C and NE-10 registries/held-candidate records, Bible/lexical data, licenses, and attribution are protected inputs. Capture baseline hashes before data deletion and compare afterward.
- Historical Commentary identity and signed/frozen source references remain in Git tags and immutable commit ancestry; do not rewrite history. The current branch is based on the commit that contains the retired artifacts, so their Git objects remain reachable.
- Retained Tyndale attribution and licensing files remain part of runtime/package verification.

## Baseline inventory disposition totals

The inventory has exactly one entry for each baseline tracked file (19,993 rows, excluding its header). Applying the documented file/path decisions produces:

| Classification | Files | Baseline bytes | Decision |
| --- | ---: | ---: | --- |
| KEEP | 1,842 | 130,247,549 | Retain in the current tree |
| RETIRE | 17,929 | 527,989,649 | Remove after source/dependency updates; Git history retains the baseline |
| CONSOLIDATE | 85 | 829,419 | Replace redundant generation documentation with maintained current references |
| HISTORICAL | 9 | 117,501 | Retain retirement rationale and pinned freeze reference |
| INVESTIGATE | 128 | 1,884,084 | Retain while the Sol artifact workflow's branch trigger remains unverified |

These are baseline source-tree byte totals, not compressed Git object sizes. The derived CSV is separately classified RETIRE and verified by the reproducibility check above. Retired code/data categories are not deleted until their active consumers and preservation references are checked.

## Inventory refinement before source changes

The initial filename pass had left several generation-only test and diagnostic filenames classified as KEEP because they did not use the common `test_commentary_`/`tools/commentary_` prefixes. Before source deletion, the inventory was refined to classify the generated chapter-commentary, dense-reader, reader-projection, renderer-presentation, Transaction C3, and commentary-consolidation diagnostic tests/tools as RETIRE. `tests/test_ckl_coverage_report.py` and `tools/ckl_coverage_report.py` remain KEEP as CKL development tooling; the tool was decoupled from the retired availability classifier while preserving its report behavior. Genesis G0–G6 evidence-isolation tests remain KEEP and were refactored only where they called generated Commentary synthesis APIs.

The final path-level pass also identified the generated chapter-commentary, dense-reader, reader-projection, provenance-binding, and renderer-presentation tests, plus the old final-four Commentary artifact builder. Those are now classified RETIRE. The G0 census builder is HISTORICAL: its committed outputs and decision record stay in the protected G0 directory, and the generator remains recoverable at the audited base commit.

## Post-refinement dependency sweep

After the first source removal, a focused repository-wide search found remaining tests and a CKL scope census tied only to the retired generation corpus, plus old Vercel bundle-size reports and a pre-NE7R3 transition plan. Their inventory rows were reclassified as R08 before removal. The refreshed baseline class counts are shown above. The active ASV Bible-data boundary regression remains, with a standalone audit helper in place of its retired Commentary enforcement import. The CKL geography dry-run tool remains and is being decoupled from its obsolete Commentary preview output.
