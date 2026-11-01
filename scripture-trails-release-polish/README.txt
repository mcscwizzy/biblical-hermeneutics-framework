SCRIPTURE TRAILS v0.1.1 PUBLICATION POLISH KIT

The connected GitHub integration denied writes (HTTP 403), so these files
are a local patch kit for the existing branch:
  feat/scripture-trails-plugin-pipeline

INSTRUCTIONS
  1. Extract this kit somewhere on the computer where your BHF repo is cloned.
  2. Check out feat/scripture-trails-plugin-pipeline in that repo.
  3. Run: python /path/to/kit/apply_release_polish.py /path/to/bhf-repo
  4. Run the tests and check the git diff before committing.
  5. Push the branch and open a PR; do not merge/publish before live plugin tests.

WHAT IT CHANGES
  - Adds a 1024x1024 square PNG logo and 256x256 composer icon
  - Adds both paths to plugin.json
  - Polishes description and three default conversation starters
  - Adds image files to the deterministic builder's package allowlist
  - Adds PNG size/dimensions/header validation in source and ZIP
  - Adds tests for missing/malformed images, manifest paths and ZIP integrity
  - Adds a publication checklist
  - Bumps the plugin version from 0.1.0 to 0.1.1
  - Regenerates source manifest and release ZIP using the existing builder

NOT DONE
  - No changes have been pushed to GitHub.
  - No plugin installation or live language-model evaluation has been run.
  - Developer identity verification and public submission require user action.
