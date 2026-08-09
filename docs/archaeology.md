# Archaeology Evidence

BHF archaeology has three boundaries:

1. SQLite archaeology records are deterministic evidence and relationship data.
2. CKL archaeology objects are curated interpretation and context.
3. The reader and map workspace present retrieved evidence; AI is optional explanation.

Archaeology should be described responsibly. A record may support historical
context, demonstrate the existence of a person/place/practice, or provide
comparative evidence. It should not be described as proving a theological
conclusion unless a specific claim and evidence genuinely warrant that wording.

## Storage and retrieval

Existing `archaeology_sites`, `archaeology_items`, and
`archaeology_scripture_links` records remain the canonical deterministic
index. `archaeology_media` stores zero or more media records for one existing
item or site. Passage resolution prioritizes Scripture-link overlap, then
carefully matched canonical names, and returns at most eight cards.

The existing map service remains the map implementation. Archaeology cards use
the existing map workspace and stable item/site IDs.

## Evidence versus interpretation

Evidence records describe what an artifact, site, inscription, or excavation
record is, its date/period, location, source, confidence, and cautions. Each
enriched item also carries structured `evidence_details`: what is physically
present, discovery context, dating basis, evidence summary, passage relevance,
scholarly context, current location, an interpretive caution, and reviewed
external provenance references where applicable. Blank fields remain blank
rather than being filled with generated prose. CKL objects may
explain relevance and scholarly context, but detailed media catalog data does
not belong in universal CKL prose.

User-facing confidence should remain qualified: strong evidence, probable,
possible, or disputed. The `bhf_caution` field is shown with the card rather
than hidden from the reader.

## Media rights policy

Internet accessibility is not redistribution permission. Every media record
has a rights state:

- `public_domain`, `cc0`, `cc_by`, `cc_by_sa`, or `other_redistributable` may
  be bundled only when `can_redistribute` and `can_cache` are both true.
- `remote_display_only` and `link_only` remain outbound metadata only.
- `unknown` fails closed: it cannot be bundled, cached, or copied locally.

CC BY and CC BY-SA records require attribution metadata. Attribution survives
API serialization, online cards, and permitted offline packs. Missing or
invalid licenses must fail validation rather than silently permit copying.

The UI never proxies arbitrary third-party images. It renders only media that
has explicit redistribution/cache permission; otherwise it provides source
and rights metadata or an outbound source link.

## Importing records

Imports are explicit and manifest-driven. Application startup does not crawl
provider APIs. The provider interface lives in
`bhf_agent/archaeology_import.py`. `WikimediaCommonsProvider` uses the
MediaWiki API for candidate searches and exact reviewed-file metadata; it does
not scrape rendered HTML or select the first search result automatically.

The initial reviewed file manifest is
`data_sources/archaeology/wikimedia-manifest.json`. It maps one stable Commons
`File:` identifier to one BHF item ID. It currently covers Tel Dan, Mesha,
Siloam, the Black Obelisk, Cyrus Cylinder, the Pools of Siloam and Bethesda,
Lachish, Caesarea, Jericho, Capernaum, and Qumran.

```bash
python tools/import_archaeology.py \
  --provider wikimedia \
  --manifest data_sources/archaeology/wikimedia-manifest.json \
  --database .bhf/study.sqlite
```

The importer fetches canonical source and image URLs, thumbnails when Commons
provides them, creator/credit, license name and URL, external file ID, and
dimensions. It normalizes only public domain, CC0, CC BY, CC BY-SA, and a
reviewed explicit attribution-only Commons license as reusable. Unknown and
non-free metadata remain non-cacheable and non-redistributable.

When adding an image: choose the exact file during review, record it in the
manifest, run the import against a clean database, inspect the rendered card
and attribution, and keep the evidence source separate from the image source.
The fixture provider remains available for isolated importer tests.
`MetOpenAccessProvider` is also available for exact reviewed object IDs. It
imports only records whose API payload says `isPublicDomain: true` and includes
a primary image; its initial manifest is
`data_sources/archaeology/met-manifest.json`.

Open Context's Iraq Heritage Program is represented as reviewed local
provenance metadata in
`data_sources/archaeology/opencontext-provenance-manifest.json`. The public
project JSON-LD record is CC BY 4.0 and is rendered as an outbound data-source
link for relevant Nimrud records. No live Open Context provider runs at startup
or study time: individual subject JSON endpoints were browser-challenge
protected during evaluation, so a runtime fetch would not be dependable or
compatible with deterministic retrieval.

The cross-period corpus review is recorded in
`data_sources/archaeology/corpus-expansion-manifest.json`. It adds the
Merneptah Stele, Shoshenq I's Karnak relief, the Arad ostraca, the Temple
Warning inscription, and the Gallio inscription. Each record preserves a
reviewed institutional or academic source URL and a specific interpretive
caution. Each now also has one exact reviewed reusable Commons image, with
its media ID, file page, and license recorded in the same manifest.

`data_sources/archaeology/babylon-context-manifest.json` records the separate
source review for the text-first Babylon / Ishtar Gate context record. It is
linked narrowly to Daniel 1. Its associated 1932 Library of Congress Commons
photograph is separately rights-reviewed and is a visual aid only.

## Offline behavior

The optional `archaeology` offline pack contains text metadata, structured
evidence details, Scripture relationships, coordinates, source information,
and only explicitly redistributable/cacheable media. Unknown, remote-only,
and link-only media are excluded. The current pack exports reviewed media
metadata and URLs; a later downloader can choose bounded thumbnails without
changing the rights boundary. The pack is not required for the PWA core.

## Adding a record or media

Reuse existing site/item IDs. Add Scripture links only when the relationship
is specific enough to avoid generic collisions. For media, provide a stable
ID, exactly one item/site relationship, source URL, rights state, license
metadata, and attribution where required. Validate the record before review;
do not add an image merely because it is visible on a public website.

## Implementation status

Infrastructure is complete, and the content/media expansion is now populated
with 31 substantive archaeology records, 31 reviewed media records (28
Wikimedia Commons files plus 3 Met Open Access public-domain images), and
reviewed Open Context project-level provenance for three Nimrud records. Every
current substantive record has one reviewed reusable image. The Babylon/Ishtar
Gate image is a 1932 public-domain Library of Congress photograph of the gate
at Babylon, rather than a later museum reconstruction.
