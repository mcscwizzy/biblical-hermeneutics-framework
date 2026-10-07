# Transaction C1 — CKL geography Commentary v1.2 selective impact

## Scope and baseline

This document records Transaction C1 only: determine which published Commentary v1.2 inputs changed after Transaction A and repair the read-only selective input recompilation blocker. No Commentary prose was generated or rerendered, no CKL or archaeology/map source data was changed, and no deployment was performed.

- Transaction A production baseline: `master` / `0772c19c178bd4478991f40d6181a927f4095378`; CKL has 679 objects, 90 places, 102 people, 14 warnings, inventory fingerprint `78d983e0aed63f489e1126a054d087e86049b10915ffd3810ca0fd5eb617defd`, byte signature `0bd8259ce0af2a8cd748d1c82cda732010954ee98173e72238950f8de2661c40`.
- Transaction B: `DERIVED_RUNTIME_NOT_SEPARATELY_REQUIRED` for this input impact operation.
- Published Commentary v1.2 remains immutable. The published payload is `.bhf-data/bhf-commentary-v1.2/`; its release publication index is `.bhf-data/bhf-commentary-v1.2/.bhf-commentary-release.json`, and chapter files contain `generated_metadata.evidence_hash` and `generated_metadata.synthesis_hash`.

## v1.2 pipeline, identity source, and reader path

`framework/commentary/production/inputs.py::prepare_chapter()` is the current packet preparer. It calls `get_chapter_evidence_bundle()` with `EVIDENCE_BUNDLE_CANDIDATE_VERSION`, calls `compile_chapter_synthesis()`, validates the synthesis, and returns a `PreparedChapter` whose packet and `InputIdentity` bind evidence and synthesis hashes. The current constants are EvidenceBundle `1.1`, synthesis schema `1.1`, and synthesis compiler `1.1`. The packet is assembled in memory; this function does not persist Commentary.

The frozen source-lineage snapshot is `.bhf-data/bhf-commentary-candidates/commentary-v1.2-current-source-lineage-v2/manifest.json` with chapter records beneath its `qualification/` and `scale-pilot/` directories. That snapshot is a deterministic source-contract baseline, not the release consumed by readers. For this comparison the authoritative old per-chapter hashes came from the published release manifest’s `chapter_publication_index[].source_lineage` where present, cross-checked against published artifact `generated_metadata`; Acts 27 uses its published artifact metadata because its index row comes from the historical 75-chapter release. Psalms 76 has no published prose file, but its release index stores both old input hashes and points to a validated source-limited corpus result. All 15 old evidence and synthesis hashes were independently reproduced from the pre-Transaction A CKL snapshot.

`docs/commentary-v1.2-release.json` freezes release identity. `bhf_agent/runtime_paths.py` resolves `BHF_COMMENTARY_RELEASE=commentary-v1.2` to `.bhf-data/bhf-commentary-v1.2/` in a source checkout, with packaged fallback `bhf_agent/data/commentary-v1.2/`. `bhf_web/settings.py`, `bhf_web/app.py`, and `bhf_web/routes/bhf_commentary.py` consume that resolved storage path. The production reader does not read the candidate/source-lineage workspace directly.

## Reproduced blocker and minimal repair

Before repair, `selective_recompile(["Ruth 1"])` failed at `framework/canonical_library/expansion.py::selective_recompile()` with:

```text
TypeError: prepare_chapter() got an unexpected keyword argument 'study_db_path'
```

The caller also supplied the unsupported `read_only_inputs=True` flag. The default selector now calls the real `prepare_chapter()` with only its explicit `study_db_path` input. `prepare_chapter()` passes that path to the existing EvidenceBundle builder; it has no persistence path for Commentary. `selective_recompile()` first calls `require_current_study_database()`, which checks the existing database schema through SQLite read-only access and fails closed if the database is absent or stale. Both archaeology and map evidence lookups then use `prepare_schema=False`, reading the prevalidated database without initializing or migrating it. The public preparer behavior is unchanged unless a caller supplies the optional database path. Injected `chapter_preparer(book, chapter)` remains supported; supplying `study_db_path` with an injected preparer is explicitly rejected. Legacy `bundle_builder` and `synthesis_compiler` hooks remain rejected.

The selector continues to enforce the current v1.2 EvidenceBundle version, chapter identity, synthesis identity, and `validate_synthesis()` result. Its diagnostic row now also records evidence item count and sorted evidence IDs, alongside evidence availability and synthesis unit count. No result contains Commentary prose.

## Focused verification

