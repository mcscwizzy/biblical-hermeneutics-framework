# ED-1B pre-merge compatibility review

## Decision

ED-1B is compatible with the current CKL, Narrative Explorer, and release paths. The NE-9C fingerprint rejection is a historical bulk-curation checkpoint guard. It detects that ED-1B changed CKL object files and stops the original inventory from being silently reused. It does not reject ED-1B in current CI or release validation, and the runtime Narrative Explorer does not load that checkpoint.

Psalm 72's initial reader projection was too narrow for the evidence item's royal-psalm and literary-setting focus. Its evidence type is now the existing `literary-convention` type, which projects into `biblical_narrative` and `themes_biblical_connections`. This changes one evidence metadata value; the evidence ID, exact anchor, source records, research claims, qualifications, and NE-9C data are unchanged.

## NE-9C fingerprint and operational impact

`scripts/ne9c_bulk_curation.py` computes `object_source_tree_sha256` from every non-underscore JSON object under `framework/canonical_library/objects/`. Both `initialize_inventory` and `validate_inventory` compare the current hash with the value pinned in `docs/narrative-explorer/ne9c-bulk-curation/checkpoint.json`. Any CKL object edit changes this tree hash, including adding evidence to an existing book object. The guard therefore rejects ED-1B by design; it protects the historical triage snapshot from being treated as a fresh inventory.

At review, the checkpoint's pinned hash was `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`; the ED-1B object-tree hash was `d190ad16dc2c0fa2845d18960dd676ade1ec65f2c7556a6d3768dc8f77055873`.

The current `.github/workflows/validate.yml` does not call the bulk-curation command or validate the documentation checkpoint. It runs framework validation, selected regression tests, package/release checks, and a wheel smoke test. The release checks require the accepted runtime curation file under `framework/canonical_library/curations/narrative-explorer/ne9c/`; ED-1B leaves that registry unchanged. The runtime loader in `bhf_agent/presentation/narrative_explorer_curations.py` reads that version-controlled registry. It does not read `docs/narrative-explorer/ne9c-bulk-curation/`.

The repository contains tests for the bulk-curation workflow, but those test temporary state and do not invoke the committed historical checkpoint. The fingerprint rejection is therefore a historical audit result, not a current CI, release, or reader failure.

The bulk validator passed with all 3,925 decisions against a complete, temporary `origin/master` snapshot. Running it against a temporary copy of the checkpoint paired with the current CKL returned the expected `protected CKL source fingerprint changed` error. Both runs left the repository checkpoint untouched.

## Reviewed identity and decision audit

The ED-1A `origin/master` snapshot and the ED-1B tree were compared without editing either checkpoint or decision ledger:

- The pinned checkpoint and `decisions.jsonl` are byte-identical to `origin/master`.
- Rebuilding the authored object relationship inventory from both trees produced 4,061 relationships in each. All 4,061 edge IDs and exact authored identity tuples match. The tuple is relationship kind, source ID, target ID, authored relationship type, authored notes, and authored weight.
- All 3,925 reviewed decision IDs resolve to their original `authored_identity` in both the ED-1A snapshot and current CKL. The decision ledger is byte-identical to the baseline, and canonical JSON comparison confirmed that every decision payload is unchanged and passes current disposition/curation validation.
- The original backlog classification remains `uncategorized` for all 3,925 reviewed relationships. Dispositions remain 408 curated, 1,895 held, and 1,622 excluded.
- All 408 curated decisions still match their exact runtime curation payloads. Their classifications remain: 248 `interpretive_association`, 107 `thematic_relationship`, 45 `later_canonical_reception`, 6 `shared_literary_motif`, 1 `direct_quotation`, and 1 `narrative_parallel`.

No NE-9C decision, accepted relationship identity, or classification was changed. The historical fingerprint was neither regenerated nor weakened.

## Psalm 72 projection check

The evidence item is `ckl:psalms#evidence:psalm-72-royal-justice-setting`, anchored to Psalm 72:1–14, with two resolved source records. Before correction, `worldview-concept` placed it only in `themes_biblical_connections`. The existing projection policy maps `literary-convention` to both `biblical_narrative` and `themes_biblical_connections`; the current exact-passage projection now exposes it in both contexts. Its source locators, primary observation, scholarly interpretation, confidence, dispute status, and passage relevance remain visible and unchanged.

## Future compatibility validation

Keep the full object-tree fingerprint as the historical inventory lock. For future CKL additions that do not alter authored relationships, the smallest safe addition is a separate, read-only compatibility check that:

1. verifies a pinned SHA-256 for the reviewed decision ledger;
2. resolves each ledger `edge_id` and `authored_identity` against current authored `related_objects`;
3. validates every disposition, classification, and curated payload against the current runtime curation registry; and
4. reports identity or decision drift without rewriting the checkpoint, waves, or ledger.

This would be a distinct compatibility result, not a bypass or replacement for the existing strict historical fingerprint check. ED-1B does not implement that future mechanism.

## Targeted verification

The final regression run and current-tree CKL validation are recorded in the ED-1B [pilot report](README.md). The compatibility audit above additionally checked the original checkpoint and decisions against the `origin/master` snapshot and current authored relationship identities. No checkpoint or scholarly decision files were written during this review.
