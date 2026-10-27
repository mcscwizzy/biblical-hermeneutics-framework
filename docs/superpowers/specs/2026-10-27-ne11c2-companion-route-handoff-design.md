# NE-11C2: Verified Evidence-to-Connection Handoff

## Intent

Let a reader open the exact verified Narrative Explorer relationship that
supports a Study Companion discovery. The reader should inspect the route's
explanation, classification, sources, and uncertainty before following it.

## Goals and constraints

- Match a discovery's cited CKL record to a route only by the complete key:
  object ID, record kind, and local record ID.
- Require a route in the verified projection for the selected passage, with
  current route support and provenance intact.
- Reuse the existing Narrative Explorer loader, resource router, passage
  selection, trail, and browser history.
- Keep all CKL and curation inputs unchanged. Do not add a biblical
  relationship or surface held/excluded candidates.
- Preserve existing Companion cards, generic cross-reference actions, source
  disclosures, and feature-flag behavior.
- On missing, incomplete, ambiguous, disabled, or stale data, omit the direct
  action or fall back to the existing generic passage resource.

## Approaches

1. **Use the existing verified projection (chosen).** Add a backward-compatible
   read-only identity mapping to compact Companion evidence. When a cited
   record has a complete identity and Narrative Explorer is enabled, load the
   selected passage through the existing projection client. Offer a direct
   action only for exact support-record matches. On activation, revalidate the
   route ID and identity through the resource router, then focus the route card.
   This reuses the API's curation and provenance gates and avoids a parallel
   route implementation.
2. **Add a route-only API.** This could reduce the projection payload but would
   duplicate route resolution and verification logic and introduce a second
   contract. It is unnecessary because the existing projection already
   carries exact route and support identities.
3. **Match from text, topics, or source IDs.** This is not eligible: those
   fields do not establish the complete canonical record identity and can
   create false positives.

## Design

Companion response evidence will include `ckl_record_identity` only for
structured claims and evidence items whose provenance metadata provides a
parent CKL object and record kind. Legacy fields, source-only evidence, and
records without a standalone local ID will not receive this mapping. Existing
evidence IDs, source labels, and presentation fields remain intact.

When the feature flag is enabled, Study Companion will request the existing
Narrative Explorer projection only if a visible discovery cites at least one
complete mapped identity. It will match those identities against the
projection's confirmed `related_passages` collections: bridge records use
their explicit object/kind/record fields; authored routes use the existing
stable CKL record key. The lookup will require complete route-query status and
will never use headlines, claim wording, topic overlap, source IDs, or passage
co-occurrence as a substitute.

The direct action will carry the stable route ID and exact supporting record
key. On activation, the existing resource router will load the selected
passage projection, validate both values again, and only then initialize the
trail and browser-history entry. The route card will be expanded if needed,
visibly selected, scrolled into view, and keyboard-focused. It will not
automatically follow the destination. Existing route follow and return-to-origin
controls remain responsible for passage navigation.

Request sequence checks and abort signals will discard results after a chapter
change, resource close, or later route activation. If revalidation fails, the
reader receives the existing generic cross-reference action and no empty
Narrative Explorer trail. Narrative Explorer remains feature-flagged.

## Acceptance

- Genesis 1:1–5 to John 1:1–5 matches `john#claim:john-logos`, preserves
  `interpretive_association`, and retains the stated uncertainty.
- Jonah 1:17 to Matthew 12:40 matches
  `jonah#claim:jonah-three-days`, preserves
  `later_canonical_reception` and historical Jonah-to-Matthew direction, and
  appears only for the matching discovery and selection.
- Held/provisional, source-only, topic-only, wrong-parent, wrong-kind,
  incomplete, stale, and disabled cases never create a confirmed handoff.
- All CKL, NE-9C, NE-10, presentation, packaging, Companion, and Narrative
  Explorer protections remain intact.
