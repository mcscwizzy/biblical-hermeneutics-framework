# Commentary v1.2 freeze

Commentary v1.2 is immutable. Future content changes require a new release
version. Unexpected v1.2 identity drift is a release failure; expected hashes
are never updated merely to make verification pass.

## Final corpus

| State | Chapters |
| --- | ---: |
| Published | 972 |
| Source-limited | 185 |
| Model-rejected | 26 |
| Quality-review | 6 |
| **Canonical total** | **1,189** |

Missing chapters, orphan artifacts, duplicate identities, and checksum
conflicts are all zero. The 185 source-limited, 26 model-rejected, and 6
quality-review states are intentional terminal states in the release and are
not hidden or retried.

## Identity

- Promotion baseline: `71f86e18b7d918020884f89027a83ab1b50f6b80`
- Manifest SHA-256: `aad968530b371ac05de3529c3f0ac0a59afebc66bfaa21c2fcf4ca6306684c5b`
- Chapter inventory identity: `17c2ecd7eb2ee519b9dce332eb370d97cea42ce75fa0eb5537729c424f4990ae`
- Source-lineage identity: `e8af58131e066def98a2`
- Package checksum-root identity: `ae31de2fe50c0435387995dd4110579ff2b68ae9f59f9dd1b9f5afc55cb785eb`
- Release descriptor: [`commentary-v1.2-release.json`](commentary-v1.2-release.json)

The descriptor's `freeze_git_sha` records the promotion baseline that was
frozen. The immutable tag target is the final freeze commit reported by the
release pass; Git cannot embed a commit's own SHA inside that same commit.

Renderer contract: corpus result v1, renderer input v1, GPT-5.6 Terra at high
effort, prompt 1.8. Output contract: runtime release checksums v2.

## Operational safeguards

- No commentary generation occurred during promotion or freeze.
- Normal v1.2 `prepare`, `run`, `render_local`, and `finalize` operations fail
  closed after the descriptor marks the release frozen.
- The frozen verifier reads only the packaged release and canonical inventory;
  candidate/corpus-runner state cannot override it.
- Provider configuration is not required to read published commentary or
  represent terminal unavailable states.
- Historical 75 artifacts remain byte-for-byte protected by their existing
  validation contracts and are not rewritten.

Use `python tools/commentary_v12_freeze.py verify` for deterministic release
verification. Use `python tools/commentary_v12_rebaseline_lineage.py verify`
for current source-lineage verification. Any failure is a freeze blocker.
