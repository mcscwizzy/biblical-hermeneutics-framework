# ED-5 connection journeys

## Jonah 1:17 and Matthew 12:40

The scripted suite resolves both passage endpoints and finds exactly one
`jonah-1-17-matthew-12-40-sign-of-jonah` route from each. It confirms the
source passage is Jonah 1:17, the receiving text is Matthew 12:40, direction
is `source_to_receiving_text`, the supporting CKL claim is
`ckl:jonah#claim:jonah-three-days`, and the explanation and uncertainty fields
are present. The explanation records standard English Jonah 1:17 numbering
alongside MT/LXX Jonah 2:1.

The reader presents the textual direction and states navigation can be
followed from either passage. The route disclosure separates the CKL-documented
claim and its sources from authored CKL relationship edges. It retains the
recorded interpretive caveat; it does not imply that every similarity is an
intentional allusion.

## Governance and continuity

The current-state read-only compatibility validator passes with 3,925 reviewed
relationship identities, 433 accepted current curation identities, 44
verified bridges, and 7 held candidates. The bridge and held registry hashes
match the baseline. The held Ezekiel 40–48 / Revelation 21–22 proposal remains
held. No NE-9C or NE-10 data changed.

ED-4 browser tests previously exercised back/forward, original-passage return,
and focus restoration. ED-5's new browser run could not execute in this
environment, so live restoration/focus behavior for the new overview text was
not measured. The script validates data projection and route direction, not
visible clicks or user comprehension.
