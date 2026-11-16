# Reader Presentation Policy

## Separation from CKL governance

Presentation tier is a deterministic reader-display decision. It is separate
from content status, review status, curation state, certainty, source identity,
and human approval. It cannot change a CKL record or relationship. The policy
is implemented in `bhf_web/static/narrative-presentation-policy.js`, with
record-level evidence in
[`source-verification-results.json`](source-verification-results.json).

## Three tiers

1. **Featured discovery** — exact passage relevance, a substantive observation,
   source text checked at the scope stated, observation separated from the
   proposed interpretation, and material disagreement or access limits stated.
   The initial view presents no more than three; the audited set currently has
   two: Nahum 3:8–9 and Proverbs 15:25.
2. **Available on demand** — legitimate contextual or specialist material with
   an exact anchor and usable source information, or a separately identified
   map/archaeology item. It remains within the existing topic/source flows.
   The policy currently assigns 26 audited ED-3 items to this tier. A map or
   archaeology citation does not by itself establish a Scripture relationship.
3. **Withheld from reader promotion** — inaccessible or insufficiently checked
   audited claims, claims without exact passage linkage or reader-useful
   bibliographic information, and material the policy cannot responsibly
   present as a discovery. Withheld means no promotional card; it does not
   mean false or deleted. There are 71 such audited items.

## Deterministic criteria

For the 99 audited IDs, the checked-in policy tier is explicit per stable CKL
ID. For other evidence, on-demand requires a direct passage anchor and useful
bibliography fields (work identity plus locator/year); map and archaeology
domains remain on demand with an explicit source-to-passage limitation. All
other items fail closed to withheld. Featured wording is separately enumerated
for the two source-rechecked records. There is no automatic promotion based on
draft status, source count, record count, or a shared Scripture reference.

In the overview, the app shows at most three featured discoveries with a
collapsed “How we know” disclosure. The six topic areas and Location quick
glance remain. Topic views hide audited records assigned withheld; their data
remain in CKL and research tools. Connection navigation continues to depend on
the existing verified relationship/bridge pathways, not textual similarity
alone. Location detail and its geographic uncertainty are handled by the
existing location experience.

If no featured record qualifies, the page leads into study topics, original
context, and verified biblical connections when evidence supports them. It
does not describe the absence of a featured item as a research-audit result.
When the CKL reports a completed empty lookup, a separate note preserves the
accurate coverage explanation and clarifies that it reflects current BHF
coverage, not the passage's importance. It does not imply that all Scripture
or scholarship has been searched.

## Source language

Source disclosure names available works and locators, describes relevant
material, and states meaningful access limits. If citation fields are
incomplete, one plain note says so. Reader copy does not describe automated
source checks as human review. For unaudited source items, the UI says the
cited source was not independently checked; it does not assert support. The
language and citations are checked by focused frontend tests and live Chromium
acceptance tests.