- RED: focused test run reproduced the `TypeError` in the default selector and the existing missing-database test showed the same argument mismatch before reaching the intended read-only database guard.
- GREEN: `.venv/bin/pytest -q tests/canonical_library/test_expansion.py -k 'selective_recompile'` — 13 passed, 52 deselected, including read-only map input.
- `.venv/bin/pytest -q tests/test_commentary_v12_reader_provenance_binding.py::test_current_record_reconstructs_to_its_frozen_source_identity` — 1 passed.
- The broader `tests/test_commentary_v12_current_lineage.py` run produced 5 passes and 1 failure: `test_current_lineage_rebuild_is_deterministic_and_explicit` detects the expected global source-lineage drift after Transaction A. The release-manifest old hashes were separately reproduced from the pre-A CKL for every requested target and control; the three controls show no drift.
- Final read-only map change was followed by a fresh CKL verification and two preparations of the exact 15 references. Counts, warnings, fingerprint, and byte signature matched; both runs were identical to one another and to the recorded C1 manifest.
- `git diff --check` will be rerun before commit.

## CKL preflight and deterministic recompile

Immediately before the 15 requested chapter preparations, a fresh `CanonicalLibrary().load()` and `scan_library()` yielded exactly 679 objects, 90 places, 102 people, 14 warnings, and zero errors. The inventory fingerprint and byte signature matched the required values above. Source Git SHA recorded for this transaction is `0772c19c178bd4478991f40d6181a927f4095378`.

The exact target set was `1 Samuel 17`, `2 Kings 5`, `Acts 27`, `Genesis 13`, `Genesis 34`, `Isaiah 36`, `John 4`, `Joshua 6`, `Judges 20`, `Matthew 2`, `Numbers 18`, and `Ruth 1`. Controls were `Psalms 76`, `Revelation 18`, and `Acts 16`. `selective_recompile()` ran twice for the exact combined 15-reference set in the same unchanged input environment; all result rows matched exactly. No model or prose renderer was invoked.

All old evidence and synthesis hashes were rebuilt with the same v1.2 bundle/compiler from the first parent of the production merge, `0b39f7a05f2b748de81f6b9b4b8175a6247dc417`, which holds the pre-Transaction A CKL. Each of the 15 reconstructed old hashes matched its published release identity. For every changed target, the current bundle contains new evidence IDs owned by CKL records changed in Transaction A; the specific added IDs are listed below. This establishes a direct CKL evidence delta and not unrelated environment drift.

## Per-chapter identity comparison

All current versions are EvidenceBundle `1.1`, synthesis schema `1.1`, and compiler `1.1`. Old per-chapter hashes are from the published v1.2 release manifest; old version fields are copied from published chapter metadata where that artifact exists. Psalms 76 has no prose artifact, so per-chapter version metadata is unavailable there, while both frozen hashes remain present in the release index and were reproduced from pre-A CKL.

