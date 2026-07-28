You are working in the Biblical Hermeneutics Framework repository.

Implement a knowledge-gap and research-expansion stage in the BHF agent pipeline.

The purpose of this change is to prevent the Canonical Knowledge Library from becoming a ceiling on the model’s reasoning. The CKL should remain trusted foundational context, but it must be treated as incomplete and non-exhaustive.

Do not attempt to make the CKL contain every possible piece of biblical scholarship.

Do not remove or weaken the existing hermeneutical framework, CKL retrieval, lexicon retrieval, Bible context, genre detection, reference detection, caching, observability, or offline/BYO-model behavior.

First inspect the current implementation before making changes, especially:

- `bhf_agent/runner.py`
- `bhf_agent/config.py`
- `bhf_agent/prompts.py`
- `bhf_agent/models.py`
- `bhf_agent/runner_state.py`
- `bhf_agent/question_types.py`
- `framework/canonical_library/`
- existing CKL retrieval and scoring helpers
- existing tests in:
  - `tests/test_runner.py`
  - `tests/test_prompt_building.py`
  - `tests/test_pipeline_context.py`
  - `tests/test_agent_config.py`
  - `tests/test_question_types.py`

The current code already has concepts such as:

- `minimum_relevance_score`
- `canonical_library_strong_match`
- `ckl_retrieval_usable`
- `ckl_coverage_gap`
- `fallback_to_model`
- `fallback_reason`
- `canonical_library_prompt_mode`
- `STRICT_CKL_NO_MATCH_PROMPT`
- CKL retrieval metadata and caching

Reuse and extend the existing architecture instead of creating a separate parallel pipeline.

# Main architectural requirement

Separate these two concepts:

1. Retrieval relevance

This measures whether the retrieved CKL entries are related to the user’s question.

Examples:

- Does the question match Ruth?
- Does it match redemption?
- Does it match inheritance?
- Does it match Boaz?

2. Answer coverage

This measures whether the retrieved context actually contains enough information to answer the specific question responsibly.

A CKL result may be highly relevant to the topic while still failing to cover the legal, historical, lexical, archaeological, scholarly, or interpretive details needed for the answer.

Do not use `minimum_relevance_score` as though it were the answer-coverage score.

Preserve `minimum_relevance_score` for CKL retrieval relevance.

Add a separate configurable answer-coverage system.

# Configuration

Add a new configuration section or clearly named fields for knowledge-gap behavior.

A dedicated configuration object is preferred, such as:

```python
@dataclass(frozen=True)
class KnowledgeExpansionConfig:
    enabled: bool = True
    sufficient_coverage_threshold: float = 0.85
    major_gap_threshold: float = 0.60
    research_override_enabled: bool = True
    allow_model_knowledge_expansion: bool = True
    allow_external_retrieval: bool = False
    max_gap_items: int = 6
```

Naming may be adjusted to fit the repository conventions, but the meanings must remain clear.

Validate that:

- thresholds are between `0.0` and `1.0`
- `major_gap_threshold` is lower than `sufficient_coverage_threshold`
- `max_gap_items` is greater than zero

Default behavior:

- 85% or greater: CKL-primary synthesis
- 60% through 84%: targeted gap expansion
- below 60%: broad knowledge expansion
- explicit research-oriented questions override the score and request expansion
- external network retrieval remains disabled by default
- model knowledge expansion remains available by default when permitted by configuration

Do not silently enable web access or network calls.

BHF must continue to function:

- offline
- with Ollama
- with OpenAI-compatible local servers
- with small local models
- with remote models
- without any configured external research provider

# Coverage levels

Implement three clear expansion modes.

## 1. CKL primary

Conditions:

```text
answer_coverage >= 0.85
and no research-oriented override applies
```

Behavior:

- use Scripture, CKL, lexicon, genre, reference, map, and other supplied context as the primary evidence
- allow the model to synthesize and reason
- do not claim that the CKL is exhaustive
- do not trigger additional retrieval solely because the score is below perfection
- broader pretrained knowledge may be used cautiously for explanation when allowed, but the answer should remain grounded in supplied evidence

Suggested internal mode name:

```text
ckl_primary
```

## 2. Targeted gap expansion

Conditions:

```text
0.60 <= answer_coverage < 0.85
```

Behavior:

