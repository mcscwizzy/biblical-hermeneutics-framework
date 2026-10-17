# NE-7R2 performance and local acceptance

## Environment and method

- Linux, Python 3.12, Firefox 155.0.1, geckodriver 0.37.1.
- CKL backend: verified read-only SQLite at the original local `.bhf/ckl.sqlite`;
  source JSON from `framework/canonical_library`.
- Protected study database: original local `study.sqlite`, with
  `BHF_STUDY_DB_READ_ONLY=1`. Browser pack tests use disposable Firefox
  storage. Offline UI records are created only in that disposable profile.
- Process-cold means a new Python/app process. The filesystem page cache could
  not be cleared; process-cold timings may have warm OS pages. Genesis 2:8
  used three fresh processes per backend and three warm requests per process
  (n=3 cold and n=9 warm). Maps used three sequential requests in one fresh
  process. These are observed samples, not percentile estimates.
- Browser timings include local Firefox, loopback transfer, and rendering. No
  hosted deployment was tested.

## Matched and follow-up measurements

| Workload | NE-7R1 | NE-7R2 local | Requests / identity |
|---|---:|---:|---|
| Genesis 2:8, process-cold SQLite | 1,912.8 ms | 9,892 ms (9,872–9,917; n=3) | 3 fresh processes; 17 items; 131,228 B; same SHA |
| Genesis 2:8, warm SQLite | 1,502.8 ms | 1,609 ms (1,555–1,646; n=9) | 3 warm requests per process; same bytes and SHA |
| Genesis 2:8, process-cold JSON fallback | 30,473.2 ms | 30,586 ms (30,457–30,785; n=3) | explicit JSON backend; 131,228 B; same SHA |
| Genesis 2:8, warm JSON fallback | 1,515.2 ms | 1,665 ms (1,605–1,809; n=9) | 3 warm requests per process; same bytes and SHA |
| Companion + Explorer, concurrent first use | 957 ms direct lookup in NE-7R1 | 10,526.8 ms FastAPI wall | 2 HTTP 200s; 102,915 B and 131,228 B |
| Jerusalem search, first / later API calls | 2,314 / 2,350 ms direct in NE-7R1 | 635 ms first; 617 ms median later (578–617; n=2) | default UI query; 1,681 B; same SHA |
| Jerusalem search in Firefox | 4.86 s | 588.8 ms response; rendered in acceptance run | same 1,681 B and response SHA |
| John 2 compact Maps | 243.5 / 184.5 ms direct in NE-7R1 | 271 ms median (269–361; n=3); 3.20 s in full Firefox run | 69 markers; 187,007 B; same SHA |
| Selected-place detail (`openbible-aac6cda`) | 188.4 ms | 287.2 ms median (286.6–287.2; n=3) | 32,842 B, on demand; same SHA |
| Reader open, optional pack absent | — | John 1 response consumed at about 3.0 s | no `/api/offline/packs/` request; optional install disabled |
| Reader with Study pack present | — | 589 ms navigation timing in focused probe | reload rendered John 1; 637 objects persisted |
| Manual Study pack installation | — | 11.58 s focused probe; 16.34 s in full browser run | 637 objects; 15,099,413 B response |

Process-cold means a fresh local app process with an uninitialized provider;
the host filesystem page cache could not be cleared, so the figures do not
represent cold physical storage. SQLite cold first use is slower than NE-7R1
because the runtime now also compares the canonical fingerprint of all
schema-validated source records with the SQLite index metadata. The new
attestation took 4,567 ms in a process-cold direct measurement; complete
provider initialization took 8,139 ms in that direct probe. SQLite API cold
latency had a 9,892 ms median across three processes; nine warm calls had a
1,609 ms median. The existing SQLite integrity scan was
3,069 ms in the prior detailed profile and remains complete. The API's
earlier single run measured 9,521 ms cold and 1,149 ms warm. The repeated
samples give the representative values in the table. This work does not claim
a lower SQLite cold wall time; the provider removes duplicate initialization
and now retains every required integrity comparison.

Each of the three process-cold SQLite probes constructed one repository, ran one full
index integrity verification, validated one source manifest and one source
inventory, and computed one content signature and canonical inventory
fingerprint. The source fingerprint computation took 4.57 s; complete provider
initialization took 8.14 s in the detailed probe. Each API request returned the same 131,228-byte
Genesis 2:8 body as JSON fallback, with SHA-256
`31c61da20dbbcd655b1ec949115ad6ecb44e54ee8052bb14b3a5e5f8c7a5155e`. The
concurrent Companion + Explorer probe had one repository construction, one
full integrity verification, one inventory verification and fingerprint
comparison, one content signature computation, one canonical fingerprint
computation, and one single-flight waiter. See
[`02-concurrency-and-integrity.md`](02-concurrency-and-integrity.md) for
response hashes and exact verification counts.

Firefox John 2 compact and selected-place payload hashes are listed in
[`03-maps-performance-analysis.md`](03-maps-performance-analysis.md). Maps
search stage results and the retained 21.7 MB explicit legacy response are also
documented there.

## Regression results recorded in this transaction

- Latest shared provider and consumer tests: **15 passed**, including canonical
  fingerprint mismatch rejection, source-change invalidation, retry behavior,
  explicit fallback policy, and Vercel fail-closed behavior. SQLite projection
  parity, storage, and read-only tests: **13 passed**.
- Narrative Explorer API/projection, Companion Context, Maps matching, and
  evidence graph: **135 passed, 8 skipped, 3 subtests passed**. The API group
  ran before the two final provider-only policy tests; those are covered in
  the latest 15-test provider and consumer run above.
- Vercel index/startup, `tests/test_web_app.py`, archaeology offline, and
  optional-pack runtime: **102 passed, 55 skipped, 4 subtests passed**, with
  one pre-existing Vercel packaging assertion failure described below.
- General Firefox reader smoke: **8 passed**. Geography and offline-pack
  Firefox acceptance: **10 passed**.
- Frontend Node tests: **13 passed, 0 failed**.
- `tests/gui/test_pwa_offline.py`: 3 skipped because the optional
  `webdriver_manager` dependency is absent.
- Compatibility group: **181 passed, 15 known failures, 8 skipped, 11
  subtests passed**. The exact 15 failed test identities match the NE-7R1
  triage; rights, provenance, Isaiah 13 identity, frozen prompt hash, and
  source synthesis counts were not changed.

The additional failure is
`test_vercel_ignore_preserves_required_runtime_paths`. It fails because the
unchanged `.vercelignore` contains `.bhf-data/**`, which the assertion treats
as excluding the packaged Commentary v1.1 runtime files. Both the ignore file
and this test are byte-identical to NE-7R1, and the task boundary forbids
changing Vercel configuration. This packaging mismatch is recorded as an
independent hosted-release issue; it did not affect local reader acceptance.

## Local release boundary

The local worktree remains based on NE-7R1 commit
`4c86fc624deb515c8b42f4d6bdfbaa7fdcb0c1a2`. The installed pack and its 637
local CKL objects remain readable through IndexedDB after the server stops;
notes, highlights, and user settings also persist. Full offline navigation
reload remains pending because Firefox WebDriver reaches `about:neterror` for
that probe, and the Chrome PWA suite skips without `webdriver_manager`. Hosted
SQLite verification, hosted Tyndale provisioning, the Vercel 317.82 MB function
size blocker, true 390 px layout acceptance, and spoken screen-reader
acceptance remain independent release gates.

No push, merge, Vercel configuration change, environment-variable change, or
deployment was performed.
