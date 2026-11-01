# Scripture Trails

Scripture Trails is a portable, skills-only ChatGPT plugin for conversational
Bible exploration. It answers the question first, uses the passage's own
literary and historical context, and offers optional Scripture connections
when there is a good reason to follow them.

The installed package contains a portable `plugin.json`, one skill, its
supporting references, attribution, license text, and a source provenance
manifest. BHF modules are read only by the repository build tool. The plugin has
no BHF runtime dependency, Bible text database, account, backend, API key,
external API, or MCP server.

## Build and validate

From the BHF repository root, Python 3.9+ and the existing PyYAML dependency are
enough to build it:

```bash
python3 tools/build_scripture_trails.py --validate
python3 tools/build_scripture_trails.py --check
python3 tools/build_scripture_trails.py --build
python3 tools/build_scripture_trails.py --check
python3 tools/build_scripture_trails.py --package
python3 tools/build_scripture_trails.py --validate-zip
```

`--package` builds and validates resources before producing:

```text
dist/plugins/scripture-trails-0.1.0.zip
dist/plugins/scripture-trails-0.1.0.zip.sha256
dist/plugins/scripture-trails-build-manifest.json
```

The ZIP has `plugin.json` at its archive root. Generated reference files and
`source-module-manifest.json` are committed so `--check` can detect drift. If a
selected framework module changes, the check names both the stale output and
the source module. Rebuild with `--build`, review the generated changes, and
commit them with the source update.

## Add source modules

Edit `config/module-selection.yml`. Add a stable BHF module ID under the themed
reference where its guidance belongs. The builder checks that IDs resolve,
required dependencies are also explicitly assigned, all seven foundational
modules remain included, selected source modules pass BHF validation, and
internal BHF module references resolve. Keep each source ID assigned to one
generated reference; the source manifest maps every selected module to its
package output. Rebuild and review the generated Markdown and provenance.

The current selection includes all eight genre modules, Hebrew and Greek
guidance, nine historical/cultural context modules, and book profiles for
Genesis, Deuteronomy, 1–2 Kings, Psalms, Job, Isaiah, Micah, Jonah, Matthew,
and John. Passage-specific guidance is kept in its own reference so it need not
be presented on every question.

## Update conversation behavior

Edit `skills/explore-scripture/SKILL.md` for activation, answer-first behavior,
reference-loading rules, or the main interaction. Edit
`references/trail-selection.md` for how connections are evaluated and offered;
edit `references/interaction-patterns.md` for conversational pacing. Update
`tests/acceptance-cases.yml` with positive and negative prompts. That YAML is a
developer evaluation fixture and is deliberately excluded from the ZIP.

## Test the experience

Run deterministic checks with:

```bash
python3 tools/validate.py framework/
python3 -m pytest -q tests/test_scripture_trails_build.py
python3 tools/build_scripture_trails.py --check
python3 tools/build_scripture_trails.py --package
```

Then manually test the cases in `tests/acceptance-cases.yml` in ChatGPT with
the plugin enabled. Evaluate whether it answers the exact question, preserves
context, distinguishes text from inference, qualifies uncertain connections,
and avoids each listed failure. Automated tests validate package structure and
instruction resources only; they do not run a language model or establish that
its answers pass these behavioral cases.

## Local ChatGPT testing

The current ChatGPT desktop plugin workflow installs a plugin from a local
marketplace folder. Extract the ZIP to a folder, add that folder to a repo or
personal marketplace catalog, and restart ChatGPT desktop to enable it. The
ZIP itself is also the package format used to upload a public-submission draft
in the OpenAI Plugins dashboard; a successful local build is not a submitted or
published plugin.

See the current [plugin packaging guide](https://developers.openai.com/plugins/build/plugins),
[skills guide](https://developers.openai.com/plugins/build/skills), and
[submission guide](https://developers.openai.com/plugins/deploy/submission).

## Prepare a publication release

1. Review the module manifest, generated references, attribution, license, and
   all manual acceptance cases.
2. Increment `VERSION` and the matching `plugin.json` version together.
3. Run source validation, the full Python test suite, `--check`, and `--package`.
4. Inspect the ZIP and SHA-256 checksum; keep the build manifest with the
   release record.
5. Upload the ZIP as a draft using a verified publisher identity. Complete any
   listing fields or primary icon assets required by the current portal, pass
   the automated skill checks, and submit the draft for review. Publish only
   after approval and a separate release decision.

## Skills-only limitations

The skill carries methodology and curated references, not a searchable Bible
corpus or live research service. It cannot independently verify a newly
published archaeological claim, manuscript report, or scholarly reference; it
must not imply that it searched a source unless a conversation tool actually
did so. It relies on the model's available knowledge and the current
conversation, and it cannot persist a selected trail outside that conversation.
Updates to framework guidance require rebuilding and redistributing the plugin.
