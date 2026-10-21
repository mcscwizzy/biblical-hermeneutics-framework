# NE-10 evidence-discovery audit

## Baseline and method

The audit was run on `origin/master` at `c3aba86ec82cfe014c4f596a3c8bb136f2bb8fea`. I read the Narrative Explorer projection and browser trail, the CKL evidence and source models, the NE-9C registry and validation report, and the connection audits including [NE-9C prioritized candidates](connection-audit/06-prioritized-candidates.md). The NE-9B rank-one sibling-evidence navigation fix is already present: projected CKL evidence targets are resolved and the reader can follow them through the existing evidence trail. NE-10 leaves that path in place.

The current CKL inventory contains 687 objects, 4,061 `related_objects` edges, 305 `related_evidence` edges, 2,329 claims, 1,297 evidence items, 3,691 interpretive notes, and 5,232 source records. It has 4,631 top-level Scripture-reference entries and 11,433 reference entries when every nested `scripture_references` array is counted recursively. It also has 805 top-level `cross_references`, 693 `intertextuality` entries, and 374 `new_testament_connections` entries. There is no `intertextual_connections` field. The recursive reference total includes the top-level entries; nested copies and typed child references are preserved as separate corpus entries.

A corpus scan found 222 claims, 126 evidence items, and 133 interpretive notes with references to more than one biblical book. This is a discovery sweep, not a relationship count: multi-book scope by itself did not qualify any route. Each promoted bridge was checked against its exact CKL record identity, both canonical passage scopes, the record's attached source IDs, and the parent object's bibliographic entries. References found only in a parent's cross-reference, keyword, topic, or later-reception fields were recorded as candidates rather than promoted.

The audit also read the authored `related_objects` and `related_evidence` graph, claims, evidence, interpretive notes, Scripture anchors, sources, free-text cross-references, intertextuality, New Testament connections, and later canonical reception metadata. The main discovery gap was projection and presentation: CKL can contain a passage pair in one scoped claim or evidence item, but the passage projection returns only relationships attached to a current CKL edge. The reader could inspect evidence previews and then move through subject pages, yet had no compact list of destination passages with provenance and uncertainty.

## Separate route classes

### Existing authored CKL relationships

These remain the `connections` projected from CKL `related_objects` or `related_evidence`, carrying original source and target IDs, direction, relationship type, edge basis, and NE-9C curation. The new route projection only presents the curated supporting passage destinations. It does not add or change authored edges or curation decisions.

### CKL-documented passage bridges

The versioned [NE-10 passage bridge registry](../../framework/canonical_library/curations/narrative-explorer/ne10/passage-bridges.json) contains 43 separately projected routes. Each names exact supporting CKL claim, evidence, or interpretive-note records, the source IDs attached to those records, category, direction, evidence layer, explanation, and uncertainty. Unidentified interpretive notes use a content-hash locator and are explicitly presented without a standalone CKL record ID. The resolver validates all 43 entries against the current CKL corpus.

The registry has 32 claim-backed route records, 4 evidence-backed route records, and 8 note-backed route records across 31 distinct CKL record identities (44 support-record references total because the Genesis 6/Jude route combines two records). They come from 19 CKL objects. Categories remain separated: direct quotations and explicit textual references; literary and thematic comparisons; later canonical reception; textual-critical variants; and lexical or ancient-comparative evidence. Interpretive associations are never labelled as direct quotation or borrowing. Runtime verification requires each exact passage scope to be contained in a supporting record's Scripture scope or named explicitly in its text; mere overlap is insufficient.

The registry deliberately keeps original setting and later reception visible. For example, the Genesis 3 serpent route says Revelation 12:9 makes the later identification; it also says Genesis 3 itself does not name Satan. The Genesis 6/Jude route includes both a scoped Genesis evidence item about later 1 Enoch/Jubilees reception and a Jude note about common readings, while warning that the later Watchers details are not in Genesis and are not all retold by Jude. The sanctuary routes compare distinct referents and do not make Eden, tabernacle, temple, Christological metaphor, community imagery, and new creation interchangeable.

### Research candidates held out of the graph

