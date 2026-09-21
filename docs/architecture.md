# BHF architecture

BHF has two related concerns in one repository:

1. A composable Markdown hermeneutics framework and maintainer-side generation
   tooling.
2. A Python/FastAPI study application whose normal web runtime is
   model-independent.

## Runtime boundary

```text
Browser / BHF application
    deterministic Scripture, Commentary, CKL, lexicon, archaeology, maps,
    cross-references, notes, and offline study data
        ↓
    Ask BHF handoff modal
        ↓ clipboard + new tab
External BHF assistant
    conversational synthesis and follow-up
```

The current external destination is the BHF assistant hosted in ChatGPT. It is
configured through the generic `BHF_ASSISTANT_URL` setting and injected as
`assistantUrl`. A future plugin or supported assistant destination can replace
the URL without changing the reader or evidence layer.

The browser never embeds, scrapes, or automates the external assistant. Opening
the modal, preparing text, browsing Scripture, and using deterministic study
tools make no LLM/provider request. Users do not configure providers, API keys,
models, endpoints, context windows, or output limits inside BHF.

## Evidence domains

Scripture, CKL, lexicon, archaeology, Commentary v1.2, maps, and timeline are
peer evidence domains. The application retrieves and renders deterministic
evidence, preserves provenance and uncertainty, and keeps device-local notes,
highlights, and saved studies available offline where supported.

The companion context endpoint returns deterministic evidence bundles and
precomputed presentation packets. It does not perform runtime inference.

## Maintainer boundary

The repository still contains model adapters, provider modules, prompts,
commentary-generation commands, renderer qualification, evidence compilation,
and conformance tests needed for future offline release engineering and
historical reproducibility. Those modules are not imported by the web runtime
routes or browser assets.

The web application retains only deterministic routes such as:

```text
GET  /api/bible/{book}/{chapter}
GET  /api/study/companion-context
POST /api/study/actions
GET  /api/bhf-commentary/{book}/{chapter}
```

There is no runtime `/ask`, provider health, fallback-inference, or presentation
generation API surface.

## Offline behavior

The service worker and IndexedDB cache Bible/study assets and device-local
records. Reader, Commentary, CKL/evidence, lexicon data, maps, notes,
highlights, and saved studies remain independent of the assistant destination.
Only the external conversation handoff naturally requires network access.

See [Ask BHF assistant handoff](assistant-handoff.md) and
[Frontend and backend routing](deployment-routing.md) for deployment details.
