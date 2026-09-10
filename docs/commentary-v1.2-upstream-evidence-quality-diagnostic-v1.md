# Commentary v1.2 upstream evidence-quality diagnostic

This is a read-only diagnostic of the five bounded v1.2 cases. It made zero
model calls and did not change CKL data, evidence bundles, production packets,
Prompt 1.8, binding v2, renderer reference presentation v1, or the quality Gate.
The machine-readable artifact is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-upstream-evidence-quality-diagnostic-v1-4bf89c81144e13aad6eae6b3`

## Answer in plain language

The three QUALITY_FAILs are primarily evidence-quality failures, not a
renderer-selection failure. The source path supplies explicit anchors, but
several anchors are semantically poor. The legacy-field evidence bridge then
turns those parent anchors into renderable evidence, and the deterministic
synthesis compiler gives most emitted evidence its own unit. This makes the
packets numerically large without making them chapter-rich.

Psalm 19 is the strongest renderer result among the failures: the two
defensible Torah paths were both selected, while the archaeological noise was
left out. 2 Kings 4 and Psalm 103 are source-limited: there is no omitted
distinct useful claim in their exact legal packets that would plausibly cure
under-explanation.

## Classifications

| Chapter | Primary | Secondary | Renderer assessment |
| --- | --- | --- | --- |
| 2 Kings 4 | A — `CKL_SOURCE_ANCHOR_POLLUTION` | C — `EVIDENCE_BUNDLE_OVERINCLUSION`; D — `SYNTHESIS_OVERINCLUSION`; E — `PASSAGE_COVERAGE_GAP` | `SOURCE_LIMITED` |
| Psalms 103 | F — `REDUNDANCY_COLLAPSE` | C — `EVIDENCE_BUNDLE_OVERINCLUSION`; D — `SYNTHESIS_OVERINCLUSION`; E — `PASSAGE_COVERAGE_GAP` | `SOURCE_LIMITED` |
| Psalms 19 | A — `CKL_SOURCE_ANCHOR_POLLUTION` | C — `EVIDENCE_BUNDLE_OVERINCLUSION`; D — `SYNTHESIS_OVERINCLUSION`; E — `PASSAGE_COVERAGE_GAP`; I — `CANONICAL_TEXT_INTEGRITY` | `GOOD_RESTRAINT` |

Overall root cause: `MIXED`, dominated by CKL anchor pollution and passage
coverage gaps, with evidence-bundle overinclusion, synthesis overinclusion,
and Psalm 103 redundancy materially contributing. No failing case demonstrates
renderer underselection of a genuinely useful current-packet path.

## Retrieval and evidence path

`retrieve_by_scripture_reference()` parses the query into a
`ScriptureReferenceSpan`, uses a book index, and admits an object when one of
its indexed Scripture intervals overlaps the query interval. Ranking uses the
scripture match score and object importance. The SQLite implementation unions
object, evidence, and claim Scripture-reference indexes. The investigation
found no string/token match, relationship expansion, reverse-reference
expansion, or cross-reference expansion in this path.

The important distinction is that overlap retrieval is behaving consistently
with the stored anchors; the stored anchors themselves are the problem in the
suspicious cases. `build_evidence_bundle()` also has a legacy bridge: where a
matched object has no structured child evidence, it emits legacy fields such
as `ancient_near_east_context` and `historical_context` while inheriting the
parent Scripture anchor. Legacy-only word-study objects fail closed and are
recorded as retrieval-only when they contribute no evidence item.

## 2 Kings 4

The live CKL query returned nine objects, all with an overlapping stored
`2 Kings 4:1-7` anchor. Each produced two generic legacy-field evidence items,
so the immutable production bundle contains 18 evidence items, 18 synthesis
units, and 18 fallback paths.

The eight clear false-positive object associations are:

* Anna the Prophetess
* Elijah
* Ezekiel the Prophet
* Isaiah the Prophet
* Jeremiah the Prophet
* Jonah the Prophet
* Nathan the Prophet
* Zechariah the Prophet

Their underlying objects are person profiles whose stored chapter anchor is
the same inherited `2 Kings 4:1-7` relationship; their emitted claims are
generic social-world or canonical-setting text and do not materially explain
2 Kings 4. Elisha is a real chapter character, so the diagnostic does not call
that object a false positive. Its two legacy claims are nevertheless only
generic context, not episode-specific explanation.

The renderer selected only
`render_path_2_kings_004_cdc77fdaa034152a5c0ddd78`, backed by
`elisha:ancient_near_east_context:0` and
`syn_cultural_context_8f8acb881488`. That is good noise restraint, but the
selected path is not strictly useful under the diagnostic's direct/defensible
standard.

Coverage is 7 of 44 verses (15.91%) for any evidence ancestry and 0 of 44
(0%) for genuinely useful ancestry:

| Span | Any evidence | Useful evidence | Selected ancestry |
| --- | --- | --- | --- |
| 1–7 | yes, 7 verses | no | yes, generic Elisha path |
| 8–17 | no | no | no |
| 18–37 | no | no | no |
| 38–41 | no | no | no |
| 42–44 | no | no | no |

Using every genuinely useful current-packet path would not cure the failure:
there are zero such distinct claims. Better explanation requires accurate
episode-level source ancestry for the uncovered spans; canonical-text-only
prose would violate the current ancestry rules.

## Psalms 103

The bundle contains six evidence items and six synthesis units. They originate
from three separate CKL parent objects—`mercy-theme`, `divine-mercy`, and
`grace`—with two deterministic legacy-field derivatives per object. The
historical three are near/exact duplicates of one broad canonical-continuity
claim. The cultural three form one near-duplicate family of broad mercy/grace
background. Cultural versus historical labeling does not create six distinct
reader-useful claims.

The six items all target `Psalms 103:8-13`, which is why the renderer produced
two blocks limited to that span. The current query also returns four
word-study parents (`agape`, `charis`, `eleos`, and `hesed`), but those are
legacy-only retrieval results and contribute no bundled evidence item under the
fail-closed bridge. The exact packet therefore contains no accurate,
chapter-specific synthesis ancestry for the other tested spans; the diagnostic
does not claim that an exhaustive external search was performed.

The packet is numerically dense but substantively thin: 6 raw synthesis units,
2 duplicate/near-duplicate groups, 0 strict distinct useful claims, and 0
useful unselected claims. There are 6 nominal fallback paths, all selected
across the two output blocks.

Coverage is 6 of 22 verses (27.27%) for any evidence ancestry and 0 of 22
(0%) for useful ancestry:

| Span | Any evidence | Useful evidence | Selected ancestry |
| --- | --- | --- | --- |
| 1–5 | no | no | no |
| 6–7 | no | no | no |
| 8–13 | yes, 6 verses | no under strict standard | yes |
| 14–18 | no | no | no |
| 19–22 | no | no | no |

The renderer assessment is `SOURCE_LIMITED`. Selecting every current path
already happened; using the six nominal paths more expansively would repeat
the same two claim families rather than add explanation.

## Psalms 19

The bundle contains 30 evidence items, 30 synthesis units, and 30 fallback
paths. Ten archaeological parents account for 20 generic legacy evidence
items: Kurkh Monolith, Samaria Palace, Ein Gedi Scroll, Samaria Ostraca,
Shiloh excavations, Arad Ostraca, Masada excavations, Pool of Bethesda
excavation, Caesarea Maritima excavations, and Herodium excavations. Each
entered because its parent stored Scripture references include an overlapping
`Psalms 19:1-6` relationship; the emitted material is generic archaeological
background, not a specific explanation of Psalm 19.

The two `what-does-torah-mean` evidence items are defensible context for
`Psalms 19:7-11`, and both were selected:

* `render_path_psalms_019_176748aa532684fce9b0721c804555bde734195666d61fef2dbe8cfc03a8e3fb`
  → `syn_historical_context_05d0e00263c5`
* `render_path_psalms_019_bd733525bd832a667014cb5128831863d53a0a91f6ae5046f928fe47bff36e45`
  → `syn_cultural_context_64555661036b`

Bibliology, inspiration, inerrancy, and Word of God theme are generic context
in this packet. The six word-study retrieval results (`dabar`, `logos`,
`martyria`, `nephesh`, `ruach`, and `shalom`) are recorded as retrieval-only:
the legacy-only word-study guard prevented them from becoming evidence items.

Coverage is 11 of 14 verses (78.57%) for any evidence ancestry and 5 of 14
(35.71%) for useful ancestry:

| Span | Any evidence | Useful evidence | Selected ancestry |
| --- | --- | --- | --- |
| 1–6 | yes, but only generic/false-positive archaeology | no | no |
| 7–11 | yes | yes, Torah context | yes |
| 12–14 | no | no | no |

This is `GOOD_RESTRAINT`, not underselection: the two useful paths in the
packet were selected and no useful path was left unselected. The failure is
therefore a source coverage problem for the first and final Psalm sections,
plus noisy overinclusion upstream.

## Psalm 19 canonical-text integrity

The exact raw authoritative value of Psalm 19:14 in
`bhf_agent/data/asv_bible.json` is:

> Let the words of my mouth and the meditation of my heart Be acceptable in thy sight, O Jehovah, my rock, and my redeemer. Psalm 20 For the Chief Musician. A Psalm of David.

`bible.resolve_chapter()` returns that value unchanged, and
`bible.passage_text()` joins the resolved verse text without introducing the
suffix. The production renderer prompt contains the same suffix. This is real
source Bible-data contamination, not a parser-boundary or prompt-serialization
defect. The canonical data SHA-256 is
`8b171dc6a89d8ce0328879604a0061e47acfea2a27e9fa18ff21b2cf9f3be16d`.

The contamination is recorded as a secondary Psalm 19 finding. It was not
the cause of the selected Torah output's quality failure; the selected output
did not rely on the contaminated final verse.

## Controls

Numbers 2 has two nominal fallback paths with the same two evidence IDs and
one effective disputed sanctuary-comparison idea. One path was selected and
produced 66 words. It can legitimately pass because its evidence is specific,
chapter-wide, materially distinct, and explicitly qualified as disputed. Word
count is not the explanation.

Numbers 1 has four priority paths, a high-confidence chapter-specific source
packet, distinct setting/literary/census/significance claims, and full
chapter-wide ancestry. Its 179 words reflect several different supported
reader functions, not a minimum-length rule. Both controls show that Sol can
be appropriately narrow when the available ancestry is focused and useful.

## Quality Gate counterfactual

For all three failures, the validation record is structurally valid,
provenance-valid, ancestry-valid, readable, coherent, and has no HIGH dump.
The Gate result is nevertheless `QUALITY_FAIL`; the existing bounded-case
diagnostic then records `under_explanation: FAIL` because that field is derived
from a non-PASS Gate result. It is not an independent finding that the prose
was unreadable or that the model ignored a known useful path.

* 2 Kings 4: all genuinely useful current paths = 0. The criterion cannot be
  satisfied by selection alone.
* Psalms 103: all six nominal paths were selected, but they collapse into two
  broad duplicate families. More selection would be repetition.
* Psalms 19: both genuinely useful paths were selected. More selection would
  add archaeology and generic theology, not useful explanation.

Under the current ancestry rules, satisfying the Gate's under-explanation
expectation would require improving source evidence and chapter coverage. It
would otherwise require canonical-text-only explanation or filler, neither of
which is authorized. The Gate is therefore source-sensitive in a way that
appears mismatched for these legally thin/noisy packets, but the Gate itself
was not changed by this diagnostic.

## Smallest next remediation boundary

The smallest defensible boundary is the CKL-to-evidence boundary: audit and
curate Scripture-anchor provenance and the legacy-field inheritance bridge,
then recalculate chapter coverage and duplicate families. Keep Prompt 1.8,
reader-provenance binding v2, renderer reference presentation v1, ancestry
rules, fallback selection, and the Gate unchanged until that source audit is
complete. This diagnostic intentionally stops there.

## Artifact and reproducibility

The artifact contains a manifest, contract identities, exact evidence traces,
retrieval and path traces, synthesis classifications, verse-coverage maps,
duplicate groups, renderer selection comparison, quality counterfactuals,
canonical Psalm 19 integrity data, final machine-readable report, and
checksums. Source bundles, CKL objects, production packets, and contract files
are referenced by stable paths and hashes rather than copied wholesale.
