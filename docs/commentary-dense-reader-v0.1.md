# Dense Reader Synthesis v0.1

Dense Reader Synthesis is an isolated post-pilot reader experiment. It exists
because the accepted Commentary 1.5 artifact is intentionally comprehensive
and auditable, while a human reader may benefit from fewer repeated frames and
more coherent paragraphs in dense chapters.

## Pipeline boundary

The layer sits strictly after accepted Commentary 1.5:

```text
accepted Commentary 1.5 (schema 1.2)
  -> deterministic Dense Reader Synthesis v0.1 sidecar
  -> reader presentation artifact
```

The current UI is not changed. It still consumes the existing
`project_commentary()` projection. This experiment writes candidate-only files
under `.bhf-data/bhf-commentary-candidates/commentary-dense-reader-v0.1/`.

Commentary 1.5 remains the evidence-rich audit artifact. Dense Reader
Synthesis is only a reader-facing presentation artifact and never replaces the
source, CKL, EvidenceBundle, synthesis packet, or source provenance.

## Contract and provenance

Each reader unit contains its section identity, readable text, verse-reference
union, evidence-ID union, source Commentary block IDs, source synthesis IDs,
source idea-cluster IDs, and diagnostic quality classes. The artifact records
the exact source Commentary path and SHA-256, source prompt/schema identities,
transform version, and a deterministic artifact identity.

When blocks are merged, provenance is the union of every mapped source block's
evidence IDs, verse refs, and synthesis IDs. In active chapters, v0.1 may omit
only explicitly diagnosed low-value single-record background repetition; the
omitted source block IDs are recorded and validated, and CORE blocks may never
be omitted. Restrained controls map every source block. The validator rejects
unknown block IDs, evidence IDs, references, empty units, duplicate unit IDs,
incomplete mapping/omission accounting, hash drift, and omission of source
CORE synthesis IDs.

## Consolidation behavior

The transform does not call a model and does not add outside knowledge. It
removes repeated section framing, collapses an exactly duplicated word-half
when present, removes exact repeated sentences within a merged unit, and joins
blocks only within the same section when they share an existing idea cluster,
share evidence with meaningful lexical overlap, or are near-duplicate text.
In active chapters it may also omit only a low-value single-record generic
background block; those omissions are labeled in the artifact and are
prohibited for CORE/disputed blocks. Unrelated blocks remain separate. No
fixed word cap or first-N-block rule is used.

Source metadata distinguishes CORE, disputed, supporting, surrounding, and
optional classes using the existing richness classifier. These are retention
and uncertainty diagnostics, not theological rankings. CORE source clusters
have absolute priority; lower-value explanatory repetition is where
consolidation is expected to help.

Activation is adaptive. A dense or long chapter alone is not enough. v0.1
activates when a dump, low-coverage, or low-utilization signal is paired with
another stress signal such as high block or word count. Chapters with long,
well-utilized, non-dump source commentary remain restrained.

The experimental dump metric is separate from Gate v2.1: it evaluates the
reader-unit/idea-cluster shape and records the raw diagnostic alongside the
reported reader severity. Restrained controls retain their source dump status
so a presentation denominator cannot create a false warning.

Philippians 1 is therefore an important control: it is long but has perfect
source coverage/utilization and no dump warning. It should not be compressed
merely because it is dense. Romans 8 is the complementary warning: the reader
sidecar may improve coherence, but it cannot repair the source's missing
weighted coverage or invent evidence.

## Activation criteria for future study

Use the ten-chapter results to test a future rule combining density/high block
shape with dump severity or low weighted/utilization coverage. Do not activate
globally on `density == 41+`, word count alone, or reader preference alone.
The experiment is not production approval and does not authorize full-corpus
generation or UI integration.
