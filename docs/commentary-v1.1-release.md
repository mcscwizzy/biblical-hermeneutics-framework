# Commentary v1.1 release engineering report

Commentary v1.1 is certified and ready for application release hardening. The
scaled pipeline finished at `CORPUS_COMPLETE` with 935 eligible chapters,
935 eligible finalized chapters, 948 protected finalized artifacts, zero
quarantines, zero data gaps, zero reader-unfriendly outputs, and clean CKL
integrity. Protected fingerprints validate and CKL records were not changed.

The release population is derived from the evidence-supported low-information
audit artifact; the runtime publisher consumes only protected certified
artifacts. It rejects missing or changed fingerprints, duplicate chapter
identities, invalid schemas, unsupported availability, and missing evidence
hashes. Publication is atomic, deterministic, LLM-free, and does not mutate
CKL or historical batch artifacts. Bounded remediation was limited to the
certified per-chapter policy, and persistent quarantine recovery state remains
in the audit workspace.

The canonical packaged runtime root is
`.bhf-data/bhf-commentary-v1.1`, with manifest
`.bhf-data/bhf-commentary-v1.1/commentary-v1.1-manifest.json`. It contains 935
chapter artifacts and corpus fingerprint
`9df456a3a22003587347cc0a78a9de5ca292e1d9554c4af3fc591207dd87e5db`.
The web reader resolves this root for local and Vercel execution. Candidate,
Terra, preflight, remediation, and certification workspaces remain in Git for
reproducibility but are not runtime dependencies.

Vercel function configuration excludes
`.bhf-data/bhf-commentary-candidates/**`; the certified runtime corpus remains
included. The previous reported function bundle was approximately 388.83 MB
raw and 397.27 MB optimized against a 225 MB limit. The local certified runtime
corpus is approximately 3.2 MB. External release evidence for commit
`dd62adf` reports a Vercel preview at `READY` with the application root
returning HTTP 200 and `commentaryRelease: commentary-v1.1`; exact optimized
post-hardening size was not exposed in the available deployment evidence.

The repository has no verified programmatic branch-protection result in this
environment. Automation should continue through feature branches and pull
requests, with direct pushes to `master` disabled in GitHub branch protection.
No administrative GitHub change is claimed here.

Known test caveats: the Vercel subprocess smoke tests cannot run with
`/usr/bin/python3` because that interpreter lacks the project FastAPI/httpx
dependencies; the dependency-complete focused runtime suite passes. The broad
Commentary suite reports 230 passes and three historical Terra fixture
failures: the canary lock for Numbers 16 and the Batch 003 lock assumptions
are stale against current evidence. The broad web-app suite exceeded its
bounded 180-second check while running a canonical-editor test; focused
commentary web checks pass. These are recorded rather than hidden by
weakening assertions.

Machine-readable audit artifacts are in `docs/commentary-v1.1-release/`:

- `storage-classification.json`
- `certified-runtime-reconciliation.json`
- `vercel-packaging-audit.json`
- `release-integrity.json`
- `branch-cleanup-audit.json`

Commentary prose regeneration during release hardening: **0**.
