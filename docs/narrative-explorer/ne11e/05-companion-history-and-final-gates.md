# NE-11E5: Companion history and release gates

## Previously failing gates

| Gate | Baseline | Current |
| --- | --- | --- |
| Structured output | Six failures | 141 presentation and adapter tests passed |
| CKL governance | One manifest failure, missing generation provenance | **FAIL**, unresolved; see [governance](02-ckl-governance.md) |
| Release path sanitizer | 24 files flagged | Two sanitizer tests passed; see [sanitization](03-release-path-sanitization.md) |
| First Corinthians retrieval | Three subtest failures | **FAIL**, unresolved; see [retrieval](04-first-corinthians-retrieval.md) |
| Companion Back | First Back returned peek | Browser regression including Back, Forward and selection preservation passed after the Maps history change |

Maps exposed the resource before asynchronous opening completed, but pushed its history entry only afterwards. Back during that interval skipped the overview. The change records the Maps entry synchronously after making the resource visible. A separate GUI fixture cleanup race was exposed when an in-flight CKL request outlived the ten-second server join; the fixture now waits for server shutdown before deleting its temporary database and errors if it cannot stop.

Additional checks: real CKL journey and keyboard browser batch 11 passed; additional browser acceptance and negative-route batch 8 passed; `npm test` 14 passed; Narrative Explorer API/projection 88 passed; NE-9C and passage tests 483 passed; CKL schema, source locks and Scripture-reference integrity 100 passed; inventory validation found 687 valid objects, 0 errors and 14 warnings; packaging, startup, CKL index, Tyndale provisioning and retired Commentary 32 passed; mobile responsive actions 2 passed; another native resource browser test passed. `tools/validate.py framework/` validated 94 modules. The tracked CKL tree and source locks match the original baseline. These results do not establish all requested integrated gates.

## Release decision

- NE-11 feature readiness: **BLOCKED**, the complete requested release verification remains pending.
- Repository-wide CI health: **FAIL**, manifest, First Corinthians and four broader retrieval control tests remain failing.
- CKL governance: **BLOCKED**, missing authoritative generation identity.
- Vercel build readiness: **BLOCKED**, no exact final-commit Preview verified.
- Manual accessibility readiness: **BLOCKED**, spoken screen-reader test not performed.
- Production deployment readiness: **BLOCKED**, unresolved gates and no final Preview.

The Vercel production domain points to deployment `dpl_4X8FwBmG9EznqymqZRP52bQzhghJ`, commit `e2f696db98be2e1662916a14781a6203073a4605`. The latest listed Preview is the NE-11D5 branch at `50158e940a5edd2b580dd4d7dc7fa3e471dd2bbd`, not the final NE-11E tree. Master auto-deployment is disabled in the checked-in Vercel configuration. After the branch is completed and pushed, an operator must verify a Preview built for the final exact commit and perform the remaining acceptance before considering production; no deployment or promotion was requested here.

## Manual spoken screen-reader protocol

With a supported screen reader and keyboard, navigate headings in the reader and Companion; select a passage and open its discovery. Confirm that the action is announced as “Explore this connection,” and that selecting a route announces its selection. Navigate to a related passage and confirm its name and context are spoken. Use Escape and Return to leave the detail, checking that focus returns to the invoking control and its name is announced. Record browser, screen reader, platform, observed announcements and any failures.