| Reference | Old evidence hash | New evidence hash | Old synthesis hash | New synthesis hash | Evidence items | New synthesis units | Classification | Future candidate |
|---|---|---|---|---|---:|---:|---|---|
| 1 Samuel 17 | `8c289caf94a73985981ef3dcc6406928169c3748f12780374fb0a92ad5655155` | `5556dbf59881489d3f94e32f0f0e01879fcdfdfdb11ac1a7f579ac833a9f67cd` | `664eaf4262927f411efd0d25886c72ab05e0299b0cc78ce930e577194afa5c65` | `1105d490acf8e7254af3d2168e1b81606026ac684aa36ec89b07199bf86c5d4d` | 44 → 46 | 10 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| 2 Kings 5 | `a92d1c9d4c6c771bc882fe0af2e8518526c88e484a141d6c595f762d4907a952` | `3809454fdb77b0baf035e62d82d15102942d170a17b5025163c308d3dd38e76c` | `13e54a21f10d4097fb1d360bb352e16f3725ca8e9afb10959b05d3a9811118de` | `6314975c710fce70018f69f07ae6c4e28a6c7097ca092e74669eba4e0b1666fc` | 1 → 6 | 5 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Acts 27 | `43fab16887c84e08998867bfda7d0a272b276965f4d46b079f2613d81fa556db` | `ff14fba83fb2c7718d454252c70d64649e0901dabee5d2dd4ca12f860a601f78` | `62bade47f701b4a49eee5cc595723774ead0772970780af5a4b74bcec3075a9d` | `e763b6c025da056653022115b1799b21ad51d82e348a491936df211bede85a2a` | 5 → 14 | 14 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Genesis 13 | `4b16ee265db55e19aa832b598ce57e18fe3e847f3a2fd0c0955eba97084f12f6` | `513efc8ac13f279874b658ffb3529b1fb78e0a5102c7f1bb650e38f93be21fc2` | `d22dadff9ff153050af30dbeeb1021b84248c1d310ef4830f6f73f709f0fe710` | `c83250bfd35e5cfca438a18d707bfb57a1145e626fac61a4d8c998a9b1330c95` | 3 → 6 | 5 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Genesis 34 | `32aa624e5ce08506ccfa20866f8f73c6cb968fe230eb3df9465545c21102a994` | `dd3fac5f67d75d70c3c4038fcc24d3470776e1692e9fe363e7db31441ddb1426` | `aa06e626eff7f4dfe1fe229af641f77da4625fe7f1e9a276de3b9cca6997db48` | `dc91ea7b624f4c709028d8231c904ee1c9edffd2f21140d885dddb9e1b23ec0b` | 3 → 5 | 5 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Isaiah 36 | `d0a416ef62843e2a5bfd6b7afbc00b28e47e21663011b89e638f79bfa31faedb` | `a4628db116c607cc1520eca1cf86d67cfc00082bacd9f8bb9bebd289752c237f` | `13bfdd657d8894b1cffacbe5ced27c8d399b29266a306a31f1a8c28fdd4a3669` | `0ae4045de8f1fe601699b54e05484e1fa0d77a3cfae66ebaa47d29b494cf737c` | 25 → 28 | 12 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| John 4 | `5754dce09b19398db16f631917a2604c5ce5596e6cde0fe1f3331e2baa7dba0f` | `c838a5c9af50544141adfefc264077d001db9017d6f4ad25040f26ad80e2424b` | `5f8626783e689b48318feb3f3e6d90ce0631c6096bc652c6f8d257db3197c182` | `acfe73951b7800c01c5f838061e6b2a3964267a38a6930b46518bfc42b9542ca` | 7 → 10 | 5 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Joshua 6 | `d10fd021c232ebdfedea2bcbf61b9a18e0aa1f5ec3d414e1b8258e7fef6e6895` | `3d8ee512e4ccd07b52a096ad3fde0995b43509fcf048b9a5cf6892c97289a789` | `23eb1892b86436e5d84228a379184ba253b6bbcdda3ff602c09cd731536edaec` | `25a695fb8911720b3894a8a3385696c18ef46d4a7bf6e64e2d3cefc63d2b9a7c` | 7 → 9 | 7 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Judges 20 | `96f737fed1db2e5347af242223ccb9f6c2c423bfda2fd67960067f44ac67afc8` | `fd5efa85a5497c7355681d78dd0bbc376abb4f4c380ae352358bc0860473edd9` | `58284a66f1fc53aa3e59fe5bd5781da85390e693c5f3e962524d109bca86a392` | `331c586bed622fcec67d365d862566d23438f297dcac642134cc05d1b8f82f8e` | 2 → 3 | 3 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Matthew 2 | `1aeee333a66ab737a49c10c24eb5d603ddc1e22f140d03c62886a4990bfe524f` | `c48913bd185047f1a80f086817bf59cf494bb37a6747310f3722b89bfec1b94e` | `3247a06fc2b87d11623896db0367659f322b23492ef5a73e87075272930f4f5b` | `4fb286f565a7eddbd15488efb4ae30e793ff6fee6375638ac5c30e34e3dbb0c6` | 33 → 34 | 10 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Numbers 18 | `94b518a68787e9ca707665e95a262b0169bfb611f3cd51d8654e799ad99d204d` | `785aafb367ed47fa7eb77a2266b51348c31451de23d2cf455c6c77901dd9c6bc` | `81a4afab49a895a9957932a35496b7c574dc951ca032285e16f08c58c5007674` | `462866b275503b11655d321f4286a59d16d5637e50b0ad572e61f46f921f0253` | 5 → 7 | 3 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Ruth 1 | `9b25f9ec169873ffbbcfe387f238bf2618195918a136c2c6eda37ca4c74c119c` | `1224b8fcf887845f926aa765da713e3301c1b5f26f2d9bb8fc9505dc5e0677ba` | `ba93ac0b616347616f3e7d8c000cd05a31836a96429c0cd1268a194e351e72a7` | `315fb5e50f38e7f3720f3bbdd574360e7d02e6dc48964b1edd1deae1a9e29969` | 14 → 17 | 8 | EVIDENCE_AND_SYNTHESIS_CHANGED | yes |
| Psalms 76 | `a4b7138baefd5f742058b5334dab09befa853dc0702151bc57c6965282fa2e72` | `a4b7138baefd5f742058b5334dab09befa853dc0702151bc57c6965282fa2e72` | `ff565d20e5bac53a9991662ea3d49ff549898064ec5472a0c2d68be5cae133ba` | `ff565d20e5bac53a9991662ea3d49ff549898064ec5472a0c2d68be5cae133ba` | 0 → 0 | 0 | UNCHANGED | no |
| Revelation 18 | `25557051dcec7d29672b60818336b838b7ad8c9f2b434129fc4628de3631eaa2` | `25557051dcec7d29672b60818336b838b7ad8c9f2b434129fc4628de3631eaa2` | `4278ced9a5bd1c4cb2331fb0946aaddb44069c5ea51c9fb449a2ca20084ebbc0` | `4278ced9a5bd1c4cb2331fb0946aaddb44069c5ea51c9fb449a2ca20084ebbc0` | 13 → 13 | 3 | UNCHANGED | no |
| Acts 16 | `e37784f5bcd4a44435e8104ae9097f27c59d03fdf332707603fe81b8b87fe0f2` | `e37784f5bcd4a44435e8104ae9097f27c59d03fdf332707603fe81b8b87fe0f2` | `3ceb2889b3680af307b37f7304390010506014be0c2477bd93b4f83576f93592` | `3ceb2889b3680af307b37f7304390010506014be0c2477bd93b4f83576f93592` | 89 → 89 | 50 | UNCHANGED | no |

