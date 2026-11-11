# ED-4 Baseline

## Branch and merge state

- Fetched `origin/master`: `31832793a155b16b6d694b1e84202bac1ee47c38`.
- This is merge commit #78, merging `audit/ed3-scholarly-integrity`; ED-3 is
  merged.
- Created `feat/ed4-research-quality-and-review` from that exact commit. The
  starting worktree was clean.
- The ED-3 report, review process, queue, research-depth priorities,
  source-integrity findings, validation results, and the ED-1C/ED-2 source and
  reader reports were reviewed before implementation.

## Reproduced inventory

Commands ran on the current repository. Generated JSON and census artifacts
are under `/tmp/ed4-baseline-*`, not in Git.

| Measure | Current baseline |
|---|---:|
| CKL objects / valid objects | 687 / 687 |
| Claims | 2,329 |
| Typed evidence items | 1,408 |
| Interpretive notes | 3,691 |
| Child source-reference occurrences / unresolved | 17,721 / 0 |
| Unique bibliography source IDs / occurrences | 2,897 / 5,348 |
| Missing title or bibliographic detail | 558 (472 Scripture/text IDs; 86 reference-work IDs) |
| Passage-specific / contextual-only / entity-only chapters | 1,089 / 56 / 2 |
| No-eligible / incomplete-or-unknown chapters | 41 / 1 |
| NE-A1 census rows / unmapped identities | 1,189 / 0 |
| NE-A1 deterministic sample checks / targeted service builds | 19 / 16 |
| Strict retrieval report: 2+ items / 1 item / 0 items | 669 / 479 / 41 |
| Strict CKL errors / warnings | 0 / 14 |
| Deep heuristic error-severity findings / warnings | 63 / 1,093 |
| Source-support-target signals | 102 |

The detailed chapter classification is an eligibility audit; the separate
strict retrieval report counts retrieved CKL records. Their counts answer
different questions and are not interchangeable. The chapter census reported
Obadiah 1 as `incomplete_or_unknown` with 62 eligible items and one unresolved
anchor; the strict retrieval scan reported that chapter as `AVAILABLE` with 3
valid anchored parent candidates and 61 bundle items. Phase 6 investigates
that classifier difference.

The current runtime census fingerprint is
`c531b8cfa32e2d817c2c9232b1f0bf78897c15ac86e2348bfa2b5b209247eb80`. ED-3's
baseline recorded its earlier ED-1A fingerprint separately; this run uses the
current library and census code on the fetched ED-3 merge.

## Human-review baseline

- Queue: 99 rows, preserving 99 distinct evidence IDs.
- Individual packets: 99, each referenced from the queue.
- Reviewer name, affiliation/expertise, date, decision, rationale, and
  correction/follow-up fields: all blank for all 99 rows.
- ED-3 machine outcomes: 27 supported with limitations, 1 correction-required
  note already repaired, 71 unable to independently verify; no human
  approvals. The 71 outcomes describe an access/verification limit, not proof
  that the claims are false.

## Protected curation baseline

ED-3 recorded 433 accepted NE-9C identities (431 object, 2 evidence), 44
verified NE-10 bridges, and 7 held candidates. The protected hashes reproduced
on this branch baseline:

| Protected artifact | SHA-256 |
|---|---|
| Frozen NE-9C checkpoint | `0f8e4f690bd701be2856fc5af1a304f864163f7a8adc896b760d0c95b349c6f9` |
| NE-10 verified bridges | `8460edaafcadfbabb807e3bde8b1979f8bbcadf81b5d42cae755ddc4bdec999b` |
| NE-10 held candidates | `15e577dae912904409cedd39015507f3aec92d6c3f389c65ff58a8396acd64f3` |

The legacy NE-9C bulk validator intentionally pins an earlier CKL source-tree
fingerprint. Its rejection on the modern CKL is an inherited limitation, not a
reason to refresh the checkpoint.

## Retrieval baseline

Command:

```bash
.venv/bin/python -m pytest -q \
  tests/canonical_library/test_1_john_record.py \
  tests/canonical_library/test_1_thessalonians_record.py
```

Result: **2 failed, 16 passed, 224 subtests passed** in 426.96 seconds. The two
failures match ED-3's inherited cases:

| Query | Expected first result | Baseline first result |
|---|---|---|
| `What if our heart condemns us?` (asked with the test's `1 John` prefix) | `1-john` | `john` |
| `How does 1 Thessalonians relate to Acts 17?` (asked with the test's `1 Thessalonians` prefix) | `1-thessalonians` | `acts` |

The work begins with both failures present on the fetched merge, rather than
attributing them to ED-4.

## Baseline commands

| Command | Result |
|---|---|
| `.venv/bin/python tools/validate.py framework/` | 94 modules valid |
| `.venv/bin/python tools/ckl_validate.py --root framework/canonical_library --json` | 687 valid, 0 errors, 14 inherited warnings |
| `.venv/bin/python tools/ckl_report.py --root framework/canonical_library --deep --json --output /tmp/ed4-baseline-deep.json` | 1,408 evidence items; 63 heuristic error-severity findings; 1,093 warnings; 102 support-target signals; 0 unresolved child-source references |
| `.venv/bin/python tools/ckl_coverage_report.py --json /tmp/ed4-baseline-coverage.json` | 1,189 chapters analyzed; 669 available, 479 thin, 41 data gaps |
| `.venv/bin/python scripts/audit_ed1a_evidence_depth.py --output-dir /tmp/ed4-baseline-ed1a --study-db .bhf-data/study.sqlite` | Pass; 1,189 chapters, 687 CKL objects, 0 unmapped identities, 19 sample checks, 16 service builds |

The local `.bhf-data/study.sqlite` was used as a read-only audit input; all
generated census output went to `/tmp`.
