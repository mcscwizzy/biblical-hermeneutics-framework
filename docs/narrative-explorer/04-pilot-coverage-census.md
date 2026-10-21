# Narrative Explorer: Pilot Coverage Census

> Historical pilot census. It records retrieval and route snapshots from the
> pilot implementation and is not the current NE-9C/NE-10 registry inventory.
> Use the [current overview](README.md) and current CKL source for present
> behavior.

## Method and scope

This census was run against the checkout at b9812fd0236cc2341fd4b777fe92b009dfb05c8b. It uses the existing Companion service and local runtime data contract; it is not an HTTP session against a production deployment.

Reproducible method:

1. Load CKL through the same default repository path used by CompanionContextService.
2. For each pilot chapter, capture the full candidate set using retrieve_by_scripture_reference(reference, limit=100, include_placeholders=False), then apply is_canonical_object_passage_eligible to reproduce the eligible-object IDs. The Companion summary itself is capped at twelve canonical summary rows.
3. Call CompanionContextService.build(book=..., chapter=...) with local .bhf-data/study.sqlite, after require_current_study_database succeeds, to capture the live-capable response and visible-card projection.
4. Use PresentationEngine(cache=MemoryPresentationCache()) and provider=None, so packet generation stays local/deterministic and does not call a paid provider. Map and archaeology links are chapter lookups against the existing Study DB.
5. Independently inspect source JSON for object IDs, claim/evidence/source metadata. Direct map and archaeology counts were cross-checked with SQLite mode=ro queries against place_references, route_references, and archaeology_scripture_links.

The local Study DB schema was confirmed current before reading. No CKL, map, archaeology, release, or source records were changed. canonical_count is the Companion eligible-object count; it is not an endorsement, scholarly review decision, or count of direct claims.

## Coverage summary

| Pilot | Eligible CKL objects | Theme entities | Map places / routes | Archaeology-service records | Cross-reference count | Current presentation cards |
|---|---:|---:|---:|---:|---:|---|
| Genesis 1 | 19 | 6 | 0 / 0 | 0 | 46 | 3: ordered-world observation; significance; ANE comparative context |
| Genesis 2 | 14 | 3 | 8 / 0 | 0 | 70 | 3: dust/adamah/breath; significance; ordered-world observation |
| Genesis 3 | 2 | 1 | 1 / 0 | 0 | 0 | 3: deception/autonomy sequence; significance; serpent characterization |
| Genesis 6 | 7 | 0 | 0 / 0 | 0 | 70 | 2: evil-intention/violence evidence; significance |
| Deuteronomy 32 | 12 | 2 | 12 / 0 | 0 | 29 | 3: divine-assembly interpretive note; Meribah map item; manuscript variant |
| Psalm 82 | 1 | 0 | 0 / 0 | 0 | 3 | 3: divine-assembly interpretive note; Psalm 82 claim; Ugaritic comparison |
| Exodus 3 | 28 | 3 | 3 / 0 | 0 | 25 | 3: Sinai/ANE context; Midian map item; Sinai covenant-encounter theme |

The Companion cross-reference counts aggregate strings from eligible parent objects, and the response returns at most twelve displayed strings. They are not passage-scoped connection counts. Genesis 6's first returned items include Exodus 1, Psalm 105, Isaiah 51, and Matthew 1, even though the selected chapter is Genesis 6. Treat current counts as a retrieval diagnostic, not as a set of navigable, proven intertexts.

## Existing eligible CKL object IDs

These are actual eligible object IDs returned by Companion retrieval. They include broader book-level objects and objects whose relationship to the current question needs a passage-scoped claim/evidence view. Presence in this list does not mean every parent summary field is appropriate to display for this chapter.

### Genesis 1

mesopotamian-creation-and-flood-comparisons, creation, genesis, john, creation-theme, image-of-god-theme, spirit-theme, new-creation-theme, water-and-spirit-theme, creation-doctrine, pneumatology, spiritual-gifts, what-is-the-image-of-god, what-is-the-significance-of-the-holy-spirit, creation-doctrine-framework, what-is-the-holy-spirit, what-does-ruach-mean, light-and-darkness-theme, zephaniah.

### Genesis 2–3

Genesis 2: genesis, mesopotamian-creation-and-flood-comparisons, creation, revelation, creation-theme, sabbath-theme, new-creation-theme, creation-doctrine, 1-corinthians, creation-doctrine-framework, what-does-ruach-mean, what-is-the-significance-of-the-sabbath, ephesians, song-of-songs.

