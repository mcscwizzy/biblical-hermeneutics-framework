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

## Final passage-bridge acceptance

Acceptance audited the existing **43** bridge records against the relationship thresholds in the [evidence and connection contract](03-evidence-and-connection-contract.md). All 43 still resolve to their specified CKL claim, evidence item, or interpretive note, the record-attached source IDs and bibliography, and both scoped Scripture passages. **32 classifications are retained, 11 are corrected, and none of the 43 is held.** This acceptance did not add or remove a bridge.

### Classifications retained

The unchanged category assignments are:

| Classification | Bridge IDs |
| --- | --- |
| `direct_quotation` (10) | `mark-1-exodus-23-20`, `mark-1-malachi-3-1`, `mark-1-isaiah-40-3`, `mark-11-isaiah-56-7`, `mark-11-jeremiah-7-11`, `amos-5-acts-7-quotation`, `amos-9-acts-15-quotation`, `genesis-15-romans-4`, `galatians-3-genesis-12-3`, `galatians-3-genesis-15-6` |
| `interpretive_association` (6) | `genesis-1-john-1-creation-word`, `genesis-6-jude-1-watchers-reception`, `job-1-zechariah-3-accuser`, `isaiah-53-mark-10-ransom`, `daniel-7-mark-13-son-of-man`, `nahum-1-romans-10-parallel` |
| `later_canonical_reception` (7) | `genesis-3-revelation-12-serpent`, `hosea-11-matthew-2-son-egypt`, `hosea-13-first-corinthians-15`, `isaiah-7-matthew-1-immanuel`, `isaiah-53-acts-8`, `isaiah-53-1-peter-2`, `micah-3-jeremiah-26-reception` |
| `shared_literary_motif` (3) | `micah-4-isaiah-2-zion`, `exodus-34-nahum-1`, `nahum-1-isaiah-52-messenger` |
| `thematic_relationship` (6) | `genesis-3-exodus-25-cherubim`, `genesis-3-kings-6-cherubim`, `sanctuary-tabernacle-first-temple-presence`, `sanctuary-first-temple-john-temple-presence`, `sanctuary-john-temple-ephesians-community`, `sanctuary-ephesians-community-revelation-new-creation` |

### Classifications corrected

| Bridge | Previous | Accepted | Acceptance reason |
| --- | --- | --- | --- |
| `exodus-12-numbers-33-egypt-gods` | `explicit_textual_reference` | `thematic_relationship` | Exodus 12:12 and Numbers 33:4 connect the departure with judgment on Egypt's gods; the mention of gods is not a reference to another biblical text. The passages do not identify individual gods or map them to particular plagues. |
| `exodus-40-leviticus-1-continuation` | `narrative_parallel` | `shared_literary_motif` | The scoped texts continue the tent-of-meeting scene across the book boundary. The evidence does not support a parallel-plot claim or quotation/dependence. |
| `luke-3-psalm-2-variant` | `explicit_textual_reference` | `direct_quotation` | The Psalm 2:7 wording is present in a variant of Luke 3:22, supported by Codex Bezae and patristic evidence; most witnesses retain the Synoptic-form declaration. The route is explicitly textual-critical. |
| `habakkuk-2-romans-1` | `explicit_textual_reference` | `direct_quotation` | Romans 1:17 reproduces the identifiable Habakkuk wording; it is a quotation rather than merely naming a source text. |
| `galatians-3-deut-21-23` | `explicit_textual_reference` | `direct_quotation` | Galatians 3:13 quotes the Deuteronomy wording. |
| `galatians-3-deut-27-26` | `explicit_textual_reference` | `direct_quotation` | Galatians 3:10 quotes the Deuteronomy wording. |
| `james-2-gen-22` | `explicit_textual_reference` | `later_canonical_reception` | James interprets the Abraham episode in a later scriptural argument; it does not explicitly identify Genesis as a written source. |
| `james-2-josh-2` | `explicit_textual_reference` | `later_canonical_reception` | James interprets Rahab's episode as an example; naming Rahab does not itself constitute an explicit textual citation. |
| `hebrews-7-genesis-14` | `interpretive_association` | `later_canonical_reception` | Hebrews 7 takes up Genesis's Melchizedek episode and develops it in a later canonical argument. |
| `hebrews-7-psalm-110` | `interpretive_association` | `direct_quotation` | Hebrews 7:17 quotes the priest-forever oracle in Psalm 110:4. |
| `jude-2-peter-literary-relation` | `narrative_parallel` | `proposed_intertextual_echo` | The claim records extensive wording and sequence parallels but leaves dependence direction and mechanism disputed; these are not parallel narrative plots. |

