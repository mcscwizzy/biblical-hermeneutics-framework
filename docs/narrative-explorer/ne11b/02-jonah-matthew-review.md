# NE-11B review: Jonah 1:17 and Matthew 12:40

## Decision

**READY_AS_IS** for a narrowly scoped later-canonical-reception bridge, subject to the ordinary explicit NE10 registry authorization and validation process. The existing CKL claim expressly names both endpoints and states that the narrated duration in Jonah is later taken up in Matthew 12:40. No CKL edit is needed for this narrow route. This decision does not claim that Jonah was originally written as a prediction.

| Route field | Review decision |
|---|---|
| Stable supporting CKL identity | `jonah#claim:jonah-three-days` |
| Source passage | `Jonah 1:17` (standard English numbering; MT and LXX Jonah 2:1) |
| Receiving passage | `Matthew 12:40` |
| Relationship category | `later_canonical_reception` |
| Direction | `source_to_receiving_text` |
| Reciprocal display | Yes, as reversible navigation; preserve Jonah-to-Matthew as the historical reception direction |
| Supporting CKL source IDs | `jonah-masoretic` and `jonah-new-testament` for the primary-text observation; both are attached to the exact claim. `graybill-kaltner-mckenzie-jonah` is also attached, but is not relied on for a scholarly interpretation in this decision because the relevant commentary pages were not independently inspected. |
| Source verification | Hebrew MT Jonah and the LXX Jonah 2:1 checked; Matthew 12:40 and its immediate context checked in SBLGNT. The primary textual statement is directly verifiable. Academic debate about the duration, idiom, and “heart of the earth” remains open. |
| Canonical data required | No for this route’s exact passage claim. A later NE10 registry change would be needed to expose it at runtime. |

## Textual scope and comparison

The current CKL claim text is: “Three days and three nights is a narrated duration for Jonah in the fish and later becomes important in Matthew 12:40; attempts to derive a precise biological chronology exceed the text.” Its Scripture references are exactly `Jonah 1:17` and `Matthew 12:40`, and its source IDs are `jonah-masoretic`, `jonah-new-testament`, and `graybill-kaltner-mckenzie-jonah`.

The CKL uses standard English verse numbering for `Jonah 1:17`. That verse is MT Jonah 2:1 and LXX Jonah 2:1: the Lord appoints a great fish/large sea creature, and Jonah is in it three days and three nights. Hebrew `דָּג גָּדוֹל` is “great fish”; the Septuagint uses `κῆτος μεγάλῳ`, a large sea creature. The LXX continues with `τρεῖς ἡμέρας καὶ τρεῖς νύκτας`. ([Hebrew Jonah, MT 2:1](https://www.mechon-mamre.org/p/pt/pt1702.htm); [Septuagint Jonah 2:1](https://www.die-bibel.de/bibel/LXX/JON.2))

Matthew 12:39–41 calls the sign “the sign of Jonah.” In verse 40 Matthew makes an explicit comparison: “as Jonah was … so the Son of Man will be …,” repeating the Greek duration `τρεῖς ἡμέρας καὶ τρεῖς νύκτας`; Matthew also changes the destination image to “the heart of the earth.” Verses 41–42 return to Jonah’s preaching and judgment. The wording establishes a Matthean reuse and application of Jonah’s narrative; the larger comparison is best represented as later canonical reception, not solely as a direct-quotation edge. The Greek wording is also shared with the LXX phrase, but Matthew does not introduce this saying with a formal citation formula. ([SBLGNT Matthew 12](https://www.thekoinebible.com/text/sblgnt/matthew/12.html); [Matthew 12, USCCB notes](https://bible.usccb.org/bible/matthew/12))

## Verification categories and limits

- **Directly verifiable in Scripture:** Jonah’s narrative assigns a three-days-and-three-nights duration inside the fish. Matthew explicitly compares Jonah’s time with the Son of Man’s time “in the heart of the earth” and places the saying within the sign-of-Jonah dispute. The Jonah endpoint is one verse, not Jonah’s entire narrative.
- **CKL sources inspected:** `jonah-masoretic` identifies the Hebrew book with MT chapter numbering; `jonah-new-testament` locates Matthew 12:38–41 and other reception texts. The claim’s scoped references and these primary-text sources jointly support the narrow route. `graybill-kaltner-mckenzie-jonah` is Rhiannon Graybill, John Kaltner, and Steven L. McKenzie, *Jonah: A New Translation with Introduction and Commentary* (Yale University Press, 2023), but its book-level bibliography entry is not a substitute for inspection of pages addressing the duration or Matthew’s reception. No page-specific claim is attributed to it here. ([Publisher record](https://yalebooks.yale.edu/book/9780300206678/jonah/))
- **Scholarly material independently inspected:** Kenneth L. Waters argues for reading Matthew’s “heart of the earth” topologically in relation to Jerusalem and interprets the Jonah comparison as suffering rather than only death, burial, or resurrection. He also discusses different ways to understand the interval. This is a specific scholarly proposal and is not adopted as the route’s description or presented as consensus. ([Waters, “Jesus in the Heart of the Earth”](https://journals.sagepub.com/doi/full/10.1177/21582440211014178))
- **Uncertainty retained:** The phrase does not by itself settle whether ancient inclusive reckoning, idiom, or a strict elapsed interval is intended. Nor does it settle the referent of “heart of the earth,” the temporal alignment with Jesus’ death and burial, or Matthew’s literary and theological intent. The relationship establishes Matthew’s later use of Jonah; it does not establish that Jonah’s original narrative was composed as a prediction of Jesus.
- **No unsupported source assertion:** The Graybill et al. source is present in CKL but its relevant pages were not available for this review. It is not counted as independently inspected support for a precise chronology or typological interpretation.

## Route and collision review

The exact pair is scoped in `jonah#claim:jonah-three-days`. The CKL claim is intentionally modest: a narrated duration becomes important in Matthew, while precise biological chronology exceeds what the text establishes. `jonah-masoretic` covers Jonah 1:1–4:11 with MT numbering; `jonah-new-testament` covers Matthew 12:38–41. Their scopes include the two precise endpoints.

The NE-9C authored registry and the 43 active NE-10 bridges contain no Jonah 1:17–Matthew 12:40 relationship. The held NE-10 inventory also contains no Jonah/Matthew candidate. No duplicate or conflicting relationship was found, and no registry was changed.

## Future route contract

If NE10 implementation is later authorized, it should add one bridge with:

- ID `jonah-1-17-matthew-12-40-sign-of-jonah`.
- Supporting record `jonah#claim:jonah-three-days`.
- `passages`: `Jonah 1:17`, `Matthew 12:40`; `source_text_passage`: `Jonah 1:17`; `receiving_text_passage`: `Matthew 12:40`. Show the standard endpoint in the route and explain MT/LXX Jonah 2:1 in evidence details.
- Category `later_canonical_reception`; direction `source_to_receiving_text`; reciprocal display enabled while retaining that direction.
- Selected supporting source IDs `jonah-masoretic` and `jonah-new-testament`. Do not use the uninspected Graybill commentary as the sole or implied scholarly authority.
- A description saying that Matthew explicitly compares the duration in Jonah’s fish episode with the Son of Man’s time in the heart of the earth.
- Uncertainty stating that chronology, idiom, “heart of the earth,” and the literary force of the comparison remain debated; do not call Jonah’s narrative an original prediction.

This route is eligible on the current CKL evidence, but it is not yet a runtime route. Do not add it without the later NE10 registry authorization.
