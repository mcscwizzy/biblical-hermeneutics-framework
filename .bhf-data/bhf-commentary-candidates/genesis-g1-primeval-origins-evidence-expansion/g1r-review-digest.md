# Genesis G1R comparative applicability reconciliation

**State:** `GENESIS_G1_PRIMEVAL_ORIGINS_EVIDENCE_MERGE_GATE_VERIFIED`. The focused validation suite and `git diff --check` pass.

The chapter preparer indexed every `scripture_references` entry as an applicability anchor. The passage matcher ignores the link’s `relationship` and `temporal_relation`. G1 stored three comparative/later-reception references alongside Genesis 3 anchors, so they were prepared in other books. This is a G1 data-model mistake exposed by a shared, systemic applicability behavior.

## Repaired Genesis 3 evidence

- `g3-cherubim-biblical-sacred-space-context`: only Genesis 3:24 remains in applicability references. Exodus 25:18–22 and 1 Kings 6:23–35 remain in notes and their Scripture source records remain linked.
- `g3-serpent-later-canonical-reception`: only Genesis 3:1 remains in applicability references. Revelation 12:9 remains as later reception context with its source records.
- `g3-seed-later-jewish-christian-reception`: only Genesis 3:15 remains in applicability references. Revelation 12:9, 17 remain as reception context, distinct from the immediate offspring-conflict wording.

The other 29 G1 items had no non-Genesis Scripture references. The full 32-item audit is in `g1r-comparative-applicability-report.json`. Source-lock outcomes remain 32 LOCKED, 3 UNRESOLVED, 6 REJECTED, and 0 CONFLICTED.

## Chapter results

Genesis 1–5 inputs match original G1 exactly. Genesis 1 and 5 remain GOOD; Genesis 2–4 remain GOOD with their G1 evidence intact. Exodus 25, 1 Kings 6, and Revelation 12 evidence and synthesis hashes return exactly to their G0 identities. Isaiah 36, Acts 16, and Revelation 18 remain input-identical.

Commentary v1.2 was not regenerated or modified. Its manifest, checksum index, corpus root, release descriptor, and chapter tree identities remain unchanged.

A read-only CKL scan found 47 other mixed direct and non-direct cross-book evidence records. The applicability semantics need a separate maintenance review; no historical CKL records were changed in this repair.

**Tests:** 213 passed and 35 subtests passed in the focused batch; the G1R regression module also passed 2 tests. `test_evidence_graph_expansion.py` could not be collected because FastAPI is absent in this environment; typed-target tests and whole-CKL validation passed.