### Traceable CKL evidence deltas

- **1 Samuel 17:** added CKL evidence IDs: `azekah-1samuel-17-socoh-azekah-encampment-identity`, `socoh-1-1samuel-17-socoh-azekah-encampment-identity`, `source-lock-1samuel-17-elah-opposing-slopes`, `source-lock-1samuel-17-socoh-azekah-encampment`. Removed IDs: `jericho-1:ancient_near_east_context:0`, `jericho-1:historical_context:0`. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **2 Kings 5:** added CKL evidence IDs: `abana-2kings-5-damascus-river-comparison-identity`, `pharpar-2kings-5-damascus-river-comparison-identity`, `source-lock-2kings-5-damascus-river-comparison`, `source-lock-2kings-5-naaman-aram-israel-jordan-journey`, `source-lock-2kings-5-naaman-jordan-immersion`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Acts 27:** added CKL evidence IDs: `cnidus-acts-27-sidon-crete-maritime-itinerary-identity`, `crete-acts-27-sidon-crete-maritime-itinerary-identity`, `cyprus-acts-27-sidon-crete-maritime-itinerary-identity`, `fair-havens-acts-27-sidon-crete-maritime-itinerary-identity`, `italy-acts-27-sidon-crete-maritime-itinerary-identity`, `lasea-acts-27-sidon-crete-maritime-itinerary-identity`, `myra-acts-27-sidon-crete-maritime-itinerary-identity`, `source-lock-acts-27-crete-wind-navigation-conditions`, `source-lock-acts-27-sidon-crete-maritime-itinerary`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Genesis 13:** added CKL evidence IDs: `source-lock-genesis-13-abram-negev-bethel-ai-movement`, `source-lock-genesis-13-jordan-valley-well-watered-description`, `source-lock-genesis-13-lot-eastward-separation`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Genesis 34:** added CKL evidence IDs: `source-lock-genesis-34-city-gate-negotiation-setting`, `source-lock-genesis-34-local-population-description`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Isaiah 36:** added CKL evidence IDs: `source-lock-isaiah-36-assyrian-campaign-against-judah`, `source-lock-isaiah-36-lachish-jerusalem-assyrian-deployment`, `source-lock-isaiah-36-upper-pool-conduit-field-setting`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **John 4:** added CKL evidence IDs: `source-lock-john-4-judea-samaria-galilee-journey`, `source-lock-john-4-sychar-well-near-jacob-field`, `sychar-john-4-sychar-well-near-jacob-field-identity`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Joshua 6:** added CKL evidence IDs: `source-lock-joshua-6-jericho-closed-city`, `source-lock-joshua-6-jericho-encirclement`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Judges 20:** added CKL evidence IDs: `source-lock-judges-20-mizpah-gibeah-campaign-locations`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Matthew 2:** added CKL evidence IDs: `archelaus-matthew-2-archelaus-judea-administration-identity`, `source-lock-matthew-2-archelaus-judea-administration`, `source-lock-matthew-2-bethlehem-judea-territory`, `source-lock-matthew-2-egypt-return-itinerary`, `source-lock-matthew-2-nazareth-galilee-region`. Removed IDs: `nazareth:ancient_near_east_context:0`, `nazareth:hebraic_worldview:0`, `nazareth:historical_context:0`, `nazareth:second_temple_context:0`. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Numbers 18:** added CKL evidence IDs: `source-lock-numbers-18-levites-no-territorial-inheritance`, `source-lock-numbers-18-levites-tithe-as-inheritance`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Ruth 1:** added CKL evidence IDs: `judah-territory-ruth-1-bethlehem-judah-territory-identity`, `source-lock-ruth-1-bethlehem-judah-territory`, `source-lock-ruth-1-bethlehem-moab-migration`. Removed IDs: none. Every added ID was found on a CKL object changed by Transaction A. The evidence and synthesis hashes changed; the pre-A rebuild reproduces the old release hashes.
- **Psalms 76 (control):** no evidence IDs entered or left the bundle; both hashes match the published baseline.
- **Revelation 18 (control):** no evidence IDs entered or left the bundle; both hashes match the published baseline.
- **Acts 16 (control):** no evidence IDs entered or left the bundle; both hashes match the published baseline.