- retain all useful CKL material
- identify exactly which dimensions are missing
- expand only those missing dimensions
- allow broader model knowledge when configured
- use an external research provider only if one is explicitly configured and enabled
- do not discard CKL context
- do not repeat the full original retrieval unnecessarily

Suggested internal mode name:

```text
targeted_gap_expansion
```

Examples of missing dimensions:

- ancient legal background
- Second Temple context
- lexical ambiguity
- manuscript evidence
- archaeology
- geography
- chronology
- historical setting
- major scholarly interpretations
- translation differences
- relationship to another passage
- reception history
- cultural practice
- missing direct evidence from the passage

## 3. Broad knowledge expansion

Conditions:

```text
answer_coverage < 0.60
```

Behavior:

- treat CKL results as partial background
- allow the model to reason from broader pretrained knowledge when configured
- use external retrieval only when explicitly enabled and available
- clearly communicate uncertainty
- never invent CKL support
- never present external/model-derived material as though it came from the CKL
- preserve BHF’s hermeneutical method throughout the response

Suggested internal mode name:

```text
broad_knowledge_expansion
```

# Research-oriented overrides

Some question types must request expanded research even when CKL coverage appears high.

Detect explicit research intent from the question and, where appropriate, existing question classification.

Examples include:

- “What are the major scholarly interpretations?”
- “Why do scholars disagree?”
- “How did Second Temple Jews understand this?”
- “What does archaeology tell us?”
- “What is the manuscript evidence?”
- “How does this compare with ancient Near Eastern law?”
- “How did the early church interpret this?”
- “Is this translation accurate?”
- “What are the competing interpretations?”
- “What do historians believe?”
- “How does the Hebrew or Greek affect this interpretation?”
- “What do commentaries say?”
- “What evidence supports this view?”

Do not rely only on exact keyword matching.

Create a small, testable helper or classification mechanism that identifies likely research-oriented questions.

Avoid triggering research mode for every normal explanatory question.

A simple question such as “Who was Timothy?” should not automatically trigger broad research just because the CKL entry is short.

# Coverage evaluation

Create an explicit answer-coverage evaluation stage after CKL, Scripture, lexicon, and other local context have been gathered, but before the final answer prompt is built.

Suggested flow:

```text
User question
    ↓
Reference and question classification
    ↓
Bible/context retrieval
    ↓
CKL retrieval relevance
    ↓
Lexicon and other local context
    ↓
Answer-coverage evaluation
    ↓
Choose expansion mode
    ↓
Optional targeted or broad expansion
    ↓
Final synthesis prompt
```

The coverage evaluator should produce structured data similar to:

```python
@dataclass(frozen=True)
class AnswerCoverageAssessment:
    score: float
    mode: str
    sufficient: bool
    research_override: bool
    covered_dimensions: tuple[str, ...]
    missing_dimensions: tuple[str, ...]
    rationale: str
    evaluator: str
```

Exact naming may differ, but it must be structured and testable.

Do not store only a raw percentage.

The assessment should explain:

- what the local context covers
- what is missing
- why the selected mode was chosen
- whether an explicit research override applied
- how the score was determined

Limit missing dimensions according to configuration.

# Deterministic-first behavior

Do not require an extra model call for every question.

Use a deterministic first-pass evaluator based on available pipeline signals, including where relevant:

- CKL result count
- CKL relevance scores
- strong-match status
- direct Scripture availability
- question type
- reference confidence
- genre confidence
- lexicon availability
- whether retrieved CKL sections directly address the user’s requested subject
- placeholder or incomplete CKL status
- CKL rejection reasons
- `ckl_coverage_gap`
- whether the question requests comparison, scholarly debate, archaeology, textual criticism, translation analysis, or historical research
- whether the question has multiple distinct requested dimensions

Keep the implementation explainable.

Do not create a fake precision formula that claims more certainty than the available signals support.

The initial score is a routing estimate, not a claim that the system mathematically knows 85% of all scholarship.

Document this clearly in code comments and developer documentation.

An optional model-assisted coverage evaluator may be supported later, but do not make the base implementation dependent on a second LLM call.

# Important distinction

A high CKL relevance score must not automatically produce high answer coverage.

For example:

