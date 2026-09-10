# Commentary v1.2 scale prose pilot

## Decision

`SCALE_PILOT_NOT_READY`

The deterministic 75-chapter corpus was frozen, but generation stopped after
Batch 001 under the pilot's explicit catastrophic-stop policy. Four of the
first 13 chapters (`30.77%`) cited valid full-synthesis ancestry paths that were
not present in the frozen reader-level ancestry envelope. This is a widespread
envelope-consumption failure, so Batches 002–006 were not generated.

BHF should **not** begin controlled bulk generation of the remaining v1.2 prose
yet. The bounded next step is to determine why the combined prompt 1.7 plus
relational-envelope presentation still permits use of full-synthesis paths
outside the envelope. Do not create prompt 1.8, alter scoring, or tune around
Revelation 20 from this truncated population.

## Frozen pilot identity

- Starting SHA: `07778940c159449443fd8d47ffeeca00b2732483`
- Branch: `feat/commentary-v1.2-enrichment`
- Namespace: `.bhf-data/bhf-commentary-candidates/commentary-v1.2-scale-pilot-922472547555015a3ced/`
- Planned chapters: `75`
- Batches: `13 / 13 / 13 / 12 / 12 / 12`
- Generated chapters: `13`
- Ungenerated chapters: `62`
- Seen chapters in the frozen corpus: `5`
- Unseen chapters in the frozen corpus: `70` (`93.33%`)
- Renderer: `gpt-5.6-sol`, effort `medium`
- Runtime self-attestation: disabled
- Persisted-response policy: first response bytes are immutable; no score-based
  retry or manual prose repair

The frozen contract was exactly:

- renderer prompt `1.7`
- `reader-level-idea-projection-v1`
- `reader-level-idea-ancestry-envelope-v1`
- `essential-passage-context-v2`
- `reader-relevance-eligibility-v1`
- `commentary-richness-clusters-v2`
- `commentary-richness-policy-v3-reader-relevance`
- `commentary-richness-gate-v2.1`

No CKL, synthesis, evidence-routing, projection, envelope, prompt, validator,
scorer, or threshold behavior was changed during the pilot.

## Corpus selection

The manifest uses fixed genre quotas, five requested controls, and deterministic
SHA-256 ordering with density-deficit and genealogy/list preference. The 21-case
Sol qualification corpus defines `seen`; every non-control selection is unseen.
The planned strata are Torah 8, Historical Narrative 10, Poetry/Wisdom 8,
Major Prophets 8, Minor Prophets 8, Gospels 8, Acts 4, Pauline Epistles 8,
General Epistles 7, and Apocalyptic literature 6. Production-rule DATA_GAP
chapters and their reasons are recorded in `exclusions.json`.

The five controls are Exodus 14, Romans 3, 1 Corinthians 14, Revelation 20, and
Revelation 21. Only Romans 3 occurred in Batch 001. Revelation 20 remains frozen
in the manifest as `KNOWN_SCORER_RENDERER_EDGE_CASE`; it was not reached, so
this stopped run cannot determine whether it is isolated or representative.

## Completed-population metrics

These statistics describe the 13 generated chapters only. They are not a
completed 75-chapter scale estimate.

| Metric | Result |
| --- | ---: |
| Structural validity | `13/13` (`100.00%`) |
| Validator hard-provenance safety | `13/13` (`100.00%`) |
| Ancestry safety | `9/13` (`69.23%`) |
| Gate PASS | `12/13` (`92.31%`) |
| Core coverage `1.0000` | `12/13` (`92.31%`) |
| Category coverage `1.0000` | `13/13` (`100.00%`) |
| HIGH dumps | `0/13` (`0.00%`) |
| Clean passes | `8/13` (`61.54%`) |
| Genuine renderer failures | `5/13` (`38.46%`) |
| Mean weighted coverage | `.9736` |
| Median weighted coverage | `1.0000` |
| Mean eligible utilization | `.9762` |
| Median eligible utilization | `1.0000` |
| Average prose length | `254.2` words |

Weighted coverage percentiles were P10 `.9048`, P25 `1.0000`, P50 `1.0000`,
P75 `1.0000`, and P90 `1.0000`.

## Exceptions and lowest results

The exception queue contains five chapters:

