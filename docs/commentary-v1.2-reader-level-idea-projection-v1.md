# Commentary v1.2 Reader-Level Idea Projection v1

Status: diagnostic prototype; production behavior is unchanged.

## Proposed representation

`reader-level-idea-projection-v1` is a deterministic renderer-input index between
the frozen `CompiledChapterSynthesis` and prose rendering:

```text
CompiledChapterSynthesis + frozen eligible SynthesisIdeaCluster records
  -> reader-level ideas
  -> prompt 1.7 diagnostic input view
  -> renderer (future experiment only)
```

The projection consumes existing synthesis units and the independently computed
`commentary-richness-clusters-v2` / `commentary-richness-policy-v3-reader-relevance`
cluster records. It does not create an evidence store, alter eligibility,
change scoring, rewrite synthesis, or write commentary.

Each projected idea will retain:

- a content-addressed idea ID and projection identity/hash;
- a conservative source-derived label, never an LLM summary;
- `CORE` or `RELEVANT` importance derived from the existing cluster contract;
- category families, cluster IDs, synthesis-unit IDs, and evidence IDs;
- synthesis/evidence hashes, source packet identity, and source-order metadata;
- conservative confidence and dispute status;
- an auditable grouping reason.

## Deterministic grouping rules

Only eligible clusters (`REQUIRED` or `RELEVANT`) enter the projection. Candidate
cluster pairs are considered in stable cluster-ID order and grouped with
union-find only when one of these explainable rules holds:

1. their synthesis or evidence ancestry intersects exactly;
2. a synthesis unit explicitly relates to a unit in the other cluster;
3. they share a normalized authored parent/topic identifier within the same
   passage scope; the authored parent is treated as an existing concept
   relationship, not as a newly inferred theological topic; or
4. their authored facts meet the existing high fact-overlap shape while their
   passage scope and kind-family remain compatible.

Category overlap alone, a shared book/chapter, or a broad theological theme is
never enough. Current-chapter and surrounding-passage records are not merged
across scope in v1. Ambiguous pairs remain separate and are recorded as
ungrouped ambiguity rather than forced into a group.

The first source fact in original synthesis order supplies the label, trimmed at
a deterministic word boundary. This makes labels navigational excerpts from
frozen source text, not free summaries or new conclusions.

## Frozen inspection basis

The local branch is `feat/commentary-v1.2-enrichment` at
`e8b8d737e8972dd4962e74014a01ce1eb01f4833`. `git fetch origin` and checkout
were attempted but the environment rejected writes to `.git`; the local branch
and HEAD were already correct. Existing unrelated worktree changes are
preserved.

The live authorities match the immutable prompt-1.7 packets:

| Reference | Synthesis units | Eligible clusters | Core eligible | Evidence hash | Synthesis hash |
| --- | ---: | ---: | ---: | --- | --- |
| Revelation 21 | 119 | 16 | 0 | `a470ccd9e79bf996b7b7a31161313c149d8de6e571ef0216f62242c2d91489ba` | `750ad9065279a515f8cd7388fbe7c53eea26020881f9224aa828bf73fba09eaf` |
| Revelation 20 | 21 | 6 | 0 | `10bdd6520946a94624785538b521141e16dc31be7fc21d4076188d456c1018a0` | `18ad538b296b68a310b14c968632b7eb48aec459f2d822ae8664776462295eb6` |
| Exodus 14 | 34 | 2 | 1 | `a8b53c334b69629f2bbb0ea1ecdafc21ae687a26f7c59ce2d965de9b06058380` | `1059b0c617109751eb944cc9b22b2d8e83233f720d258561449c4624f8c2b2db` |

These counts use the existing canonical chapter text with the frozen
`essential-passage-context-v2`, `reader-relevance-eligibility-v1`, cluster v2,
policy v3, and gate v2.1 contracts. Revelation 21's eight forensic misses are
therefore available as source clusters; this prototype must not reinterpret
their scorer status.

## Diagnostic boundary

The experimental user prompt will be byte-distinct from the immutable prompt
1.7 packet and identified as `prompt-1.7 + reader-level-idea-projection-v1`.
It will add a delimited CORE/RELEVANT navigation section while retaining the
complete original compiled synthesis and citation summary below it. Prompt 1.7
source files and hashes remain unchanged. Candidate generation is a separate,
one-response renderer handoff and is not part of projection construction.

The prepared immutable diagnostic namespace is
`.bhf-data/bhf-commentary-candidates/reader-level-idea-projection-v1-1d7761ad8f69c739e395/`.
Its Revelation 21 handoff is marked `AWAITING_EXTERNAL_RENDERER`; no candidate
response was generated.
