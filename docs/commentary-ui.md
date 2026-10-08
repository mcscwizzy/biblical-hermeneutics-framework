# BHF Commentary UI

**BHF Context** is the CKL-backed BHF Commentary, currently served from the
immutable `commentary-v1.2` release as an optional, read-only context layer in
the Study Companion. It can show contextual synthesis, cited evidence, verse
references, maps, canonical objects, and personal actions. It is separate from
Tyndale's published study notes and from Scripture translation comparison.
The reader and Scripture remain primary; BHF Commentary is a concise aid for
understanding the world behind the text, not a replacement for Scripture or a
theological authority.

## Read-only release boundary

The UI consumes immutable `commentary-v1.2` artifacts through a presentation
projection. It does not write commentary files, regenerate chapters, or
retrieve replacement evidence. A future corpus release must use a new release
identifier so cached content cannot be confused with v1.2.

## Availability states

- `AVAILABLE` — **Context available**. The chapter has anchored contextual
  evidence and can show the normal context card.
- `THIN` — **Limited contextual evidence**. The card remains available but
  makes the limited evidence visible.
- `DATA_GAP` — **Contextual evidence not currently available**. Scripture and
  stored canonical observations remain readable, while evidence controls are
  omitted; the UI never substitutes semantic or unrelated CKL results.
- Missing legacy metadata — **Context status not recorded**. The UI preserves
  the missing value and does not infer a state.

Availability describes evidence coverage, not theological or prose quality.

## Reader and API routes

The Study Companion loads the chapter projection from:

```text
GET /api/bhf-commentary/{book}/{chapter}
```

Evidence exploration is progressive disclosure and is limited to evidence
explicitly cited by that chapter:

```text
GET /api/bhf-commentary/{book}/{chapter}/evidence
```

The beginner view shows the claim, category, confidence, dispute note, and
Scripture anchor. Advanced details expose the cited record's ID, assertion,
interpretation levels, sources, and related entities. Unknown cited IDs are
shown as unavailable; no substitute retrieval is performed.

Commentary discovery uses the existing reader search surface:

```text
GET /api/bhf-commentary/search
```

It supports chapter, verse, book, availability, category, entity, and period
filters. Internal coverage review is read-only at
`/internal/commentary-coverage` and
`/api/internal/bhf-commentary/coverage`.

## Offline behavior

Chapter and cited-evidence responses use the existing BHF offline database and
service worker. Cache entries are checked for the current release identifier;
older commentary releases are ignored rather than displayed as current.
Uncached commentary or evidence fails with the normal offline state. No model
call is required to read cached release content.

## Separate reader features

- **BHF Context** presents CKL-backed BHF Commentary from the current v1.2
  release.
- **Tyndale Companion** is the independent published Tyndale Open Study Notes
  reader pane; it remains available through its own workspace tab and API.
- **Compare translations** displays parallel Bible text from translations that
  the existing reader reports as installed and readable. It uses the reader's
  chapter data and offline cache, and never installs or imports a translation.

## Integration boundary

Commentary links into existing BHF destinations such as Context, Maps,
Timeline, History, Culture, Archaeology, Lexicon, Notes, Highlights, and
translation comparison. Those tools remain their own destinations; the BHF
Commentary card does not duplicate their data or create a separate commentary
application.

Future UI work should happen on a UI branch and should preserve the frozen
corpus boundary. CKL expansion, commentary regeneration, schema changes, and
validation changes are separate workstreams.
