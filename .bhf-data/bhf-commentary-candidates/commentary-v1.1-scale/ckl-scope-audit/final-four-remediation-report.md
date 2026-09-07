# Commentary v1.1 Final-Four Routing Remediation

The unchanged Luna High hardened preflight independently evaluated all 257 historical quarantine chapters. All 257 passed; the normal maximum batch size remains 150. Terra was not invoked and no prose was generated.

## Root cause and fix

The legacy evidence projection discarded the authored claim before deriving a presentation role, so it defaulted the affected legacy fields to `historical_context`. The audit’s broad textual fallback then interpreted the incidental phrase `textual transmission` in generic archaeology background as manuscript evidence. This was a general routing/projection false positive, not a CKL content defect.

The fix passes the authored claim through legacy role derivation and narrows the textual fallback to actual witnesses, readings, variants, manuscripts, papyri, codices, and named textual traditions. Explicit textual metadata remains authoritative; archaeology material-object guards remain in force.

## Affected chapters

| Chapter | Evidence IDs | Before | After | Terra suppression | Classification |
| --- | --- | --- | --- | --- | --- |
| Deuteronomy 32 | `mount-ebal-altar-discovery:historical_context:0`; `qumran-archaeological-site:historical_context:0` | historical_context; 2 presentation and 2 textual-routing blockers | historical_context; audits PASS | required → false | B/C/F: generic archaeology background, not manuscript evidence |
| Numbers 6 | `ketef-hinnom-silver-scrolls:historical_context:0` | historical_context; 1 presentation and 1 textual-routing blocker | language_literary; audits PASS | required → false | C/D/E: legitimate textual witness, correctly restricted to language_literary |
| Isaiah 40 | `mount-ebal-altar-discovery:historical_context:0`; `qumran-archaeological-site:historical_context:0` | historical_context; 2 presentation and 2 textual-routing blockers | historical_context; audits PASS | required → false | B/C/F: generic archaeology background, not manuscript evidence |
| Psalms 119 | `mount-ebal-altar-discovery:historical_context:0`; `qumran-archaeological-site:historical_context:0` | historical_context; 2 presentation and 2 textual-routing blockers | historical_context; audits PASS | required → false | B/C/F: generic archaeology background, no textual-witness route |

The affected CKL objects retain their canonical identity, source identity, passage anchors, source type, applicability scope, and content. JSON/SQLite evidence IDs and bundle hashes remain in parity. No CKL metadata or citations changed.

## Adjudication

- Recoverable: 257 (253 previously recoverable + 4 final chapters)
- Still quarantined: 0
- Requires CKL remediation: 0
- Data gap: 0
- Presentation-role findings: 7 → 0
- Textual-routing findings: 7 → 0
- Terra suppression signals: 4 → 0
- Parent-scope findings: 0 → 0
- Word-study findings: 0 → 0
- JSON/SQLite parity: clean; hash disagreements: 0
- Protected canary and Batches 001–003 fingerprints: PASS, unchanged
- Terra generation: not invoked

Batch 007 remains at `EVIDENCE_PREFLIGHT` pending. The exact next safe orchestrator command is:

```bash
python3 -m framework.commentary.orchestrator run --model luna --effort high
```

The next stage must still be allowed to proceed through the orchestrator; this remediation does not generate Terra prose or unlock later stages directly.

Detailed machine-readable records are in `final-four-routing-diagnostic.json`, `final-four-root-cause-report.json`, `final-four-remediation-result.json`, and `post-final-four-quarantine-adjudication.json` in this audit directory.