| Chapter | Classification | Weighted | Eligible | Core | Gate | Envelope mismatches |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Romans 3 | `PROVENANCE_FAILURE` | `1.0000` | `1.0000` | `1.0000` | PASS | 2 |
| Joshua 10 | `PROVENANCE_FAILURE` | `1.0000` | `1.0000` | `1.0000` | PASS | 1 |
| Leviticus 1 | `PROVENANCE_FAILURE` | `1.0000` | `1.0000` | `1.0000` | PASS | 3 |
| Genesis 5 | `PROVENANCE_FAILURE` | `1.0000` | `1.0000` | `1.0000` | PASS | 2 |
| Galatians 3 | `CORE_OMISSION` | `.7763` | `.8333` | `.5000` | QUALITY_FAIL | 0 |

Acts 9 was the second-lowest chapter by both weighted coverage (`.8810`) and
eligible utilization (`.8571`), but it retained full core/category coverage,
passed Gate, and classified `CLEAN_PASS`. All other completed chapters scored
`1.0000` weighted and eligible coverage. The complete lowest-ten lists remain
in `final-report.json`.

The four envelope failures are not fabricated-ID failures. The unchanged
structural validator accepted their synthesis/evidence pairings, explaining the
`100%` hard-provenance-safe rate. The stricter envelope audit found eight blocks
whose valid source ancestry was absent from the projected envelope. That
distinction is why hard provenance and ancestry safety are reported separately.

## Sparse versus dense

| Density | Chapters | Weighted mean | Eligible mean | Gate PASS | Ancestry safe | Avg words | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Sparse (`1–5`) | 4 | `1.0000` | `1.0000` | `100%` | `100%` | `125.5` | 0 |
| Medium (`6–20`) | 5 | `1.0000` | `1.0000` | `100%` | `40%` | `226.4` | 3 provenance |
| Dense (`21+`) | 4 | `.9143` | `.9226` | `75%` | `75%` | `417.8` | 1 provenance, 1 core |

No density bucket produced a HIGH dump. The strongest observed pattern is not
the Revelation 20 richness edge case: medium chapters showed repeated envelope
escape despite perfect scorer coverage, while the dense group contained the
single core omission. The sample is truncated and cannot support genre-wide
conclusions.

## Seen versus unseen

Only one seen chapter landed in the completed batch, so comparative
generalization is not valid.

| Split | Chapters | Gate PASS | Weighted mean | Eligible mean | Hard provenance safe | Ancestry safe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Seen | 1 | `100%` | `1.0000` | `1.0000` | `100%` | `0%` |
| Unseen | 12 | `91.67%` | `.9714` | `.9742` | `100%` | `75%` |

The planned corpus remains strongly out-of-sample (`93.33%` unseen), but the
catastrophic stop prevents a valid full seen/unseen comparison.

## Human-readability review

All 13 completed chapters were reviewed because the first batch already fits
the requested 10–15 chapter qualitative sample. All were natural, coherent,
free of HIGH dump feel, and did not expose projection or ancestry vocabulary.
No checklist behavior or widespread readability regression was observed.

Isaiah 3 was unusually brief at 59 words but proportionate to its single
projected eligible idea. Genesis 5 stayed appropriately concise for genealogy
material. Galatians 3 was natural and substantial despite the scorer-confirmed
core omission. The four ancestry failures were invisible at the prose level:
their English was useful, but their machine-readable citations crossed the
frozen envelope boundary.

## Generation warning

During operational recovery from the first batch renderer session, two later
renderer returns (Romans 3 and Hebrews 1) reached immutable paths after first
responses already existed. The later driver discarded the later returns and
preserved the first bytes. No response was chosen by score and no persisted
response was regenerated, but the redundant exchanges are recorded as a pilot
execution warning.

## Tests

The combined focused suite passed `70` tests in `148.55s` with no warnings.
After adding the final manifest/batch/checksum reproducibility assertion, the
pilot-specific suite passed `7` tests in `62.83s`, also with no warnings. It covers
prompt 1.7 immutability; projection and ancestry-envelope determinism; exact
ancestry behavior; frozen scoring contracts; deterministic corpus/batch shape;
immutable response collision handling; failure quarantine; and aggregate,
percentile, density, and seen/unseen metric correctness.

## Readiness conclusion

`SCALE_PILOT_NOT_READY`

This is a system-level stop, not a Revelation 20 exception-queue decision.
Controlled bulk generation cannot safely begin while the envelope boundary is
violated in `30.77%` of the first batch. Investigate only that repeatable
presentation/consumption boundary, preserve all recorded responses, and rerun a
fresh frozen scale pilot after the bounded cause is addressed.
