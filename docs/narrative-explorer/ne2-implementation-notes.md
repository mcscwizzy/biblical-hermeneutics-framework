# Narrative Explorer NE-2 implementation notes

NE-2 adds a pure projection layer at `bhf_agent.presentation.narrative_explorer`.
The caller supplies completed CKL, map, and archaeology lookups. The adapter
does not retrieve records, persist a projection, register a route, or modify any
source object. Its output follows schema version `1.0`.

## Branch baseline

At fetch time, `origin/master` was `b9812fd0236cc2341fd4b777fe92b009dfb05c8b`.
The verified NE-1 design commit `a924d9ee68bf20d1076d3113ee86f90524d31562`
was not an ancestor of master, so this implementation branch was created from
that exact design commit and depends on the unmerged NE-1 design branch.

The regression suite reads committed CKL JSON records as immutable fixtures and
uses in-memory map and archaeology lookups. It does not write to CKL, map, or
archaeology storage.

## Existing contract differences found during implementation

- The map passage resolvers can return records matched from passage wording as
  well as records matched by stored passage references. Some returned records
  do not carry a structured, item-level Scripture anchor. NE-2 excludes those
  unanchored records from the passage projection; the existing map resolvers
  and responses are unchanged.
- Existing map serializers expose generic `confidence` and stored coordinates,
  but do not consistently expose a separate place-identification status or
  identification confidence. NE-2 preserves the stored coordinate and generic
  confidence, reports identification confidence as `unknown` when absent, and
  only marks geometry displayable when an explicit physical-identification
  status supports it. A coordinate alone is not treated as an identification.
- Some archaeology responses flatten Scripture links to reference strings.
  NE-2 parses those references for passage overlap and retains the original
  anchor data when it is supplied. Flattened responses cannot provide
  per-link notes or relation labels beyond fields retained on the record.
- Existing map-place navigation is a collection endpoint rather than an
  item-detail endpoint. NE-2 retains the map item’s stable ID as the navigation
  target and points to the existing collection route. NE-3 should verify the
  final reader navigation against the consuming client.

These limits describe available source contracts; they do not change CKL,
Study Companion, map, archaeology, or other runtime behavior.