## Outcome

`COMMENTARY_CANDIDATE_CHAPTER_SET` is exactly:

```text
1 Samuel 17
2 Kings 5
Acts 27
Genesis 13
Genesis 34
Isaiah 36
John 4
Joshua 6
Judges 20
Matthew 2
Numbers 18
Ruth 1
```

All 12 targets classify as `EVIDENCE_AND_SYNTHESIS_CHANGED`; each has a changed evidence hash and synthesis hash directly tied to newly selected Transaction A CKL evidence. The controls all classify `UNCHANGED`. No target or control is `BASELINE_IDENTITY_UNAVAILABLE` or `BLOCKED`. The separate full current-lineage verification still needs an explicit future rebaseline/reconciliation decision because its 96-chapter snapshot predates CKL geography changes; this does not alter the published release or these verified comparisons.

The complete machine-readable impact data, including availability, IDs, versions, counts, old/new hashes, classifications, reasons, and candidate-required flags, is `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-impact/impact-manifest.json` (SHA-256 `3bf1cf7a71cdc6eb7cf584c13e96a7e58652ac588a286415c00dc2bee0ac9624`).

## C2 preflight resolutions (before generation)

### Isaiah 36 published evidence hash

The malformed value shown in the C1 status display (`d0a416ef62843e2a5bfd6b7afbc00b28e47e21631f1a8c28fdd4a3669`) is not present in the repository. The authoritative old evidence hash is `d0a416ef62843e2a5bfd6b7afbc00b28e47e21663011b89e638f79bfa31faedb` (64 lowercase hexadecimal characters), and it agrees across the published release index's `source_lineage`, the published Isaiah 36 artifact's `generated_metadata`, the C1 impact manifest, and the C1 comparison table. The committed evidence is intact; the defect was a status-display transcription, not an impact-manifest serialization error or corrupted published metadata. Regression coverage checks the release/index/artifact/manifest agreement and validates all four hash cells in the rendered C1 table.

### Current-lineage test after Transaction A

The September 12 `commentary-v1.2-current-source-lineage-v2` manifest is a frozen pre-Transaction-A 96-chapter snapshot. Transaction A intentionally changed current CKL-derived packet identities. A fresh `build()` gives manifest identity `e3674534fb1acf0141a602cc602857f084cb2b5198f03967ea4e0e8b1bef8ea5`; exactly three scale-pilot rows differ from that preserved snapshot: John 2, Jeremiah 49, and Acts 27. Their old/new evidence and synthesis identities are pinned in `tests/test_commentary_v12_current_lineage.py`; Acts 27's new values match C1. The qualification population is unchanged. The frozen snapshot and historical/published lineage artifacts remain preserved. The test now expresses the distinction between that frozen baseline and deterministic current CKL output instead of treating the expected Transaction A changes as unexplained drift.

Preflight tests run before C2 input preparation: `.venv/bin/pytest -q tests/test_transaction_c_commentary_impact.py` (4 passed), `.venv/bin/pytest -q tests/test_commentary_v12_current_lineage.py` (6 passed), `.venv/bin/pytest -q tests/canonical_library/test_expansion.py -k 'selective_recompile'`, and the frozen-lineage/published-release reconstruction tests recorded in the C2 results below. No prose/model rendering has occurred at this point.

## C2 entry requirements

1. The exact candidate chapter set, impact manifest, and evidence-ID deltas are explicitly authorized for C2 by the user request.
2. Recheck the CKL inventory fingerprint and byte signature against the reviewed manifest before any C2 input lock.
3. Render only the exact C1 candidate set authorized for C2 into a distinct non-production candidate namespace. Keep the published v1.2 release immutable through C2 validation and review.
4. Require deterministic input identities and the current EvidenceBundle, synthesis schema/compiler, and Commentary v1.2 validation contracts. A control drift or any identity disagreement blocks C2.
5. Promotion/deployment requires a separate explicit release action after human review; C1 authorizes neither.

## C2 results

### Rendering and provenance

