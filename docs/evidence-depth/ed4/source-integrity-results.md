# ED-4 source integrity results

## Source-support targets

The current deep CKL report still returns 102 invalid-source-support-target
signals, the same total as the ED-4 baseline. The strict validator remains
unchanged. The ED-3 investigation classified those signals as 45 exact claim
IDs in other objects, 14 existing top-level fields, 24 generic field/category
labels, and 19 semantic targets without an exact local or global target. These
are different diagnostic classes; none was suppressed or reclassified as a
valid claim link.

The 19 unresolved rows were traced to the following exact object/source/target
triples. Target strings below are reproduced from the CKL and the ED-3 audit.
No exact target ID was found in the originating object or elsewhere in the CKL.

| Originating object | Source ID | Target(s) | Disposition |
|---|---|---|---|
| `pauline-women-coworkers-prophecy-and-assembly-authority` | `keener-acts` | `acts-enslaved-girl-exploitation` | Unresolved; the Acts source context does not establish the intended target identity. |
| `roman-athens-agora-cult-and-philosophy` | `ascsa-agora-athens` | `classical-agora-public-space`; `roman-athens-urban-layering` | Unresolved; the object has related evidence, but neither exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `ministry-agora-areopagus` | `classical-agora-public-space` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `ministry-roman-agora` | `roman-athens-urban-layering` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `rogers-roman-athens` | `roman-athens-urban-layering` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `pausanias-phaleron-unknown` | `unknown-god-comparanda` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `van-der-horst-altars` | `unknown-god-comparanda` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `epicurus-diogenes` | `epicurean-comparison` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `aratus-phaenomena` | `stoic-poetic-comparison` | Unresolved; no exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `atkinson-stoics-epicureans` | `epicurean-comparison`; `stoic-poetic-comparison` | Unresolved; neither exact target exists. |
| `roman-athens-agora-cult-and-philosophy` | `cowan-paul-socrates` | `unknown-god-rhetorical-use` | Unresolved; no exact target exists. |
| `judges-cycle` | `butler-judges-cycle-2009` | `interpretive-disputes` | Unresolved; this category-like target is not an exact claim or evidence ID. |
| `athens` | `athens-acts-text` | `athens-canonical-scene` | Unresolved; no exact target exists. |
| `athens` | `athens-first-thessalonians-text` | `athens-itinerary-limits` | Unresolved; no exact target exists. |
| `athens` | `roman-athens-cambridge` | `athens-civic-continuity` | Unresolved; no exact target exists. |
| `athens` | `atkinson-athenian-philosophers` | `athens-philosophers` | Unresolved; no exact target exists. |
| `athens` | `keener-acts-athens` | `athens-canonical-scene` | Unresolved; no exact target exists. |

The complete machine-readable row inventory is the ED-3
[source-support-target audit](../ed3/supporting/source-support-targets.csv).
Some Athens labels resemble evidence descriptions, but resemblance does not
establish identity or a one-to-one relationship. No target was guessed, and
no CKL `supports` values were changed. These 19 rows remain research tasks for
the author or a reviewer who can supply the intended support mapping.

## Bibliography identity review

The ED-3 sparse bibliography inventory contained 558 IDs: 472 Scripture/text
identities and 86 reference-work-like identities. The 86 were not treated as
86 proven defects. Their deterministic triage included Scripture or passage
labels, institutional/catalog/artifact identities, collection/topic labels,
metadata variations, and ambiguous identities. No Scripture IDs were
mass-renamed.

High-impact identity checks found several object-local ID collisions rather
than a safe global rename:

- `aune` identifies different works in different book objects.
- `bauckham` identifies the same Jude/2 Peter commentary in those objects but
  a different Revelation monograph in Revelation.
- `burnett-imperial-honors` identifies distinct authors and works in
  Thessalonians and Philippians.
- `bdag` consistently names the 2000 lexicon, but its author-role wording,
  publisher URL, and locator styles vary across book objects. The current
  University of Chicago Press catalog identifies Walter Bauer and says the
  edition was edited and revised by Frederick William Danker
  ([publisher catalog](https://press.uchicago.edu/ucp/books/book/chicago/G/bo3622223.html)).
  It does not resolve whether each older object URL is an edition-specific
  valid record, so those URLs and passage/lemma locators were preserved rather
  than bulk-normalized.

One precise bibliographic defect was verified and corrected in
`malachi.json`: the author field for `patristic-minor-prophets` incorrectly
read “Ondrey, H. Clifton Ward.” The Oxford book page and the publication
preview identify the author as Hauna T. Ondrey. The preview gives a defensible
but limited locator, the introduction's pages 10–11, where the book briefly
discusses Cyril and Theodoret on Malachi ([OUP book page](https://academic.oup.com/book/11063),
[publisher-distributed preview PDF](https://api.pageplace.de/preview/DT0400.9780192559449_A35502642/preview-9780192559449_A35502642.pdf)).
The CKL record now states that the preview does not provide verse-by-verse
Malachi coverage. Its source ID, year, support categories, and all scholarly
claims remain unchanged. No page number was inferred beyond the printed
pagination in the preview.

## Before and after

| Check | ED-4 baseline | After Phase 3 | Result |
|---|---:|---:|---|
| CKL objects | 687 | 687 | Unchanged |
| Strict CKL errors | 0 | 0 | Unchanged |
| Strict CKL warnings | 14 | 14 | Unchanged |
| Deep source-support-target signals | 102 | 102 | Unchanged; no warning suppression |
| Unresolved child-source references | 0 | 0 | Unchanged |
| Source IDs changed | — | 0 | None |
| Human-review decisions recorded | 0 | 0 | None |

The one source-record correction is metadata and locator text only. It does not
alter the queue, reviewer packets, source IDs, claim/evidence IDs, source-lock
inputs, or human-review state. The frozen curation artifacts are checked again
in Phase 4 and final release validation.