```text
Question:
How does Paul’s phrase “works of the law” relate to Second Temple Jewish identity markers?

CKL retrieval:
Romans
Galatians
Paul
law
justification

Retrieval relevance:
High

Answer coverage:
Potentially incomplete unless the retrieved material directly addresses:
- Second Temple Judaism
- circumcision
- food laws
- boundary or identity markers
- relevant scholarly disagreement
```

The implementation must support this distinction.

# Broader model knowledge

Update the prompt philosophy so a strong CKL result does not forbid all reasoning beyond the supplied context.

Add an instruction equivalent to:

“Treat the supplied Canonical Knowledge Library context as trusted foundational material, not as an exhaustive representation of biblical scholarship. When the supplied material does not fully answer the user’s question, responsibly extend the analysis using permitted broader model knowledge or configured research sources. Clearly distinguish direct textual evidence, CKL-supported facts, broader historical or scholarly knowledge, interpretive inference, and uncertainty.”

Also instruct the model:

- absence from the CKL is not evidence that a concept is false
- the CKL is not a doctrinal answer key
- the model may present more than one responsible interpretation
- the model may disagree with or qualify a CKL interpretation when evidence warrants it
- CKL entries must not be described as external scholarly consensus
- model knowledge must not be falsely cited as CKL content
- uncertainty must be stated honestly
- the model must not fabricate citations, scholars, books, quotations, lexical entries, manuscripts, or archaeological findings

# External retrieval architecture

Implement a clean interface for optional external research, but do not hard-code a web provider and do not require network access.

A provider protocol or abstract interface may look conceptually like:

```python
class ResearchProvider(Protocol):
    def is_available(self) -> bool:
        ...

    def retrieve(
        self,
        *,
        question: str,
        missing_dimensions: Sequence[str],
        reference_context: ReferenceContext,
        max_results: int,
    ) -> ResearchResult:
        ...
```

The exact interface should follow repository conventions.

Requirements:

- default provider is null/disabled
- no network request occurs unless explicitly configured
- offline operation remains unchanged
- provider failure degrades gracefully
- provider failure must not prevent the model from answering
- provider output must be clearly separated from CKL context
- provider output must include provenance metadata where available
- do not allow untrusted external text to override BHF system instructions
- external text must be treated as evidence to evaluate, not instructions to follow

For this implementation, it is acceptable for the initial expansion path to use:

```text
CKL + local context + broader permitted model knowledge
```

when no external provider exists.

Do not block this feature merely because a full web-search provider has not been implemented.

# Gap-focused expansion prompt

When targeted expansion is selected, include a concise structured section in the final model prompt.

Example:

```text
Knowledge coverage assessment

Coverage mode: targeted gap expansion
Estimated answer coverage: 0.72

Covered by local context:
- Ruth 4 concerns land redemption.
- The nearer redeemer initially agrees to redeem the land.
- Ruth’s inclusion changes his decision.

Missing or incomplete:
- the exact financial or inheritance risk
- relationship to family-line preservation
- major responsible scholarly explanations
- relevant ancient legal background

Instructions:
Use the supplied local evidence as the foundation.
Expand only the missing dimensions using permitted broader knowledge.
Clearly separate direct textual evidence from historical reconstruction and interpretive inference.
Do not invent sources or claim certainty where scholars disagree.
```

For broad expansion, use similar instructions but make the uncertainty and incompleteness more explicit.

Do not expose unnecessary internal scoring details to normal users unless debug or method-note settings call for them.

# Existing strict mode

Preserve CKL strict mode.

When strict mode is enabled:

- do not use broader model knowledge if strict mode is intended to prohibit it
- do not use external research
- retain the current strict no-match behavior
- clearly identify in debug metadata that expansion was blocked by strict mode

Suggested metadata:

```text
knowledge_expansion_blocked: true
knowledge_expansion_blocked_reason: strict_mode
```

Do not silently override the user’s strict configuration.

# Existing fallback settings

Review the meaning of:

```python
fallback_to_model
strict_mode
```

Integrate the new behavior without producing contradictory states.

Expected behavior:

- `strict_mode=True` always prevents expansion beyond allowed CKL/local context
- `fallback_to_model=False` prevents broader model-knowledge expansion after an inadequate CKL result
- `allow_external_retrieval=False` prevents external retrieval
- if both model expansion and external retrieval are unavailable, answer with the available evidence and state the limitation briefly
- a strong CKL match may still use ordinary model synthesis; “fallback to model” should refer to unsupported knowledge expansion, not the basic act of generating an answer