- The CKL inventory recheck matched C1 exactly: 679 objects, 90 places, 102 people, 14 warnings, zero errors, inventory fingerprint `78d983e0aed63f489e1126a054d087e86049b10915ffd3810ca0fd5eb617defd`, byte signature `0bd8259ce0af2a8cd748d1c82cda732010954ee98173e72238950f8de2661c40`.
- C2 prepared exactly the 12 C1 references through `V12CorpusRunner.prepare()`. All 12 were renderable and their prepared evidence/synthesis hashes matched the C1 manifest before rendering. The three controls were excluded.
- The initial sandboxed Codex CLI invocation failed before any model response because its local app-server could not write profile state. The same configured renderer was then run with the required local state access; there was no model/provider substitution. One isolated diagnostic Genesis 13 response was rejected; its raw-response hash and validation reason were recorded. The formal candidate render run then produced its separately validated Genesis 13 result.
- The formal run rendered exactly 12 chapters from 2026-10-07 00:28:33Z to 00:34:38Z. Model: `gpt-5.6-terra`; effort: high; provider/renderer: host-local Codex CLI `codex-cli 0.160.1`, renderer label `commentary-v1.2-codex-cli`; Commentary prompt `1.8`; Commentary schema `1.2`; EvidenceBundle `1.1`; synthesis schema/compiler `1.1`.
- The existing artifact format has `generated_metadata.generated_timestamp: null`; per-chapter generation start/end times are therefore recorded in the candidate manifest. Each candidate also records packet SHA-256, raw-response SHA-256, candidate artifact SHA-256, old/new evidence and synthesis hashes, Transaction A evidence ID additions/removals, renderer identity, compiler/prompt versions, and result/review status.

### Candidate outcomes and artifact hashes

The exact review set has 11 `READY_FOR_HUMAN_REVIEW` candidates and one `INVALID_ARTIFACT`. No candidate is approved. Ruth 1 retains its returned artifact and raw response, but the existing validator rejected missing confidence/interpretation fields and confidence exceeding cited evidence/synthesis; it is not marked ready for review.

| Chapter | Review state | Candidate artifact | SHA-256 |
|---|---|---|---|
| 1 Samuel 17 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-48bc7a4b71863518/chapters/1_samuel_017/commentary.json` | `f3b5669a33d28923a72bf5c801b177e81131969ce0c7236791351a0e4417b67d` |
| 2 Kings 5 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-0e53eca15a36aa3a/chapters/2_kings_005/commentary.json` | `480c7585e9836ded362662004d2818ed8f81f05affb5e9568d367a572b08c3c6` |
| Acts 27 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-9f02a6ae0a47569b/chapters/acts_027/commentary.json` | `ac625b17687b3c0158f04a5d7678394f07b2c3877ee243b6f0342a0e043ef8d8` |
| Genesis 13 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-13c4d7e346924c69/chapters/genesis_013/commentary.json` | `c389b19f4781f3000242d437c61c0d36ffefc48c596e20f00f7935bafe97c8d4` |
| Genesis 34 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-b7edc665c15bdc06/chapters/genesis_034/commentary.json` | `811c11c0421822df129b5c693d8c54047dc2a0c510b818eb3731c50385c760cd` |
| Isaiah 36 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-9e3cec1b8c2f60be/chapters/isaiah_036/commentary.json` | `c6b3461fea00d331c7f839ff8310f3081f18298341dad0762a4f9a04acfbfc41` |
| John 4 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-7c306bebfc473aa6/chapters/john_004/commentary.json` | `bac11949ded437702a0e19933a2cb692718c03cadd16b61b68c5ca8581fbed10` |
| Joshua 6 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-26540bca220b999c/chapters/joshua_006/commentary.json` | `74dbb0ee2be044b579af8ea8779d89beeb2d73dadf293decd9ad5ae24f3953a5` |
| Judges 20 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-0595ebb1c627f433/chapters/judges_020/commentary.json` | `e10386a31b8fc9311fd992953f0958353ebee261530b97f960e7c32a00b31129` |
| Matthew 2 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-0c56c7d053fadbec/chapters/matthew_002/commentary.json` | `a4f3f0f115de23a5f94ce99e91a91e7941ff7ffcef588f80c37120d19d745ebf` |
| Numbers 18 | READY_FOR_HUMAN_REVIEW | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-dae7a68dd8db0c99/chapters/numbers_018/commentary.json` | `4a2629a3e8b65a5fb99c3bbc972572e4e45a0341dcd6df46e9fdf4d8333c58c6` |
| Ruth 1 | INVALID_ARTIFACT | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/model-render-001/corpus-runner/runs/batch-9ae3229dd2fdd5bd/chapters/ruth_001/commentary.json` | `0529d5ddf77b5cfa5fbe1afa2513785cb1e02062384eb00af39c90bf2fae6e76` |

