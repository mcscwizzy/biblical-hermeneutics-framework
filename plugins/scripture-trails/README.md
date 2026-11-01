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

## Conversational discovery in v0.1.2

Scripture Trails answers first, then offers a connection only when it adds
something useful. It considers explicit quotations, strong allusions and
literary patterns, passages directly relevant to the question, and historical,
geographical, language, or cultural details. It ranks candidates by textual
support, relevance, novelty, and explanatory value; a shared word or broad
similarity alone is not enough.

The relationship is expressed at the strength the text supports: an explicit
quotation is distinct from a strong allusion, a thematic comparison, or a
speculative echo. For example, the Gospels quote Psalm 22:1 in the crucifixion
scene, while Hebrews 2:12 quotes Psalm 22:22; Hebrews 2:13 then draws on Isaiah
8:17–18. A Babel and Pentecost comparison can be explored as a possible theme,
but Acts 2 does not explicitly cite Genesis 11 or restore one universal
language.

Simple factual questions need no trail. When a meaningful connection is
available, the plugin normally offers one or two specific, optional directions.
It may offer three when the reader asks for alternatives or several strong
connections merit attention. A deep investigation stays focused on the
requested subject. Invitations explain why a connection matters and leave the
conclusion open; there is no required “Rabbit Trails” section or generic closing
question.

Within a conversation, the plugin follows the selected trail, keeps the active
passage and reasoning in view, avoids repeating material, and returns to the
original passage when asked. This conversational context does not persist across
unrelated sessions.

## Build and validate

From the BHF repository root, Python 3.9+ and the existing PyYAML dependency are
enough to build it:

```bash
python3 tools/build_scripture_trails.py --build
python3 tools/build_scripture_trails.py --validate
python3 tools/build_scripture_trails.py --check
python3 -m pytest -q tests/test_scripture_trails_build.py
python3 tools/build_scripture_trails.py --package
python3 tools/build_scripture_trails.py --validate-zip
```

`--package` builds and validates resources before producing:

```text
dist/plugins/scripture-trails-0.1.2.zip
dist/plugins/scripture-trails-0.1.2.zip.sha256
dist/plugins/scripture-trails-build-manifest.json
```

The ZIP also contains two square, self-contained PNG branding assets:
`assets/logo.png` for the listing and `assets/composer-icon.png` for the composer.
The manifest uses the required `./assets/` relative paths. The builder explicitly
allowlists the files and validates their dimensions, size, and PNG signatures
in both the workspace and release ZIP. The icon images are source-controlled,
not generated during each build.

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

For a multi-turn check, ask for two worthwhile connections, select “the second
one,” ask how it connects to Genesis, and then return to the original passage.
Check that the plugin follows the option it actually offered, carries forward
its earlier reasoning, and does not repeat the first answer. End by asking to
stop or by changing subjects; it should respect that direction without another
forced suggestion. The focused Psalm 22/Hebrews, Babel/Acts, simple-fact, and
contested-interpretation cases cover discovery quality and restraint.

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

## Prepare the v0.1.2 publication release

The plugin has release-ready artwork and draft listing text, but publication
requires **live conversational tests**, publisher verification, and review.
Confirm `developerName` against the actual verified developer identity before
submitting. Do not invent website/support/privacy URLs or screenshots, or
claim that the plugin includes an online CKL research database. Skills-only
packages do not require all four hosted listing URLs under current rules.


1. Review the module manifest, generated references, attribution, license, and
   all manual acceptance cases. For v0.1.2, `VERSION` and `plugin.json` must
   both contain `0.1.2`.
2. Refresh generated resources, then validate and package from the repository
   root:

   ```bash
   python3 tools/build_scripture_trails.py --build
   python3 tools/validate.py framework/
   python3 tools/build_scripture_trails.py --validate
   python3 tools/build_scripture_trails.py --check
   python3 -m pytest -q tests/test_scripture_trails_build.py
   python3 tools/build_scripture_trails.py --package
   python3 tools/build_scripture_trails.py --validate-zip
   git diff --check
   ```

3. Inspect `dist/plugins/scripture-trails-0.1.2.zip`, its `.sha256` checksum,
   and `dist/plugins/scripture-trails-build-manifest.json`. Automated checks
   cover deterministic resources and packaging; run the manual model cases
   before publication.
4. Upload the ZIP as a draft using a verified publisher identity. Complete any
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
