# Historical decisions index

This index points to immutable source history and a few maintained decision
records. It keeps major architecture and research milestones discoverable
without treating old reports or pipeline instructions as current operations.

| Decision | Git reference | Maintained record |
|---|---|---|
| Commentary v1.0 release identity | `commentary-v1.0` — `23ac9076c758137566e88066dc7ecd2d8a2f9ee6` | Immutable release tag |
| Commentary v1.0.1 release identity | `commentary-v1.0.1` — `4e4cb54c90766d40d3f75f1af6a7e47e0246edb1` | Immutable release tag |
| Commentary v1.1 release identity | `commentary-v1.1` — `fdd0cbe11ef8f0dcdced302caf4c856004d48bfa` | Immutable release tag |
| Commentary v1.2 frozen source release | `commentary-v1.2` — `aabca7e0c0e20ca8cc293be60b28375e163a259d`; freeze input `f02122eed9642f173e2be3ad39ac5b979a23b898` | [Pinned freeze workflow](../../.github/workflows/commentary-v1.2-freeze.yml) checks out the immutable source tree |
| Retire generated BHF Commentary and keep Tyndale | NE7R3 merge `551a998f5c40d6cb4d5e8a1f41db1bfe8f307096`; retirement implementation `7a79f73d7e78490ce7082940ca7f9b551d6bd828` | [NE7R3 dependency audit](../narrative-explorer/ne7r3/01-commentary-dependency-audit.md), [CKL fingerprint investigation](../narrative-explorer/ne7r3/02-ckl-fingerprint-investigation.md), [reader regressions](../narrative-explorer/ne7r3/04-reader-regression-results.md) |
| NE-9C scholarly relationship curation | Acceptance `0e88d104d66ff70730645387cc0d116727e2ac9e`; merge `c3aba86ec82cfe014c4f596a3c8bb136f2bb8fea` | [NE-9C final report](../narrative-explorer/ne9c-bulk-curation/final-report.md), decision and wave records |
| NE-10 passage bridge acceptance | Acceptance `21880d8cb6dcac493c13d90ec74c58b6bfb8be87`; merged master `4260e1efdac3d2795b8599b22d837cbb8267e74d` | [NE-10 audit](../narrative-explorer/ne10-evidence-discovery-audit.md), [results](../narrative-explorer/ne10-results.md) |
| Historical Vercel package-size investigation | Report snapshot in Git through `dd62adf70a0461a74d0769bf46f77b8db191c068` | [Archived Vercel bundle notes](../narrative-explorer/vercel-bundle/README.md) |

## Methodology and classification

CKL remains the authoritative, human-reviewed research source. Preserve its
evidence assertions, source identity, provenance, uncertainty, and typed
relationship decisions. The maintained [CKL guide](../canonical_knowledge_library.md)
and [Neutrality Charter](../../GOVERNANCE.md#1-neutrality-charter-the-constitution)
describe the current authoring and interpretation boundaries. NE-9C and NE-10
records are read-only runtime inputs; follow their acceptance reports for the
scope and rationale of those decisions.

Old generated Commentary source trees, prompts, batch reports, and intermediate
artifacts remain accessible through the tags and Git history above. They were
not copied to another archive directory during cleanup. Historical reports
describe their recorded checkpoint and should not be used as a current runtime
or deployment guide.
