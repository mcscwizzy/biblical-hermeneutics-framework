# NE-A2 Acts 7 map investigation

## Reproduction

The target `openbible-a012705` exists in the stored map-place catalog as **Nile**. Its stored passage association is `openbible-ref-openbible-a012705-45`, reference **Acts 7:19**, relationship `directly_named`, with the note “Imported from OpenBible.info Bible Geocoding Data.” The source is the existing OpenBible.info Bible Geocoding Data catalog.

On the pre-change resolver, a full **Acts 7** lookup returned 53 text matches and omitted this ID. The resolver only tried the stored-reference path when it had no text match. A narrower **Acts 7:18-20** lookup returned four text matches and also omitted it. An isolated **Acts 7:19** lookup had no text match, fell back to passage references, and returned Nile. This reproduces the text-first suppression reported by NE-A1. The chapter and 18-20 wording does not mention “Nile”; the stored Acts 7:19 association is the evidence that supports retrieval.

The map record has a stored representative point at latitude 31.4653, longitude 30.3667. The Narrative Explorer projection marks `place_identification_confidence` as `unknown`, `coordinates_displayable` as `false`, and `coordinate_display_reason` as `physical_identification_not_established`. It retains the stored coordinate as source metadata but does not present it as a precise, established location. Its source confidence rank does not override the projector's physical-identification safety rule.

## Correction and boundaries

Narrative Explorer now opts into additive explicit-reference retrieval for places and routes. The legacy resolver keeps its default text-first/fallback behavior. Results retain resolver source identity and match rationale, deduplicate by stable record ID, and keep original match ordering. The projection still independently requires the map record's own Scripture anchor to overlap the requested passage. Thus a text-only place-name match without an overlapping authored anchor is not admitted by this change.

After the correction, both **Acts 7** and **Acts 7:17-19** return `maps:openbible-a012705` with its Acts 7:19 anchor, source metadata, and uncertainty state. The authored `directly_named` relation remains intact; the code adds no coordinates, identification, certainty, or reverse edge.

The additive lookup also exposes `openbible-a1cb244` (Negeb), whose stored OpenBible.info link is Joshua 1:4, in Joshua 1 and Joshua 1:1-5. This is a second explicit-reference retrieval correction found by the representative-canon parity set. It is recorded as an intentional change in the ledger. It also retains unknown physical identification and non-displayable coordinates.

Tests cover the old default path, additive place and route lookup, stable-ID deduplication, duplicate names, final anchor eligibility, and the Acts 7 API output. The additional retrieval is isolated to Narrative Explorer; no unanchored text-only match enters the final projection.