Genesis 3: the-fall, exile-theme.

### Genesis 6

genesis-flood-postflood-context, mesopotamian-creation-and-flood-comparisons, genesis, zephaniah, jude, the-flood, 1-peter.

### Deuteronomy 32

ancient-divine-assembly-imagery, dead-sea-scrolls, temple-mount-area-finds, wadi-murabbaat-scrolls, justice-theme, righteousness-theme, divine-justice, mount-ebal-altar-discovery, qumran-archaeological-site, mishpat, tsedeq, habakkuk.

### Psalm 82

ancient-divine-assembly-imagery.

### Exodus 3

the-exodus, exodus, moses, john, who-was-moses, mount-sinai, adonai, elohim, kyrios, theos, yahweh, egypt, exodus-to-sinai-timeline, glory-theme, presence-theme, water-theme, divine-presence, burning-bush, golden-calf, moses-birth, ammon, canaan, chaldea, edom, midian, moab-1, philistia, syria-1.

## Passage evidence and presentation findings

### Genesis 1 — ordered creation and ancient cosmology

- Existing support: creation-theme, creation, and mesopotamian-creation-and-flood-comparisons are eligible. The comparison object has three claims, three typed evidence items, and five source records. It separates the Genesis textual observation from an Enuma Elish comparison and a Gilgamesh flood comparison.
- Traceable sources: Genesis 1–11 primary text; Wilfred G. Lambert, Babylonian Creation Myths (2013); British Museum Tablet K.3375; Andrew R. George's Gilgamesh edition (2003); Nahum M. Sarna's JPS Genesis commentary (1989).
- Other support: current theme bucket returns six theme objects; deterministic packet has three visible cards. Map and archaeology passage resolvers have no records.
- Gap: theme records include broad canonical themes, but no archaeology-service object is linked to Genesis 1. Ancient literary comparison should be labeled as such, not as excavation confirmation.
- Supported sections: Biblical Narrative; Themes & Biblical Connections; Archaeology & Ancient History only when labeled as ancient textual comparison; Divine Council & Cosmic Geography only for textual cosmology observations actually represented in evidence.

### Genesis 2–3 — Eden and sacred space

- Genesis 2 support: 14 CKL records, three theme entities, eight map-place records, no route, no archaeology-service record, and three deterministic cards. The eligible CKL place bucket is empty; Eden is represented in the map database as an OpenBible.info map record.
- Genesis 3 support: the-fall and exile-theme, one map-place record for Eden, no archaeology-service record, and three cards. Current event/theme relationships include an expulsion/sacred-space trail, but relationship labels are authored free text.
- Map caution: Genesis 2 returns Eden, Pishon, Gihon, Havilah, Tigris, Euphrates, Assyria, and Cush records. These local records include point coordinates and labels such as strong or likely; the point data does not settle identification of Eden or uncertain river courses. Genesis 3 returns the same Eden map identity.
- Gap: no eligible CKL Eden place identity or typed physical-versus-conceptual geography record. Preserve textual Garden and river descriptions without asserting exact locations.
- Supported sections: Biblical Narrative; Themes & Biblical Connections; Biblical Geography with identification uncertainty; Divine Council & Cosmic Geography as textual sacred-space evidence, not a point map.

### Genesis 6 — sons of God, flood, and ANE connections

- Existing support: seven eligible objects include genesis-flood-postflood-context, mesopotamian-creation-and-flood-comparisons, and the-flood. The passage-specific flood context has 25 typed evidence items and 29 source records. They cover sons-of-God positions, Nephilim wording, the 120-year statement, violence, flood, and later reception. Records distinguish biblical wording, interpretive positions, and Second Temple reception.
- Comparative source: the Mesopotamian comparison object records the Gilgamesh Tablet XI source and explicitly says shared motifs do not establish direct literary borrowing or identify Noah's flood archaeologically.
- Current UI result: Companion returns zero theme entities but has two evidence-backed deterministic cards. Study DB archaeology and map resolvers both return zero.
- Verified cause of theme gap: data exists in passage-anchored cultural_background and event objects, but _canonical_context only places object type theme in entities.themes. This is a presentation-bucket gap, not evidence that CKL is empty for Genesis 6.
- Additional retrieval issue: Companion reports 70 cross-reference strings by aggregating parent records; leading returned examples are not Genesis 6 links. A new projection must filter at claim/evidence scope.
- Supported sections: Biblical Narrative; Archaeology & Ancient History for ancient-text comparisons and later textual reception, with evidence kinds distinguished; Divine Council & Cosmic Geography for Genesis 6:1–4 textual evidence and competing readings; Themes & Biblical Connections only for recorded links with an explicit basis.