Document these semantics because the existing field names may otherwise be ambiguous.

# Debug and observability metadata

Add clear metadata without removing existing keys.

Include at least:

```text
answer_coverage_score
answer_coverage_mode
answer_coverage_sufficient
answer_coverage_evaluator
answer_coverage_rationale
answer_coverage_covered_dimensions
answer_coverage_missing_dimensions
research_override_detected
knowledge_expansion_requested
knowledge_expansion_performed
knowledge_expansion_source
knowledge_expansion_blocked
knowledge_expansion_blocked_reason
external_research_enabled
external_research_available
external_research_attempted
external_research_succeeded
external_research_result_count
external_research_error
```

Possible values for `knowledge_expansion_source`:

```text
none
model_knowledge
external_provider
model_and_external
strict_local_only
```

Preserve current metadata such as:

- `canonical_library_strong_match`
- `ckl_retrieval_usable`
- `ckl_coverage_gap`
- `fallback_to_model`
- `fallback_reason`
- `canonical_library_prompt_mode`

Make sure their meanings remain coherent.

# Caching

Review existing CKL retrieval, context, and response cache keys.

The selected coverage mode and expansion behavior can change the final prompt and response.

Update cache keys where necessary to include factors such as:

- answer-coverage mode
- answer-coverage thresholds
- research override
- whether model expansion is allowed
- whether external retrieval is enabled
- external provider identity/version when applicable
- missing-dimension fingerprint

Do not return a cached CKL-primary answer for a request that now requires targeted or broad expansion.

Avoid caching transient external-research failures as successful research results.

# User-facing behavior

Do not make normal answers sound like database diagnostics.

The final answer should remain natural.

The response may briefly say things such as:

- “The text does not state the exact reason, so several explanations are possible.”
- “The local study material provides the legal setting, but the precise financial risk is debated.”
- “Scholars commonly propose several possibilities.”

Do not produce statements like:

- “The CKL score was 72%.”
- “The database lacks this information.”

unless debug output or explicit method notes request this level of detail.

The score is primarily for routing and diagnostics.

# Small-model support

This project supports small local models.

Keep added prompt text concise and structured.

Do not inject a huge research-policy block into every prompt.

Only add gap-specific instructions when expansion is selected.

Prefer deterministic routing over additional model calls.

Do not assume that all models support tool calling, JSON schema output, browsing, or long context windows.

The implementation must continue working with plain text completion through the existing Ollama and OpenAI-compatible adapters.

# Tests

Add or update tests covering at least the following.

## Configuration

1. Default thresholds are:

```text
sufficient = 0.85
major gap = 0.60
```

2. Invalid threshold ranges fail validation.

3. Major-gap threshold cannot be equal to or greater than the sufficient threshold.

4. Configuration loads correctly from JSON mappings.

5. Existing configurations without the new fields continue working with defaults.

## Coverage evaluation

6. A simple direct factual question with strong direct CKL support selects `ckl_primary`.

7. A highly relevant CKL result that lacks a specifically requested historical dimension selects `targeted_gap_expansion`.

8. A result with little useful context selects `broad_knowledge_expansion`.

9. High retrieval relevance does not guarantee high answer coverage.

10. Missing dimensions are bounded by `max_gap_items`.

11. The evaluator produces deterministic output for identical inputs.

## Research overrides

12. “What are the major scholarly interpretations of this passage?” triggers expansion even with strong CKL coverage.

13. “What does archaeology tell us about this city?” triggers expansion.

14. “Who was Timothy?” does not trigger a research override solely because it asks about a biblical person.

15. Normal questions containing the word “scholar” in an unrelated sense do not automatically trigger expansion.

## Strict and fallback behavior

16. Strict mode blocks broader model expansion.

17. Strict mode blocks external retrieval.

18. `fallback_to_model=False` prevents model-knowledge expansion.

19. Disabled external retrieval makes no network/provider call.

20. Provider failure degrades gracefully and still produces an answer path.

21. When expansion is unavailable, the prompt tells the model to state the limitation without inventing information.

## Prompt construction

22. CKL-primary prompt identifies CKL as foundational but not exhaustive without adding unnecessary research instructions.

23. Targeted-gap prompt includes covered and missing dimensions.

24. Broad-expansion prompt clearly distinguishes local evidence, broader knowledge, inference, and uncertainty.

