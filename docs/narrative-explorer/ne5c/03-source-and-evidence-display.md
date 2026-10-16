# NE-5C source and evidence display

## Evidence detail

Detail content comes from the selected projection item: source-authored title,
claim text and description, exact projected and parent-qualified identities,
record kind, evidence category, claim/assertion type, passage anchors,
confidence, certainty, dispute and review state, content state, human-review
flag, temporal classification, and the item's recorded rationale. Rationale
fields such as `primary_observation` and `scholarly_interpretation` remain
separate and are not rewritten as a generated summary.

The detail view distinguishes original biblical text, geographic evidence and
identification limits, historical/cultural context, ancient comparative
literature, manuscript witnesses, literary/thematic connections, later
reception, scholarly interpretation, and disputed positions where the
projection provides those fields. Unmapped categories retain their source
category label. Comparative evidence is explicitly not treated as proof of
borrowing, quotation, fulfillment, or dependence. Disputed or human-review
material keeps its recorded status and is not described as verified
scholarship.

Only the selected item is rendered. Parent narrative prose is not copied into
a child detail. If an item has no passage anchors, source IDs, bibliography, or
recorded rationale, the view says that the field was not returned or is not
recorded in CKL.

## Connections

Each projected edge shows its category when validated, original CKL label,
source and target subject IDs, direction, reverse edge ID when verified,
interpretive and temporal status, recorded basis, and available anchor. An
incoming one-way edge is displayed with its direction but has no follow
button. A reciprocal label requires the paired projected edge.

The canonical detail response supplies authored relationship IDs, labels,
notes, and target details, but not the Narrative Explorer connection category
or reciprocal validation. Those links are called descriptive associations;
the original labels are preserved without stronger classification.

## Bibliography

The expandable bibliography uses only source metadata present on the projected
item or canonical detail: title, author, publisher, publication year, locator,
source type, identifier, notes, and verified stored URL. Missing fields are
identified as missing in CKL. URLs are emitted only for existing HTTP or HTTPS
source URLs and open with `noopener noreferrer`. No publisher or retailer link
is synthesized, and no source database or source-detail route is added.
