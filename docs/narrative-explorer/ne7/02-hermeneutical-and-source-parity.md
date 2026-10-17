# NE-7.2 — Hermeneutical classification and CKL source parity

## CKL identity and mutation check

The current CKL corpus has 687 objects. Its identity matches the NE-6R3 source audit:

| Identity | Value |
|---|---|
| Object inventory fingerprint | `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` |
| Source inventory signature | `5f03bdb3701e4cf8beb578933c50679324611b379417493bb3750008e044e5ea` |
| Source manifest fingerprint | `e3207f9e64825167531d08af531fc1aa22e583f9a7b9526feb7e191b9b64cc40` |
| CKL manifest SHA-256 | `334c42fc5245779f22c7e68143a09e3ee8a1c724f74faacd833d088ba7cfc0a4` |
| Verified SQLite SHA-256 | `1636e33e3ae04e44ea67a78d216ae4f63b7080537b4ea327b2eb662e5575d2e7` |

The SQLite database passed `framework.canonical_library verify-db` against the current source root: schema v4, retrieval index v3, 687 objects, 2,329 claims, 5,232 sources, 1,297 evidence records, and 116,334,592 bytes. The protected study database SHA-256 remained `2bd8f59ec0f44cef7dee7da692b9fe80ef21edd6d88cd2af1b57ee7b44f195bf`; a read-only connection reported migration version 37 and `PRAGMA integrity_check = ok`. No CKL record, Commentary source, translation license, or protected study data was changed.

Frozen Commentary v1.2 identities remained the established NE-6R3 values: data tree `5cdae385fe27dbc3e44d8bf330b75ff2b7e627af`, enrichment tree `b01d814aa10554ecd1f547b426d11cb18cc3ab8c`, and CKL object tree `45fb311c694489474702cb2f4b0c8e0f9872d71a`. Commentary was not regenerated.

## Projection contract

All six projection sections were exercised:

1. Biblical Narrative
2. Archaeology & Ancient History
3. Biblical Geography
4. Divine Council & Cosmic Geography
5. Themes & Biblical Connections
6. People, Events & Relationships

Projection/API, coverage, source parity, and browser checks passed for the implemented contracts: CKL IDs remain source identities; details preserve source and bibliography records; Scripture anchors, confidence, dispute, and evidence labels are source-derived; untyped or unsupported relationships are not promoted to authored connections. Empty, partial, and unavailable evidence must remain visibly distinct. A chapter with eligible evidence is not thereby “fully researched.”

Divine council and cosmic geography retain the NE-5A source-specific classifier. Conceptual or heavenly geography is not a physical map coordinate. A shared word or theme alone does not establish a divine-council link, sacred-space identity, or physical location. Scripture, historical evidence, comparative ANE context, interpretation, and uncertainty remain distinct source categories.

## Pilot passages

Counts below are current projection audit counts in order: **eligible CKL items / unclassified eligible items / Scripture-anchored evidence items / interpretive notes**. All listed chapters have `passage_specific_evidence` coverage; that status does not imply complete scholarship.

| Passage | Counts | Source-backed acceptance finding |
|---|---:|---|
| Genesis 1 | 34 / 7 / 2 / 5 | Creation classifications and source boundaries remain visible; comparative context is not converted into a direct textual assertion. |
| Genesis 2 | 36 / 3 / 12 / 5 | Garden/presence evidence includes `ckl:genesis#evidence:g2-garden-planting-presence`. Eden's exact point remains withheld. |
| Genesis 3 | 22 / 1 / 13 / 4 | Sacred-space context is identified by `ckl:genesis#evidence:g3-cherubim-biblical-sacred-space-context`; interpretation does not create a physical location. |
| Genesis 6 | 26 / 0 / 10 / 5 | Sons-of-God positions remain interpretive positions, not a settled historical claim: `ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions`. |
| Deuteronomy 32 | 17 / 2 / 1 / 2 | The manuscript variant is separately sourced at `ckl:ancient-divine-assembly-imagery#evidence:deuteronomy-32-8-manuscript-variant`; textual variant is not silently treated as the sole reading. |
| Psalm 82 | 6 / 0 / 2 / 1 | Assembly-language evidence `ckl:ancient-divine-assembly-imagery#evidence:psalm-82-assembly-language` is distinct from the Ugaritic comparison `...#evidence:ugaritic-council-comparison`; uncertainty remains. |
| Exodus 3 | 33 / 6 / 0 / 3 | Horeb/Sinai identification remains uncertain. The existing sacred-space evidence gap remains visible; no new CKL evidence was added. |
| Acts 7 | 12 / 1 / 0 / 3 | Nile association retains source `openbible-a012705` and Acts 7:19 anchor; association does not establish a confidently identified point. |
| Joshua 1 | 12 / 0 / 0 / 1 | Negeb association retains map source `openbible-a1cb244` and Joshua 1:4 anchor; catalog coordinates do not establish confident identification. |

## Coverage inventory

| Inventory state | Chapters |
|---|---:|
| Passage-specific eligible evidence | 985 |
| No eligible CKL material | 132 |
| Contextual coverage | 68 |
| Entity-only coverage | 3 |
| Incomplete / unknown | 1 |
| **Total** | **1,189** |

Two audit measures must not be conflated: 330 distinct IDs remain in the NE-A2 residual queue, while the current projection-placement audit counts 839 distinct unclassified IDs. Neither value is a count of missing biblical chapters. Thousands of top-level CKL relationships remain without recognized typed labels; unsupported relations are not inferred to make coverage appear fuller. The corpus-level state therefore preserves limited, absent, partial, and unclassified coverage rather than claiming completeness.