25. Prompt text explicitly says absence from CKL is not evidence against a concept.

26. Prompt text prohibits fabricated citations and sources.

27. Strict-mode prompt does not include permission to expand beyond local context.

## Metadata

28. Debug metadata records coverage score and selected mode.

29. Metadata records whether expansion was requested and performed.

30. Metadata identifies whether expansion came from model knowledge, an external provider, both, or neither.

31. Metadata records when expansion was blocked and why.

32. Existing CKL metadata remains present and meaningful.

## Cache behavior

33. Different coverage modes generate distinct relevant cache keys.

34. A research override does not reuse an incompatible non-research response cache entry.

35. External provider identity affects the cache where external results influence the prompt.

# Acceptance examples

## Example A: CKL primary

Question:

```text
Who was Boaz?
```

Expected:

- strong direct CKL and Scripture support
- high answer coverage
- mode: `ckl_primary`
- no unnecessary external retrieval
- concise grounded answer

## Example B: Targeted expansion

Question:

```text
Why did the nearer redeemer in Ruth 4 say that redeeming Ruth would endanger his inheritance?
```

Possible CKL coverage:

- land redemption
- Ruth
- Boaz
- nearer redeemer
- family inheritance

Expected:

- retrieval relevance may be high
- answer coverage should be below the sufficient threshold if the exact legal/financial risk is not directly covered
- mode: `targeted_gap_expansion`
- missing dimensions should include:
  - exact inheritance risk
  - relationship to preservation of the deceased man’s family line
  - responsible scholarly explanations
- model may explain multiple possibilities
- answer must acknowledge that the text does not explicitly state the exact mechanism
- no fabricated certainty

## Example C: Research override

Question:

```text
What are the major scholarly views of Paul’s phrase “works of the law”?
```

Expected:

- research override detected
- mode is at least `targeted_gap_expansion`, even if CKL relevance is high
- distinguish passage evidence from scholarly reconstruction
- do not imply that the CKL contains the complete debate
- do not invent scholar names or citations

## Example D: Broad gap

Question:

```text
How does this passage compare with a specific ancient Near Eastern treaty pattern that is not covered in the CKL?
```

Expected:

- low local answer coverage
- mode: `broad_knowledge_expansion`
- use broader model knowledge only if permitted
- external provider only if explicitly enabled
- clearly state uncertainty and limitations
- preserve BHF hermeneutical methodology

# Documentation

Update appropriate developer-facing documentation, likely including:

- `docs/architecture.md`
- `docs/canonical_knowledge_library.md`
- `.env.example` or example configuration files if relevant

Explain:

- CKL relevance versus answer coverage
- the three expansion modes
- the 0.85 and 0.60 default thresholds
- research overrides
- offline behavior
- strict-mode behavior
- optional external provider architecture
- that the score is a routing heuristic, not a mathematically exact measure of all available scholarship
- that the CKL is trusted and curated but intentionally non-exhaustive

# Implementation constraints

- Do not rewrite the entire runner.
- Do not remove existing tests.
- Do not make external web access mandatory.
- Do not add a paid API dependency.
- Do not bind the feature to OpenAI, Anthropic, Google, or any single provider.
- Do not require tool calling.
- Do not require a second LLM call for every request.
- Do not make the CKL less useful.
- Do not treat the model’s pretrained knowledge as automatically authoritative.
- Do not fabricate source attribution.
- Do not expose raw internal scores in ordinary answers.
- Do not make breaking configuration changes where backward-compatible defaults are possible.
- Keep functions focused and testable.
- Prefer new helper modules over making `runner.py` substantially more monolithic.

A reasonable new module might be:

```text
bhf_agent/coverage.py
```

and optional research-provider abstractions might live in:

```text
bhf_agent/research/
```

Use repository conventions and choose better locations if the current structure suggests them.

# Final validation

After implementation:

1. Run the focused tests for config, runner, prompts, pipeline context, and question types.
2. Run the full test suite.
3. Fix regressions caused by this work.
4. Report:
   - files changed
   - architecture implemented
   - configuration fields added
   - test results
   - any intentionally deferred external-provider work
   - any limitations that remain

Do not merely describe the changes. Implement them fully.

The final design principle is:

The CKL is the trusted floor of BHF’s knowledge process, not the ceiling of what the model is permitted to investigate and responsibly reason about.