Seven suggested pathways are documented in [the held research-candidate list](../../framework/canonical_library/curations/narrative-explorer/ne10/research-candidates-held.json). They remain unavailable as confirmed reader routes. These include the Deuteronomy 32/Psalm 82/Job 1 heavenly-being cluster; Isaiah 43 and the Exodus; Ezekiel 37 and John 3; Ezekiel 40-48 and Revelation 21-22; Exodus Passover and 1 Corinthians 5; Psalm 110 and Acts 2; and Eden/tree-of-life imagery in Revelation. Each entry identifies what CKL says and what exact passage-level claim or source evidence is still missing.

## Research cluster findings

- **Creation and new creation:** Genesis 1 and John 1 are connected by a scoped Johannine claim that names both passage scopes and the wider Jewish wisdom/word setting. The route is an interpretive association and marks direct borrowing as debated. Genesis 1's existing NE-9C authored pathways remain in the authored group. No Genesis 1/Revelation 21 bridge was inferred from a shared creation theme.
- **Divine assembly and heavenly beings:** Genesis 6/Jude 1 is connected through a clearly labelled reception route that preserves the Second Temple layer. Job 1/Zechariah 3 is shown as a lexical comparison about *ha-satan*. Deuteronomy 32/Psalm 82 remains held because a common CKL parent, topic, or divine-assembly vocabulary does not establish a specific relation.
- **Exodus and restoration:** Exodus 12/Numbers 33 is supported by a claim explicitly connecting the departure and judgment on Egypt's gods. Exodus 40/Leviticus 1 is supported as narrative continuation. Hosea 11/Matthew 2 is a later figural reception that preserves Hosea's Israel referent. The new-exodus claim on Isaiah 40-55 scopes Isaiah passages but does not name a particular Exodus passage, so that candidate remains held.
- **Temple and divine presence:** Genesis 3:24 is connected to Exodus 25 and 1 Kings 6 through a scoped cherubim/sacred-space evidence item. A separate sanctuary interpretive note supports a four-route sequence across Exodus 25, 1 Kings 8, John 2, Ephesians 2, and Revelation 21; its explanation keeps their referents distinct. Ezekiel's Revelation 21-22 metadata is retained as a candidate until an exact scoped claim/evidence record with its own sources is available.
- **Messiah and kingship:** The registry includes Luke 3:22's Psalm 2:7 textual variant, Isaiah 7/Matthew 1 reception, Daniel 7/Mark 13 interpretation, Isaiah 53 reception in Mark, Acts, and 1 Peter, Hebrews' Genesis 14/Psalm 110 reading, plus several explicit apostolic quotations. The Psalm 110/Acts 2 route remains held because the available Psalms metadata gives a broad list rather than a passage-pair claim.

## Reader coverage

Before NE-10, the projection had no `related_passages` field or dedicated passage-destination list. Readers could reach some paths through existing connection previews, exact edge inspection, and CKL subject navigation, but they could not see the authored routes and scoped claim-based routes together from a passage view. NE-10 adds a dedicated section to the same projection and invokes the existing `onOpenPassage` callback, trail state, browser-history navigation, cycle detection, hop limit, keyboard controls, and return-to-origin behavior.

For the ten representative API passages Genesis 1, Genesis 3, Genesis 6, Deuteronomy 32, Psalm 82, Job 1, Isaiah 43, Ezekiel 37, John 1, and Revelation 21, the checked API projection produced 27 authored route rows and 8 evidence-backed route rows across the ten views (27 and 7 unique route IDs, respectively, because a bridge appears from either endpoint). Six views had at least one evidence-backed bridge; five had authored pathways; seven had at least one passage route. Deuteronomy 32, Psalm 82, and Isaiah 43 did not gain evidence-backed bridges from generic similarity. Exact route IDs, per-view response sizes, and test results are in the [NE-10 results report](ne10-results.md).

## NE-9C preservation

NE-10 does not edit CKL object records, NE-9C decisions, or the NE-9C curation inventory. The new bridge and held-candidate files are separate read-only presentation data. Candidate routes do not enter the confirmed registry, and neither bridge selection nor runtime resolution overrides held or excluded NE-9C decisions.