The human-review package is `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/review-package/index.md`; it contains one chapter document per target with old published prose, new candidate prose, evidence deltas, identity hashes, validation errors, and a whitespace-normalized semantic/text diff. The complete provenance is `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/candidate-manifest.json` (SHA-256 `76805975d0490134b188fba3effecbf90cb25644695f21f597c0baff33534c5a`). Candidate-to-C1 evidence/synthesis identity matched 12/12. No control candidate artifact exists.

### Isolation and verification

- Before rendering, C2 recorded every file hash in the published v1.2 release tree: 974 files, tree SHA-256 `9d92742f184a6707f46e597284b0167e4c7b974ea4eec957da1f10cb5efc98f4`. The post-render file map and tree hash are identical.
- `default_commentary_storage_path({"BHF_COMMENTARY_RELEASE": "commentary-v1.2"})` resolves to `.bhf-data/bhf-commentary-v1.2`; the active local runtime defaults to the published v1.1 root. Both paths are published release roots, and neither points to the candidate workspace. No files under the published v1.2 release root were written.
- Controls Psalms 76, Revelation 18, and Acts 16 were reconstructed after rendering. Evidence and synthesis hashes matched C1 for all three; none has a candidate Commentary artifact.
- Tests executed: `.venv/bin/pytest -q tests/canonical_library/test_expansion.py -k 'selective_recompile'` (13 passed, 52 deselected); `.venv/bin/pytest -q tests/test_commentary_v12_reader_provenance_binding.py::test_current_record_reconstructs_to_its_frozen_source_identity` (1 passed); `.venv/bin/pytest -q tests/test_commentary_v12_freeze.py` (11 passed); `.venv/bin/pytest -q tests/test_commentary_v12_current_lineage.py` (6 passed); `.venv/bin/pytest -q tests/test_transaction_c_commentary_impact.py tests/test_transaction_c2_commentary_candidates.py` (7 passed). The CKL identity comparison, all 12 candidate identity checks, control reconstructions, and published-tree equality check also passed. `git diff --check` is recorded after the final documentation/test edits.

### Final C2 state

`COMMENTARY_CANDIDATES_PARTIAL_AWAITING_REVIEW`. Eleven valid candidates are ready for human review; Ruth 1 requires attention because its rendered artifact failed existing validation. Nothing is approved. C3, promotion, release-manifest updates, and publication are not started.

## C2R Ruth 1 candidate repair

### Root cause and repair

The original Ruth 1 response was valid JSON, but its five blocks omitted both `confidence` and `interpretation_level`. The reconstructed Prompt 1.8 request requires both fields in the output shape, and its system contract says confidence cannot exceed either cited synthesis or evidence. `parse_renderer_json()` parsed the response without errors. `normalize_renderer_payload_v2()` only resolves the supplied provenance references to evidence/synthesis IDs and preserved the missing fields; it did not remove returned fields or supply defaults. The existing validator correctly rejected the missing required fields. While reporting those errors it used its internal `medium` fallback, which also exceeded the low-confidence evidence and synthesis cited by the disputed-question block. No fallback values were serialized as an accepted candidate.

This was a malformed model response, not a prompt/schema ambiguity or parser, renderer, or validator defect. No production code, prompt, schema, parser, or validator behavior changed. The repair made one new call through the existing `CodexCliV12ChapterPipeline.generate("Ruth", 1)` path with model `gpt-5.6-terra`, high effort, Prompt 1.8, and host-local `codex-cli 0.160.1`. The normal parser, provenance normalizer, and full Commentary v1.2 validator ran unchanged.

### Input identity and candidate result

Before rendering, `prepare_chapter("Ruth", 1)` reconstructed the current CKL packet. It matched C1 and the original C2 manifest exactly:

- Evidence hash: `1224b8fcf887845f926aa765da713e3301c1b5f26f2d9bb8fc9505dc5e0677ba`.
- Synthesis hash: `315fb5e50f38e7f3720f3bbdd574360e7d02e6dc48964b1edd1deae1a9e29969`.
- Evidence IDs: all 17 IDs equal C1's `new_identity.evidence_ids`.
- Synthesis: all 8 current units reproduce the C1/C2 synthesis hash and unit count. Their ordered IDs are recorded in `ruth-repair-001/pre-repair-state.json`; C1 and the initial C2 candidate manifest stored the hash/count, not unit IDs.

The single replacement completed from `2026-10-07T01:16:29.322038+00:00` to `2026-10-07T01:17:04.706021+00:00`, returned `validated`, and passed the complete existing candidate validator. Required confidence and interpretation fields are present; confidence values are valid (`low`, `medium`, or `high`) and the validator confirmed no block exceeds the confidence of its cited evidence or synthesis. The focused confidence regression test also proves missing fields are rejected, invalid confidence values are rejected, and a value above either supporting ceiling is rejected.

