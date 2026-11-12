# ED-5 representative reader journeys

The suite selects exact records from the current CKL projection before treating
them as fixtures. It includes disputed, source-limited, historical, literary,
lexical, archaeological, ordinary-language retrieval, verified-connection,
and no-eligible-material cases.

| Journey | Exact expected record / target | Acceptance condition |
|---|---|---|
| Genesis 6 | `ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions` | Genesis 6:1–4 anchor and attached sources; disagreement remains marked. |
| Genesis 12 | `ckl:genesis#claim:genesis-blessing-for-families` | Genesis 12:1–3 anchor and record-attached sources. |
| Psalm 145:13 | `ckl:psalms#evidence:psalm-145-nun-verse-witness` | Exact verse, witness sources, and textual-variant status. |
| Psalm 82 | `ckl:ancient-divine-assembly-imagery#claim:psalm-82-assembly-text` | Exact passage and CKL-attached textual/interpretive source identities. |
| Deuteronomy 32:8–9 | `ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant` | Exact scope and textual-variant sources. |
| Jonah 1:17 → Matthew 12:40 | `jonah-1-17-matthew-12-40-sign-of-jonah` | One verified route at each endpoint, source-to-receiving direction, exact support, explanation, and uncertainty. |
| 1 Corinthians 11:3 | `ckl:1-corinthians#claim:1cor-kephale` | Exact verse, lexical sources, and disputed status. |
| 1 John 3:19–24 | `ckl:1-john#claim:1jn-heart` | Exact scope and sources; ordinary question “What if our heart condemns us?” ranks `1-john` first. |
| John 10:22 | `ckl:john#evidence:john-10-22-dedication-term-and-winter` | Exact verse and abstract-limited status retained. |
| Obadiah 1:7 | `ckl:obadiah#interpretive-note:sha256-b9c2e9d3224b9cec78d0ed51b5167898f7cda70e186801cd2c5f7a1df2708812` | Unique exact note identity, verse anchor, and attached sources; no broader passage substitution. |
| 2 Kings 18:13 | `ckl:sennacherib-prism#claim:prism-judah-campaign` | Exact 2 Kings 18:13–37 applicability and Taylor Prism source. |
| 1 Kings 2 | Negative case from current chapter census | Complete lookup, zero eligible CKL items, `not_represented` coverage. |

Reproduce with:

```bash
.venv/bin/python -m pytest tests/test_ed5_reader_evaluation.py -q
.venv/bin/python scripts/ed5_reader_evaluation.py --output /tmp/ed5-reader-evaluation.json
```

The evaluator verifies unique projected record identity (including the
Obadiah note), exact applicability anchors, expected source IDs, the selected
disagreement metadata, first-result retrieval, and
the verified bridge in both directions. It does not infer human
comprehension, report browser clicks, or inspect live maps/archaeology; those
lookups are injected as completed empty results to isolate deterministic CKL
projection. A failed external lookup and a completed empty result remain
different states in the production service.