The seven entries in `research-candidates-held.json` remain outside the confirmed graph: `deuteronomy-32-psalm-82-job-1-divine-assembly`, `isaiah-43-exodus-12-15-new-exodus`, `ezekiel-40-48-revelation-21-22-temple`, `ezekiel-37-john-3-water-spirit`, `exodus-12-1-corinthians-5-passover`, `psalm-110-acts-2-enthronement`, and `genesis-2-3-revelation-21-22-eden-tree-life`. No held proposal was promoted or rewritten.

### Direction and passage scope

All 25 `source_to_receiving_text` routes now carry explicit `source_text_passage` and `receiving_text_passage` fields independent of the reader's current endpoint. Reverse navigation changes the route destination only; it does not reverse the source-to-receiver claim. This includes the composite Mark 1:2-3 citation: Exodus 23:20, Malachi 3:1, and Isaiah 40:3 remain source texts, with Mark 1:2-3 the receiving text. The Luke 3:22 variant is oriented Psalm 2:7 → Luke 3:22. Thirteen previously reversed source/receiver endpoint pairs were corrected, including Mark 1, Mark 11, Galatians 3, James 2, and Hebrews 7.

Where a supporting record identifies a narrower scope, the registry now uses it: John 1:1-5, Numbers 33:4, Hosea 11:1 / Matthew 2:15, Hosea 13:14 / 1 Corinthians 15:54-55, Isaiah 56:7 and Jeremiah 7:11 / Mark 11:17, Daniel 7:13-14 / Mark 13:26, Isaiah 7:14 / Matthew 1:22-23, Isaiah 53:7-8 / Acts 8:32-35, Amos 9:11-12 / Acts 15:16-18, and Habakkuk 2:4 / Romans 1:17. Ranges remain broad only where the attached CKL claim itself is broad, including Genesis 14 and Psalm 110 in Hebrews 7.

### Preservation and reader checks

The NE-9C validator still reports the unchanged 4,061 inventory identities and 3,925 reviewed relationships: 408 curated, 1,895 held, and 1,622 excluded. The protected CKL object-tree fingerprint remains `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766`. The 25 legacy curations are unchanged: `batch-001.json` SHA-256 `2854d091672fe84d42235c9932ba0cf74f6eff081959be990cf5818bc44362cb` and `batch-002.json` SHA-256 `93417bb87b9900c4f6eb7e7699fb7b59f2bf734382bf023759d6a686910c9e3b`. All seven held NE-10 proposals are unchanged. The bridge tests resolve all 43 records and exercise navigation from both endpoints (86 endpoint checks), source/receiver direction, cycle prevention, the three-hop ceiling, return-to-origin, and negative cases for shared parent, source, keyword, or anchor alone. Browser checks cover Back/Forward restoration and mobile width; route choices remain native keyboard-focusable buttons and disclosure controls.

The ten-passage production-like JSON fallback benchmark completed with 687 CKL objects: cold load 29.57 s, first projection 1.01 s, median projection 427 ms, maximum projection 1.12 s, median full payload 145,098 bytes, maximum 476,775 bytes, median related-passage delta 6,380 bytes, and maximum delta 50,562 bytes. This is the JSON fallback measurement; the hosted Preview acceptance separately checks the packaged SQLite backend.

The Firefox desktop history/return journey passed after the reader exposed its current passage in the explorer header. The Firefox keyboard journey opened Genesis 1 → John 1 with Enter, preserved the interpretive-association label without inventing a one-way direction, and returned to Genesis 1 with the selected verse restored. The companion mobile explorer test passed as well.

### Hosted Preview and final verification

The final branch Preview matched the acceptance commit and loaded its packaged SQLite CKL index for Genesis 1, Genesis 3, Genesis 6, Job 1, Mark 1, and Revelation 21. All six CKL queries completed; maps and archaeology reported independent runtime-unavailable states and were not counted as missing CKL evidence. The exact deployment URL and commit SHA are included in the final delivery report.

Acceptance regressions: Narrative Explorer API, bridge, curation, projection, and schema-package suites **568 passed**; broader CKL schema, loader, source-lock, typed-evidence, scripture-reference, storage, and index-lifecycle suites **205 passed**; packaged Vercel-index tests **10 passed**; frontend suite **12 passed**; Firefox desktop history, keyboard journey, and mobile companion tests **3 passed**. The NE-9C validator passed with its original inventory and dispositions. A wheel built successfully using installed build tools after the isolated build could not fetch dependencies offline; inspection confirmed both NE-10 JSON files are packaged. `git diff --check` passed. No unrelated repository test failure remained.
