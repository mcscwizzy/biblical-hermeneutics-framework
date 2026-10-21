# Narrative Explorer implementation history

This page replaces the completed pre-NE7R3 implementation roadmap. Its staged
plans are preserved in Git history; current routes and inputs are documented
in the [Narrative Explorer overview](README.md).

The shipped explorer uses CKL as its authoritative research source, consumes
NE-9C relationship curations and NE-10 passage bridge records as read-only
inputs, and keeps source identity and uncertainty available to the reader.
Tyndale Open Study Notes, maps, archaeology, translation comparison, private
study records, offline support, and Ask BHF remain separate neighboring reader
workflows.

Generated BHF Commentary was retired in NE7R3. Its old generated endpoints
retain HTTP 410 responses. No future reader rollout or generation step is
described by the superseded roadmap.

See the [historical decisions index](../maintenance/historical-decisions.md)
for NE7R3, NE-9C, NE-10, and immutable release references.
