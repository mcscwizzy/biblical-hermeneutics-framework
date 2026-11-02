# ED-1C reader acceptance

## Browser case

The new Selenium case used the real CKL and the enabled Narrative Explorer
reader. It opened 1 Corinthians 11:3 on desktop (1440×1200) and mobile
(390×844), selected the Narrative Explorer overview, and exercised the new
control and the item’s provenance disclosure.

| Check | Desktop | Mobile |
| --- | --- | --- |
| Disclosure starts collapsed | Pass | Pass |
| Record absent before activation | Pass | Pass |
| `ckl:1-corinthians#claim:1cor-kephale` appears once after activation | Pass | Pass |
| Card label reflects structured `claim_type: lexical` | Pass | Pass |
| Provenance opens through its visible summary control | Pass | Pass |
| Exact applicable relationship is `1 Corinthians 11:3` | Pass | Pass |
| Source IDs `bdag` and `thiselton-1cor` are present | Pass | Pass |
| Lexical type, disputed certainty, and dispute status remain present | Pass | Pass |
| Disclosure control is at least 44px tall | 44px | 44px |
| Document width / viewport width | 1425 / 1425px | 390 / 390px |

The item retains its projected identity, claim ID, original lexical
qualification, applicable Scripture scope, and source identities in the
existing provenance details. The disclosure describes an anchor as
“applicable” because existing passage eligibility uses Scripture-reference
overlap; the item’s own original and applicable references remain visible.
The control does not duplicate the item in a section or connection preview.
The additional view is closed by default and the record’s provenance is opened
only when the reader activates its summary.

## Negative acceptance coverage

The frontend test also verifies that the additional path does not include:

- a record already assigned to an existing section;
- a broad CKL parent object;
- a record without a source identity;
- a record with no applicable anchor for the selected passage; or
- an evidence record already selected for the connection preview.

The real-CKL API acceptance test verifies that the Proverbs Greek-order claim
retains its Proverbs 24, Proverbs 30, and Proverbs 31 source anchors while only
Proverbs 31 applies to the selected chapter; that the Mark 2 disability claim
is excluded from Mark 2:23–28; and that the held Ezekiel/Revelation bridge is
absent from accepted routes.

## Reproduction and artifacts

```bash
.venv/bin/pytest tests/gui/ne11d1/test_ed1c_additional_records.py -q -s
```

Result: **2 passed**. Browser output recorded viewport measurements and exact
source/scope identities for both sizes. Selenium screenshots for this run were
written outside the repository under `/tmp/pytest-of-johnwalker/pytest-401/gui-artifacts0/`:

- `ed1c-kephale-desktop-collapsed.png`
- `ed1c-kephale-desktop-expanded.png`
- `ed1c-kephale-mobile-collapsed.png`
- `ed1c-kephale-mobile-expanded.png`

The screenshots are local test artifacts, not committed project assets. The
browser regression itself is committed as source and can regenerate them.