### Deuteronomy 32 — nations and textual variants

- Existing support: 12 eligible CKL records include ancient-divine-assembly-imagery, five archaeology-typed CKL objects, two theme records, and manuscript/textual evidence. The council record contains the Deuteronomy 32:8 variant and ties it to ulrich-biblical-qumran-scrolls-2010.
- Map support: 12 chapter-linked place records; no route. Local map data includes point records for Mount Nebo and Mount Hor with possible confidence, alongside other chapter places. These are chapter-level links, not proof of a territorial boundary in the song.
- Archaeology service: zero linked records for this chapter, despite CKL objects and a manuscript-source record. A Study DB archaeology count of zero does not erase CKL textual-witness evidence.
- Current UI result: two theme entities and three packet cards, including a manuscript-variant card. The card surface can show the variant, but resource categorization does not convey the whole object/source path.
- Supported sections: Biblical Narrative; Themes & Biblical Connections; Biblical Geography with chapter-level scope shown; Archaeology & Ancient History for manuscript/source evidence; Divine Council & Cosmic Geography for the textual variant and distinct interpretive proposals.

### Psalm 82 — council imagery

- Existing support: the only eligible object is ancient-divine-assembly-imagery. It contains Psalm 82 textual claims, typed evidence, Ugaritic comparison, and sources by Mark S. Smith and Theodore J. Lewis. It distinguishes the Psalm's poetic scene from a single modern reconstruction.
- Current UI result: no theme, person, place, or event entity; three packet cards cite the interpretive note, Psalm 82 assembly claim, and Ugaritic comparison. Map and archaeology resolvers return zero.
- Verified cause of theme gap: evidence is in a cultural_background object, not a theme object, and entity bucketing does not place this type in the theme category. Data is present; current categories/card summaries do not expose it as a theme trail.
- Supported sections: Divine Council & Cosmic Geography; Themes & Biblical Connections only as an evidence-linked motif/interpretive trail; Archaeology & Ancient History for ancient comparative texts, not a physical-site record.

### Exodus 3 — holy ground and divine presence

- Existing support: 28 eligible CKL objects include Moses, burning-bush, mount-sinai, presence-theme, divine-presence, the-exodus, and a timeline. Packet returns three cards; entity buckets contain one person, thirteen combined CKL/map places, three themes, and five event/timeline entries.
- Map support: Egypt, Midian, and Mount Horeb are returned from the map database; Horeb is labeled possible. No route and no archaeology-service record are linked to the pilot chapter.
- Narrative relationships: burning-bush and mount-sinai link to Moses and later Exodus/Sinai events through authored CKL relationships. Those labels are useful but not all part of a controlled edge vocabulary.
- Supported sections: Biblical Narrative; People, Events & Relationships; Biblical Geography with Horeb/Sinai identification status; Themes & Biblical Connections; Divine Council & Cosmic Geography for textual presence/sacred-space observations.

## Current user-facing surfaces

- The main Companion has Walk the Land, Did You Know?, and Why It Matters Here packet sections. It shows card confidence/interpretation level and an expandable evidence list for card evidence IDs.
- entities provides compact people, place, theme, group, and event chips. It does not itself include full source or claim detail.
- resource-router.js opens maps, archaeology, people, places, themes, timeline, cross-references, and context views. Canonical object detail is separately available through /api/canonical/objects/{id}.
- The separate BHF Context card loads immutable chapter Commentary and can request linked evidence. Tyndale Study Notes uses the distinct /api/commentary service.
- Ask BHF remains optional, not an evidence category or generated Commentary renderer.

## Coverage decisions for the prototype

Build categories only where this census supports them:

- Show comparative texts for Genesis 1/6 and Psalm 82 as ancient textual evidence, not archaeology-site confirmation.
- Show Genesis 6 and Psalm 82 cultural-background evidence in a relevant thematic/cosmic lens even though the legacy themes bucket is empty.
- Show map coverage with stored identification limits; do not present Eden's point as an established Garden location.
- Show Deuteronomy 32 textual-witness data from CKL even though the separate archaeology service has no passage result.
- For empty archaeology-service sections, say no linked archaeology-service record is represented for this passage; do not say archaeology disproved or never investigated it.
- Filter book-wide inherited relationships before offering passage-specific trails.
