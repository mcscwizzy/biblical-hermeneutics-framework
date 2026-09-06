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
included. The pre-hardening observed Python bundle was approximately 245 MB;
the local certified runtime corpus is approximately 3.2 MB. A Vercel CLI is
not installed or linked in this environment, so remote deployment/build status
must be confirmed by the next authorized preview build.

The repository has no verified programmatic branch-protection result in this
environment. Automation should continue through feature branches and pull
requests, with direct pushes to `master` disabled in GitHub branch protection.
No administrative GitHub change is claimed here.

Known test caveat: the Vercel subprocess smoke tests cannot run in this
environment because `/usr/bin/python3` lacks the project FastAPI/httpx
dependencies; the project interpreter’s focused runtime suite passes. Any
remaining failures must be classified in the final test report rather than
hidden by weakening assertions.

Machine-readable audit artifacts are in `docs/commentary-v1.1-release/`:

- `storage-classification.json`
- `certified-runtime-reconciliation.json`
- `vercel-packaging-audit.json`
- `release-integrity.json`
- `branch-cleanup-audit.json`

Commentary prose regeneration during release hardening: **0**.
