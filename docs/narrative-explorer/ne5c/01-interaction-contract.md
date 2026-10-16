# NE-5C interaction contract

## Scope

NE-5C makes existing Narrative Explorer projection items and authored CKL links
openable inside the Study Companion. It does not produce interpretations,
change CKL, or add a projection endpoint. The projection schema remains `1.0`.
The production feature flag remains off by default.

## Trail steps

The trail is passage → projected evidence item → CKL subject or linked passage.
The current passage projection is the only evidence source for an evidence
detail. Its exact projected ID is retained, including the CKL parent and local
child ID (for example,
`ckl:genesis-flood-postflood-context#evidence:g6-sons-of-god-interpretive-positions`).
The view reads that item's fields directly and does not substitute its parent's
summary.

Following a recorded CKL object edge uses
`GET /api/canonical/objects/{id}`. The client checks that the returned `id`
matches the requested ID and that the response is a CKL subject detail. A
missing, deprecated compatibility response, offline response, or identity
mismatch leaves the trail in place and presents an unavailable state with
return controls. Other claims on the opened subject are not evidence for the
originating passage unless their own anchors support that use.

Scripture destinations must match a canonical book in the reader's book list,
fall within that book's chapter range, and have a valid positive verse range.
Valid destinations go through BHF's existing reader navigation. An unsupported
or malformed reference remains visible as text with a reason and gets no link.

## Depth and cycles

The trail allows at most three authored relationship hops. Opening an evidence
item does not consume a hop. Each CKL subject edge and each linked passage
consumes one hop. The UI displays the current count and disables further
destinations at the limit. Session history is bounded to twelve trail nodes;
the origin is retained when that bound is reached.

The client stops a destination already present in the trail, including passage
cycles. It does not expand or draw the CKL graph. Connection lists are sorted
by stable edge ID and render twelve entries at a time. Subject Scripture anchors
and related object links also render in pages of twelve.

## Relationship semantics

The projection's validated connection categories are shown using their
existing labels. The original CKL relationship label, endpoints, direction,
recorded notes, basis, anchor, interpretive status, and temporal layer remain
visible when supplied.

An `uncategorized` edge is called a **descriptive association** and retains its
exact CKL label. It is not presented as an established intertextual link.
One-way edges only navigate in their recorded direction. An edge is shown as
reciprocal only when its projected reverse edge exists, points to the original
source, and points back to the current edge. The canonical detail endpoint
does not provide the projection's validated category or reciprocal metadata;
its authored `related_object_links` are therefore shown as descriptive
associations with their original labels.

No edge is inferred from shared wording. Labels are not upgraded to quotation,
borrowing, fulfillment, dependence, or historical development. A Scripture
link records a destination; it does not assert that both passages have the
same theological meaning.

## Other destinations

Existing archaeology and Maps actions continue through the resource router.
Physical map focus still requires a supported map target and displayable
identification or geometry. Non-displayable coordinates are not placed in the
detail view. Cosmic or sacred-space concepts do not become map markers.
