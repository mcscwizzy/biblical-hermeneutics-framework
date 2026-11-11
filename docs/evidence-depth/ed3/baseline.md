# ED-3 Baseline

## Repository base

- Fetched `origin/master`: `8a0bda764328f9399552e46c224c949b35c064fc`
- Branch: `audit/ed3-scholarly-integrity`, created directly from that commit.
- The fetched tip is merge commit #77, “ED-2 comprehensive evidence expansion.”
  It includes the final ED-2 release-readiness correction and draft-preview
  review disclosure. The first parent is `04eed56ece941f9efce2f7f05b3908baf0197648`.
- Worktree was clean before ED-3 files were created. No application or CKL
  source data had been changed at baseline.

## Reproduced inventory

The census ran on Python 3.12.3 and passed the NE-A1 runtime projection audit
for all 1,189 canonical chapters, 19 deterministic sample chapters, and 16
targeted service builds, with zero unmapped projected identities.

| Measure | Current | ED-2 reference | Result |
|---|---:|---:|---|
| CKL objects | 687 | 687 | Match |
| Claims | 2,329 | 2,329 | Match |
| Typed evidence items | 1,408 | 1,408 | Match |
| ED-2 additions since first parent | 99 | 99 | Match; reconciled from the object-tree diff |
| Unique source IDs in CKL bibliography entries | 2,897 | 2,897 | Match |
| Source-record occurrences | 5,348 | 5,348 | Match |
| Passage-specific chapters | 1,089 | 1,089 | Match |
| Contextual-only chapters | 56 | 56 | Match |
| Entity-only chapters | 2 | 2 | Match |
| No-eligible-material chapters | 41 | 41 | Match |
| Incomplete/unknown chapters | 1 | 1 | Match |
| Strict CKL errors / warnings | 0 / 14 | 0 / 14 | Match; warnings are inherited |
| Deep heuristic error findings / warnings | 63 / 1,093 | 63 / 1,093 | Match |
| Unresolved child-source references | 2 | 2 | Match |
| Source-support-target heuristic findings | 102 | 102 | Match |
| Bibliography IDs missing title plus detail under ED-1A screen | 558 | 558 | Match; screen failures are not automatically defects |
| IDs missing locator where the source type expects one | 1 | 1 | Match |

The 41 zero-eligible chapters reproduce the expected distribution: Numbers 4;
1 Kings 5; 2 Kings 6; 1 Chronicles 3; 2 Chronicles 9; Proverbs 7; Ezekiel 7.

The strict validator counted 687 valid objects and 14 warnings, all
`incomplete_section_status`. The deep report counted 1,408 typed evidence
records, 63 error-severity heuristic findings, and 1,093 warnings. These are
separate from strict schema errors; neither heuristic count is a scholarly
adjudication.

### Source-identity counter note

The ED-1A typed bibliography inventory reports 2,897 unique source identities.
The reused NE-A1 `source_identity_audit` subobject reports 2,898 under a
separately implemented counter. The independent ED-1A identity map used for
the expected 2,897 count also reports 2,897. ED-3 preserves both values and
their methods pending investigation; it does not force the counters to agree.

## Fingerprint and commands

The CKL inventory fingerprint from the NE-A1/ED-1A audit is:

`ba6cd8d0881c82dceb865e8cc254f89b5cfa8a9747386626c2ff4040c1eff39c`

Reproduction commands, run from the repository root:

```bash
python3 tools/ckl_validate.py --root framework/canonical_library --json \
  > /tmp/ed3-strict.json
python3 tools/ckl_report.py --root framework/canonical_library --deep --json \
  --output /tmp/ed3-deep-report.json
python3 scripts/audit_ed1a_evidence_depth.py \
  --output-dir /tmp/ed3-baseline-ed1a --study-db .bhf-data/study.sqlite
```

The last command reused the repository's local `.bhf-data/study.sqlite` only
as an input to the read-only audit. No local study data or generated census
output is committed. The census output confirmed 1,189 rows, 687 CKL objects,
and zero unmapped identities.

## Governance and review semantics inspected

- Draft evidence is stored in an object whose `content_status` is `draft` and
  `review_status` is `in_review`. The object records `reviewed_by`,
  `last_reviewed`, and `human_review_required`; child evidence inherits these
  values during Narrative Explorer projection unless a child value is explicit.
- `reviewed` and `approved` are CKL review states. The ED-2 records do not use
  either. The explicit human-review requirement remains true for all 99.
- Evidence separates `primary_observation` from
  `scholarly_interpretation`; `assertion_type` distinguishes
  `primary-evidence`, `secondary-evidence`, `scholarly-reconstruction`, and
  `inference`. Confidence, certainty, and dispute status are separate fields.
- Later Christian reception has a separate CKL field; Second Temple and other
  periods use their own context/temporal fields. Historical event, proposed
  occasion, source composition, manuscript date, and reception are not one
  shared date.
- NE-9C accepted/held/excluded decisions and NE-10 verified/held bridges are
  separate registries. The frozen NE-9C checkpoint is not to be regenerated.

## Protected state at baseline

The ED-2 merge and ED-3 worktree have no diff in the NE-9C bulk-curation files
or authored NE-9C/NE-10 curation artifacts relative to `origin/master`. The
current registry reference counts are 433 accepted NE-9C identities, 44
verified NE-10 bridge records, and 7 held bridge candidates. Baseline hashes:

- Frozen NE-9C checkpoint: `0f8e4f690bd701be2856fc5af1a304f864163f7a8adc896b760d0c95b349c6f9`
- NE-10 verified bridges: `8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b`
- NE-10 held candidates: `15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3`

The legacy bulk-curation `validate` command was attempted but stopped with
“protected CKL source fingerprint changed.” Its checkpoint predates ED-2's
CKL additions. ED-3 will preserve that frozen checkpoint and use artifact and
authored-identity compatibility checks, rather than regenerate the historical
fingerprint.
