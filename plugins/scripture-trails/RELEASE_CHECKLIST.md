# Scripture Trails v0.1.1 — Publication checklist

This is a skills-only package; no BHF web services, API, CKL runtime,
account connection, or separate AI model is needed.

## Release gate

- [ ] Verify `developerName` matches the actual OpenAI verified publisher identity.
- [ ] Confirm the plugin's name, description, starter prompts, and two image assets.
- [ ] Run `python tools/validate.py framework/`.
- [ ] Run `python -m pytest -q tests/test_scripture_trails_build.py`.
- [ ] Run `python tools/build_scripture_trails.py --check`.
- [ ] Run `python tools/build_scripture_trails.py --package`.
- [ ] Run `python tools/build_scripture_trails.py --validate-zip`.
- [ ] Confirm the release ZIP includes `assets/logo.png` and `assets/composer-icon.png`.
- [ ] Install plugin for local testing; complete manual acceptance-cases.yml.
- [ ] Verify multi-turn rabbit-trail continuity, source honesty, and no forced connections.
- [ ] Review any missing dependencies and the full repository CI gate.
- [ ] Verify website/support/privacy/terms fields only where requested and backed by published pages.
- [ ] Complete verified developer setup and OpenAI submission/review before publishing.

This checklist is for maintainers; it is not included in the runtime ZIP.
