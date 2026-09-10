# Commentary v1.2 Prompt 1.8 renderability remediation

## Scope and starting state

This bounded remediation was performed on
`feat/commentary-v1.2-enrichment`, starting at
`5a3cb3329a3671f81db187f85478b770f068f233`. The remote branch was fetched
first and had the same SHA. The v1.1 pipeline state was already
`CORPUS_COMPLETE`; no pipeline stage or bulk generation was run.

Prompt 1.7 remains frozen. Its system-prompt SHA-256 is
`cbe6a47cb9ec7b7186347aa3e25ff05d2b9387f72e6297ce0bce44515283f614`.
Prompt 1.8 is a separately dispatched candidate with system-prompt SHA-256
`1a263b613067895b37592994f490a2d422fdda65d42aaa2e0dafe3a4eda783ff` and
user-template SHA-256
`02bcb4c2256d2212770bacbb2e02db628852dfb635e43b7bfc43e654ad49a976`.
The production default remains Prompt 1.5.

## Investigation findings

The committed Numbers 2 Prompt 1.7 input says `EVIDENCE AVAILABILITY: THIN`,
and its deterministic reader-level index says:

```text
CORE:
- None

RELEVANT:
- None
```

The authoritative compiled synthesis nevertheless contains two current-chapter
units: `syn_interpretive_questions_ede50de2e4f9` and
`syn_why_it_matters_10105ef9796e`. Both are medium-confidence and disputed,
and both descend from the Qadesh royal-tent comparison evidence.

The empty projection is intentional, not a deterministic projection bug. The
reader-level projection is a prioritization/navigation index over eligible
richness clusters; it is not an exhaustive renderability whitelist. Numbers
2's disputed cluster is classified as `CONTEXTUAL_OPTIONAL` because its
evidence has `semantic_relationship: COMPARATIVE_CONTEXT`. The disputed
eligibility rule only promotes the bounded reader-relevant relationship set
(`book_context`, `direct_context`, `intertextual_reuse`, or `later_reception`).
The cluster is therefore excluded from the `REQUIRED`/`RELEVANT` projection
without changing evidence confidence, dispute status, synthesis ancestry, or
the supplied material.

The existing validator also answers the canonical-text question. An ordinary
non-`DATA_GAP` block must contain at least one evidence ID and, when compiled
synthesis is supplied, at least one synthesis ID. Its evidence IDs must remain
within the cited synthesis ancestry. Empty evidence/synthesis arrays are legal
only for the application-owned true-`DATA_GAP` fallback, which is a separate
validated shape. Prompt 1.8 therefore does not authorize a canonical-text-only
block for this THIN Numbers 2 packet and does not change validator behavior.

## Prompt 1.8 contract change

Prompt 1.7 allowed Sol to interpret an empty projected-idea index as permission
to emit an empty commentary even though legally renderable current-chapter
synthesis remained available. Prompt 1.8 separates the two concepts:

- `CORE: None` and `RELEVANT: None` mean that no priority ideas were projected;
  they do not mean that compiled synthesis is empty or unusable.
- The renderer must inspect authoritative compiled synthesis and canonical text
  under the existing grounding rules.
- For THIN or AVAILABLE chapters, THIN means concise, not empty.
- `sections: []` is valid only when no legally renderable reader-facing content
  exists. If a usable synthesis unit can support a valid block, the renderer
  should emit the smallest useful supported commentary. This is a renderability
  condition, not a section, block, word, or synthesis-unit quota.
- Dispute, confidence, evidence ancestry, provenance, conformance, and no-dump
  rules are unchanged. Disputed material remains disputed, and the prompt does
  not promote it into CORE or RELEVANT.

## Bounded result

The new immutable namespace is:

`.bhf-data/bhf-commentary-candidates/commentary-v1.2-prompt-1.8-bounded-validation-v1-c1b33885962b7361c1ed/`

It contains the exact Prompt 1.8 system/user inputs, source packet identities,
raw response, parse/conformance/validation artifacts, attempt history, final
report, and checksums. It reused the Numbers 2 source packet, evidence,
synthesis, projection, ancestry envelope, provenance binding, model
`gpt-5.6-sol`, and medium effort. No manual response editing or deterministic
prose fabrication occurred.

Numbers 2 received exactly one fresh live Prompt 1.8 generation. Sol returned
the same empty JSON envelope:

```json
{"reference":"Numbers 2","book":"Numbers","chapter":2,"status":"pending","sections":[],"generated_metadata":null}
```

The raw response SHA-256 was
`a53939a0aea45828e4c60ecd3234e9193b94dbbc1c8df2ad3a657ed13fc56ad0`.
Conformance rejected it with `EMPTY_REQUIRED_SECTIONS`. Structural,
provenance, ancestry, Gate, and readability success were therefore not
achieved; no accepted block existed to audit. This is a Prompt 1.8 failure for
the bounded remediation, not a transport, output-file, validator, or
normalization failure.

Because Numbers 2 did not succeed, the requested five-case regression was not
authorized and was not run. The 75-chapter pilot was not started. The bounded
remediation stops here without broadening the prompt or changing production
behavior.

