# G3 Nations and Babel evidence review

Transaction: `GENESIS_G3_NATIONS_BABEL_EVIDENCE_EXPANSION`

Base: `6bb6075d5b4142110b88a6636dcf04d27146b1ad` (latest clean `origin/master`, after G2 merge)
Branch: `feat/genesis-g3-nations-babel`

## Existing evidence audit

Genesis 10 began with 56 evidence items and 3 synthesis units but was classified GAP. The 56 split into 44 geography-only place snippets, 7 generic background items (4 FAQ and 3 Babel legacy fields), 5 Genesis book-level items, no later reception, and no structured passage-specific item. Synthesis used only `genesis-literary-movement`; the large raw count did not amount to Table coverage.

Genesis 11 began with 21 evidence items and 3 synthesis units but was classified SPARSE. Fifteen were generic legacy fields (8 person-object, 4 FAQ, 3 Babel fields), 6 were book-level context, and none was a structured passage-domain item. Published commentary consumed one of the three synthesis units; the 15 generic fields were unused.

## New object and coverage

Created `framework/canonical_library/objects/cultural_background/genesis-nations-babel-context.json` (`genesis-nations-babel-context`, `cultural_background`). Object count changed 680 → 681; cultural-background count 45 → 46. No legacy shared object was edited, and all relationships are one-way.

The object adds 29 accepted structured evidence items: 13 directly anchored in Genesis 10 and 16 in Genesis 11. All 29 candidate item records match production and were used in chapter synthesis. Genesis 10 is now 82 evidence / 17 synthesis units (evidence hash `a1e373e87e93821e6f0aa3920a5afb050c7da30b4e019252afddb33cb4f5e58f`; synthesis hash `fd851519230b1092100ae5db3e5945b1358c74ccb3ece3e093cda7d517efd06e`) and classifies GOOD under the G0 dimensional coverage approach. Genesis 11 is now 53 / 17 (evidence hash `514eb7573bee01c46b1fcfb03249c8f90182bfbc1c9504a47eab1e006b043361`; synthesis hash `57baace0ce5e073c2716fe2da00421f4541bcc5607b281f9108d38f16d99b086`) and classifies GOOD.

## Interpretation and claim dispositions

The Table is handled as a literary and ethnogeographic ordering of clans, languages, lands, and peoples, with eponymous and personal referents both allowed. Genesis 10’s language notices before the Babel episode are explained through responsible literary/compositional readings, not treated automatically as contradiction. Japheth, Ham/Canaan, and Shem identifications use `SECURE_OR_WIDELY_ACCEPTED`, `PROBABLE`, `DISPUTED`, and `UNKNOWN` levels; the Table is not a modern global map or racial taxonomy.

Nimrod is described from the wording and city list; hunting is not made inherently evil, `lifnei YHWH` remains debated, and no named ruler is asserted as his identity. Peleg’s “earth divided” receives social, territorial, political, and Babel-related possibilities; continental-drift readings are rejected. Etemenanki is a bounded ziggurat comparison, not the proven Tower of Babel. Archaeological sources support mudbrick/fired-brick and bitumen construction context.

“Make a name” is situated in ancient royal building/memory practices and contrasted with the following promise concerning Abram in Genesis 12:2; Genesis 12 is prose context only, never an applicability anchor. Divine descent is read as narrative irony. “Let us go down” preserves divine-council, plural deliberation, and literary readings; it is not declared to be the immediate grammatical statement of the Trinity. Babel/balal is explained as Hebrew narrative wordplay distinct from Babylon’s Akkadian etymology.

Genesis 11:10–32 is covered through the Shem lifespan genealogy, MT/LXX/Samaritan textual chronology differences, and Terah’s family/route notice naming Abram, Nahor, Haran, Lot, Sarai, and Milcah. Southern Ur is commonly favored but not certain; Haran’s role and Sarai’s barrenness are stated without importing later fulfillment.

Candidate dispositions: 29 accepted; claims of a proven Nimrod identification, found Babel tower, modern race encoding, Peleg/continental drift, and Babel as technical linguistic science rejected; exact identities/locations of several ethnonyms, Calneh, Nimrod, and Ur remain unresolved or withheld. All 20 local source records are accepted; three are identity-preserving local aliases.

## Source ownership and applicability

Source ownership audit: `0 existing historical source-owner rows changed`; 20 new source IDs belong only to the G3 object. Alias bibliographic identity, publication facts, stable locators, and original works were checked. Scripture applicability is restricted to Genesis 10–11. No later comparative passage, ancient parallel, or reciprocal relationship was indexed. The Genesis 11:4/12:2 comparison remains non-applicability prose.

## Impact and tests

Post-apply comparison covered all 1,189 canonical chapter inputs and found exactly Genesis 10 and Genesis 11 changed (comparison SHA `b9310e0090ee661b7c7c39c066e9f8414548edac4acdf850927dd3b8867577f3`). All 16 requested controls match base exactly. Runtime DB build and verification pass at 681 objects, 2,329 claims, 5,141 sources, and 901 evidence items (inventory fingerprint `07ea043978df7cdb7678523e688f4beac4294aa42c6ca015685de87dbb357534`; database SHA `923a74bb4395d1c2a83efd04c8dc1e3dcafbd417763c2f32c355796ff3dbbc9c`).

Commentary v1.2 was not regenerated or modified. Its packaged release diagnostics and checksum verification pass; manifest identity is `1c8972058420f00c2c9f05f52e7924566bf9fb3f56547d16c4c8b9f1f48b65d7` with 973 indexed files. Genesis 10 and 11 are marked as future stale Commentary inputs. The combined test run had 18 passes and 2 inherited failures in the historical 75-chapter promotion artifact: it pins CKL SHA `19c66f...`, already stale on the post-G2 base (G2 documented the same two failures). Exact mismatch is limited to the CKL database protected contract; packaged Commentary identity/checksum/state tests pass.

Candidate replay, whole CKL schema, source/provenance, typed-target, relationship, applicability, G0 classification, legacy fallback, isolated source-owner, controls, and full-corpus gates pass. `git diff --check` passes. The transaction is committed and pushed on `feat/genesis-g3-nations-babel`; no merge or deployment was performed.

Object SHA-256: `ee22202a8bfc1be62469d1e710ae2383149ecad445dc4d721008a18d42a22f23`

## Accepted evidence ID index

Genesis 10: g10-table-structure, g10-languages-before-babel, g10-genealogical-ethnography, g10-ancient-geographic-horizon, g10-japheth-identification-confidence, g10-ham-cush-mizraim-canaan, g10-shem-line-to-eber, g10-islands-coastlands, g10-nimrod-mighty-hunter, g10-nimrod-city-list, g10-canaan-boundaries-peoples, g10-peleg-divided-earth, g10-table-not-modern-map

Genesis 11: g11-shinar-babylon, g11-brick-bitumen, g11-city-tower-ziggurat-context, g11-top-in-heavens, g11-make-a-name-and-abram, g11-prevent-dispersion, g11-yhwh-came-down-irony, g11-let-us-go-down, g11-babel-balal-wordplay, g11-language-confusion-etiology, g11-scattering-narrative-movement, g11-shem-genealogy-lifespans, g11-genealogy-textual-chronology, g11-ur-of-chaldeans-identification, g11-terah-route-to-haran, g11-sarai-barrenness-setup

The focused G3 regression suite rerun passed 4/4. The combined G3/G2/G1R/Commentary run passed 18 tests and reproduced only the two documented historical CKL database contract failures described above. `git diff --check` passes.
