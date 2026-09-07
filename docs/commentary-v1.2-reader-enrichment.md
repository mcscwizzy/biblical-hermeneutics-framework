# Commentary v1.2 — Reader Enrichment

Commentary v1.2 is implemented as a candidate-only enrichment pipeline. The
certified v1.1 runtime corpus remains the active rollback baseline and is not
modified by this work.

## Architecture

```text
CKL / archaeology / geography
  -> EvidenceBundle 1.1 + evidence_hash
  -> CompiledChapterSynthesis 1.0 + synthesis_hash
  -> Commentary prompt/schema 1.2
  -> deterministic commentary validation
  -> v1.2 candidate workspace
```

`EvidenceBundle` remains the evidence layer. `CompiledChapterSynthesis` is a
deterministic organization layer: it groups only evidence joined by authored
entity, parent-object, or significance links; carries exact evidence facts,
anchors, entities, confidence, and dispute state; and records coverage and
gaps. It does not call a model and does not write polished reader prose.

Reader commentary receives canonical text, synthesis units, and a compact list
of permitted evidence citations. It does not receive an invitation to use
outside model knowledge. Commentary blocks cite both synthesis IDs and evidence
IDs. The validator proves that cited evidence descends from the cited units,
that confidence and dispute state are not upgraded, and that `why_it_matters`
prose cites a compiler-approved relationship unit.

Application-owned generation provenance contains:

- evidence hash and EvidenceBundle version;
- synthesis hash, schema version, and compiler version;
- commentary schema and prompt versions;
- model and generation timestamp.

Evidence, synthesis logic, schema, or prompt drift makes a candidate stale.

## Richness versus validity

The v1.2 richness audit does not treat `validated` as meaning `rich`. It reports
validation status independently from:

- `RICH_ENOUGH`: supported evidence is materially represented;
- `SYNTHESIS_GAP`: meaningful evidence exists but prose underuses it, remains
  minimal, or relies heavily on fallback language;
- `EVIDENCE_GAP`: deterministic evidence availability/specificity is inadequate
  for responsible enrichment.

The thresholds are serialized into every JSON audit. The audit also records
evidence and entity counts, category diversity, specificity, section/block and
prose size, verse-anchor coverage, used and unused evidence IDs, fallback
phrases, boundary-verse repetition, and validated-but-thin output.

Run the full read-only audit with:

```bash
.venv/bin/python tools/commentary_richness_audit.py
```

It writes only beneath:

```text
.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/audit/
```

The targeted CKL backlog is descriptive. It never populates or edits CKL.

## Canary gate

The bounded matrix contains the twelve requested torture cases plus Numbers 3,
an observed `DATA_GAP` control. Prepare and validate deterministic synthesis
locks with:

```bash
.venv/bin/python tools/commentary_v12_canary.py prepare
```

Prose generation requires an explicitly identified Terra Medium environment:

```bash
BHF_COMMENTARY_MODEL_OWNER=terra \
BHF_COMMENTARY_MODEL_EFFORT=medium \
.venv/bin/python tools/commentary_v12_canary.py generate
```

The configured provider model must also identify Terra. Unsupported model
substitution is a hard blocker and is recorded in candidate state.

Create or refresh the comparison report with:

```bash
.venv/bin/python tools/commentary_v12_canary.py compare
```

Full-Bible generation remains disabled unless all canaries exist, validate,
retain complete provenance and hash locks, introduce no deterministically
unsupported claims, materially improve appropriate `AVAILABLE` chapters, keep
`DATA_GAP` output conservative, and keep the genealogy control concise.

## Candidate boundaries

All v1.2 audit, synthesis, prose, and gate artifacts live under
`.bhf-data/bhf-commentary-candidates/commentary-v1.2-enrichment/`. Runtime path
resolution remains pinned to `commentary-v1.1`. The v1.1 publisher,
certifications, fingerprints, candidate sources, runtime files, and CKL objects
are unchanged.
