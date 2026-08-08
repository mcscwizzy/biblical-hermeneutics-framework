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
record is, its date/period, location, source, confidence, and cautions. CKL
objects may explain relevance and scholarly context, but detailed media
catalog data does not belong in universal CKL prose.

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
`bhf_agent/archaeology_import.py`; the current fixture provider is intended
for reviewed local fixtures and tests.

```bash
python tools/import_archaeology.py \
  --provider fixture \
  --manifest data_sources/archaeology/manifest.json \
  --database .bhf/study.sqlite
```

Future Wikimedia Commons, Open Context, Met Open Access, or Smithsonian
providers must normalize external IDs, source provenance, and image rights
before calling the existing media repository. Evidence-source rights and
image/media rights must remain separate.

## Offline behavior

The optional `archaeology` offline pack contains text metadata, Scripture
relationships, coordinates, source information, and only explicitly
redistributable/cacheable media. Unknown, remote-only, and link-only media
are excluded. The pack is not required for the PWA core.

## Adding a record or media

Reuse existing site/item IDs. Add Scripture links only when the relationship
is specific enough to avoid generic collisions. For media, provide a stable
ID, exactly one item/site relationship, source URL, rights state, license
metadata, and attribution where required. Validate the record before review;
do not add an image merely because it is visible on a public website.