The reconstructed Prompt 1.8 payload fingerprint is `d1af8d8dfb422f0c3737f146dce55997cbd30d7df707c8ea04164f39514f9f0c`. The independent post-render confidence audit re-ran the full validator on the persisted replacement and checked all five blocks against the exact current bundle and synthesis; all five passed. The per-block confidence ceilings are recorded in `ruth-repair-001/confidence-validation.json`.

| Ruth 1 attempt | Artifact path | SHA-256 | Result |
|---|---|---|---|
| Initial C2 invalid attempt | `ruth-repair-001/history/ruth-001-invalid-commentary.json` | `0529d5ddf77b5cfa5fbe1afa2513785cb1e02062384eb00af39c90bf2fae6e76` | INVALID_ARTIFACT; preserved with raw response and validator errors |
| C2R replacement | `.bhf-data/bhf-commentary-candidates/transaction-c-commentary-c2/ruth-repair-001/corpus-runner/runs/batch-9ae3229dd2fdd5bd/chapters/ruth_001/commentary.json` | `1b55bf3ec49942bc13eaf3cc58e4583adeeaf7b3786cafcff2eaeba4e353339e` | READY_FOR_HUMAN_REVIEW; not approved |

The C2 manifest, Ruth review page, and review index now point to the replacement and retain the first attempt under `superseded_attempts`. The replacement raw response SHA-256 is `25e1043102d13a81c4970c65c58fba22eb59858acfd1d572bf9fdde21f501272`. Its provenance is in `ruth-repair-001/render-result.json`. The eleven other candidate artifact hashes recorded before repair in `ruth-repair-001/pre-repair-state.json` still match the candidate manifest byte-for-byte; none was regenerated or modified.

### Isolation, controls, and verification

- Published Commentary v1.2 remains byte-identical: all 974 paths and SHA-256 values match both the original C2 snapshot and the C2R pre-render snapshot; tree digest remains `9d92742f184a6707f46e597284b0167e4c7b974ea4eec957da1f10cb5efc98f4`. The production reader still resolves `.bhf-data/bhf-commentary-v1.2` when v1.2 is selected.
- Psalms 76, Revelation 18, and Acts 16 were reconstructed after rendering. Their current evidence/synthesis hashes match their unchanged C1 identities, and there are no control candidate artifacts. Full identities and the reconstruction comparison are in `ruth-repair-001/control-verification.json`.
- Candidate-set and C1 identity checks still prove exactly the original 12 chapters are present, every candidate input hash matches C1, and all twelve now have `READY_FOR_HUMAN_REVIEW`. No candidate is approved.
- Added `test_confidence_fields_are_required_valid_and_bounded_by_all_support` in `tests/test_commentary_v12_validation.py`. It checks required fields, valid confidence values, and the evidence and synthesis confidence ceilings. Prompt 1.8's existing confidence constraint test remains unchanged.
- Tests executed: final combined C1 impact, C2 candidate, Commentary validation, and Prompt 1.8 run `.venv/bin/pytest -q tests/test_transaction_c_commentary_impact.py tests/test_transaction_c2_commentary_candidates.py tests/test_commentary_v12_validation.py tests/test_commentary_v12_prompt_18.py` (38 passed); `.venv/bin/pytest -q tests/test_commentary_v12_corpus_runner.py tests/test_commentary_v12_codex_cli.py` (34 passed); `.venv/bin/pytest -q tests/canonical_library/test_expansion.py -k 'selective_recompile'` (13 passed, 52 deselected); `.venv/bin/pytest -q tests/test_commentary_v12_freeze.py tests/test_commentary_v12_reader_provenance_binding.py::test_current_record_reconstructs_to_its_frozen_source_identity tests/test_commentary_v12_current_lineage.py` (18 passed). The tests include the eleven-artifact hash comparison, 12-candidate cardinality/input identities, published release isolation, reader path, confidence invariant, and control assertions. `git diff --check` passed after the final edits.

### Final C2 state after repair

`COMMENTARY_CANDIDATES_READY_FOR_HUMAN_REVIEW`. All 12 selective candidates are ready for human review and none is approved. C3, promotion, release-manifest changes, and publication are not started.

## Transaction state

```text
Transaction A = CKL_COMMITTED
Transaction B = DERIVED_RUNTIME_NOT_SEPARATELY_REQUIRED
Transaction C1 = SELECTIVE_INPUT_IMPACT_VERIFIED
Transaction C2 = COMMENTARY_CANDIDATES_READY_FOR_HUMAN_REVIEW
Published Commentary v1.2 = UNCHANGED
Commentary candidates = 12 (12 READY_FOR_HUMAN_REVIEW, 0 approved)
C3 / promotion / publication = NOT STARTED
```
