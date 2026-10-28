# NE-11E1: Presentation structured output

The structured-output suite initially had six failures: four adapter fixtures lacked the model-aware capability method, one provider response lacked required generation metadata, and one test lacked the ChatRequest import. The provider now rejects an absent or non-object `generated_from` at its boundary; downstream validation remains responsible for the metadata values and evidence integrity. Legacy test adapters inherit the production compatibility interface, and the ordinary request test imports ChatRequest.

Before: 6 failed, 15 passed in the structured-output suite. After: 141 passed across structured output, parsing, provider errors, pipeline, integrity boundary, and OpenRouter and OpenAI-compatible adapter tests. The initial combined run exposed ten further outdated fixtures; those were updated to inherit the same interface. No known phase-specific risk remains.
