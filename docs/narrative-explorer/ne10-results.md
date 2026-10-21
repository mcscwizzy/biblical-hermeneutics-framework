# NE-10 implementation results

## Coverage and pathways

The baseline projection had no dedicated passage-to-passage route section. It exposed authored edges and their existing evidence trail, so some readers could follow a connection through CKL subject pages. Passage pairs documented only inside claims, evidence, or interpretive notes did not appear as direct passage destinations.

NE-10 adds a separate **Related Biblical Passages** section to the existing passage projection and trail. It exposes **382 distinct destinations from existing authored CKL relationships** across the corpus. This count joins all 433 exact NE-9C curated relationship identities to live CKL edges, then counts destination passages whose exact one-chapter scope is supported by the curation. The read-only NE-10 registry adds **43 verified CKL-documented passage bridges**, independently checked against the exact supporting records and their attached sources. It also records **7 research candidates held out** of the confirmed route list.

In the ten required representative passages, the existing authored pathways produced 27 route rows (27 unique routes), while evidence-backed bridges produced 8 rows (7 unique bridges, since a reader can start from either endpoint). Before NE-10, 0/10 views had a consolidated passage-destination list. After NE-10, 7/10 had at least one route, 6/10 had an evidence-backed bridge, and 5/10 had an authored relationship pathway. The three views without routes—Deuteronomy 32, Psalm 82, and Isaiah 43—display an explicit coverage caveat; they do not imply that no relationship exists. Ezekiel 37 keeps its existing authored pathways and does not gain the unverified John 3 proposal.

| Passage view | Existing authored routes | CKL-documented bridges |
| --- | ---: | ---: |
| Genesis 1 | 5 | 1 |
| Genesis 3 | 3 | 3 |
| Genesis 6 | 0 | 1 |
| Deuteronomy 32 | 0 | 0 |
| Psalm 82 | 0 | 0 |
| Job 1 | 1 | 1 |
| Isaiah 43 | 0 | 0 |
| Ezekiel 37 | 4 | 0 |
| John 1 | 0 | 1 |
| Revelation 21 | 14 | 1 |

The [evidence-discovery audit](ne10-evidence-discovery-audit.md) documents the full cluster review, inventory counts, and all held candidates. NE-9C decisions remain unchanged: validation reports 3,925 reviewed relationships, with 408 curated, 1,895 held, and 1,622 excluded.

## Representative reader journeys

- **Genesis 1 → John 1:** The route is labelled a thematic interpretive association. It shows the John claim, exact CKL source IDs and bibliography, and uncertainty about conceptual genealogy. The reader can return to Genesis 1 through the existing trail.
- **Genesis 3 → Revelation 12:** The route identifies later canonical reception. Its explanation says Revelation names the ancient serpent as the devil and Satan, while Genesis 3 itself does not name those figures.
- **Genesis 6 → Jude 1:6:** The route identifies the ancient comparative and reception context. It links a scoped Genesis evidence record and Jude interpretive note, and says the Watchers reading is not stated in Genesis and that Jude does not retell every Second Temple detail.
- **Job 1 → Zechariah 3:** The route is a lexical comparison of *ha-satan*. The trail keeps lexical role, literary function, and later theological identification distinct.
- **John 2 → Ephesians 2 → Revelation 21:** The route uses the CKL sanctuary note and preserves the differences among temple, community imagery, and new creation. Frontend coverage verifies passage navigation, trail provenance, keyboard-operable controls, cycle behavior, and return to the original selection.

Shared parent, source, topic, keyword, or passage anchor alone does not create a route. Tests include two distinct passage claims in one CKL parent with shared bibliography and no bridge record, as well as a record whose Scripture scope only partially overlaps the bridge endpoint.

## Performance and packaging

The production-like benchmark used the JSON CKL repository fallback because this worktree has no SQLite CKL index. It loaded all 687 CKL objects and projected the ten representative passages.

| Measurement | Result |
| --- | ---: |
| JSON CKL load time | 28.43 s |
| First passage projection | 971 ms |
| Median passage projection | 404 ms |
| Maximum passage projection | 1.10 s |
| Median full JSON response | 145,059 bytes |
| Maximum full JSON response | 476,775 bytes |
| Median added `related_passages` payload | 6,380 bytes |
| Maximum added `related_passages` payload | 50,562 bytes |

The maximum response is Revelation 21, which has 14 existing authored pathways and one bridge. The cold load measurement covers the existing JSON fallback path, not a production indexed startup. The benchmark script records per-passage timing and payload size and counts active authored routes across the corpus.

The wheel build succeeded, and inspection confirmed it contains both the bridge registry and held-candidate JSON. No new runtime dependency was added.

## Verification

- Focused Narrative Explorer, curation, bridge, provider, and projection-parity suites: **546 passed**.
- Full Narrative Explorer API suite, including Genesis 1/3/6, Deuteronomy 32, Psalm 82, Job 1, Isaiah 43, Ezekiel 37, John 1/2, Ephesians 2, and Revelation 21: **23 passed**.
- CKL schema, package, loader, source-lock, typed-evidence, Scripture-reference, and evidence-architecture suites: **181 passed**.
- Frontend suite (`npm test`): **12 passed**.
- NE-9C curation validation: **passed**, with the original disposition counts above.
- NE-10 passage-bridge registry: every route resolves to its exact current CKL record, exact source IDs, and both supported passage scopes.
- Wheel package inspection: both NE-10 JSON files included.
- `git diff --check`: passed.

The feature is committed and pushed on `feat/narrative-explorer-ne10-evidence-trails`. It has not been deployed or merged.
