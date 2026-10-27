# NE-11B review: Psalm 22:1 and Mark 15:34

## Decision

**NEEDS_CKL_REFINEMENT.** The wording in Mark 15:34 is a direct quotation of the opening lament in Psalm 22, but the existing CKL claim does not identify Mark 15:34 or state this precise relationship. Do not promote a passage route from the current claim. A verse-scoped CKL record and source trail are required first.

| Route field | Review decision |
|---|---|
| Proposed stable supporting CKL identity | New record: `mark#claim:mark-psalm-22-1-mark-15-34` (identity reserved here; it does not yet exist) |
| Existing related CKL identity | `mark#claim:mark-crucifixion` |
| Source passage | `Psalm 22:1` (English/standard numbering; MT Psalm 22:2) |
| Receiving passage | `Mark 15:34` |
| Relationship category | `direct_quotation` |
| Direction | `source_to_receiving_text` |
| Reciprocal display | Yes, as reversible navigation; preserve the source-to-receiver direction in route metadata |
| Supporting CKL source IDs for the future exact record | `mark-greek`, `psalms-mark`; the latter needs an exact verse-level locator and identified Hebrew text edition before it can support this route precisely |
| Existing source verification | `mark-greek`: SBLGNT critical Greek text, directly compared at Mark 15:34. `psalms-mark`: CKL source entry identifies Psalms 2, 22, 69, 110, and 118, but has no bibliographic edition or verse locator. `marcus-mark-8-16` and `postcolonial-mark` are attached to the broad claim but have not been independently verified for this exact quotation. |
| Canonical data required | Yes. Add an exact CKL claim/evidence record and resolve the source-scope gap before NE10 promotion. |

## Textual comparison

In the Masoretic Text, the verse commonly numbered Psalm 22:1 in English editions is Psalm 22:2. Its opening is `אֵלִי אֵלִי לָמָה עֲזַבְתָּנִי` (“My God, my God, why have you forsaken me?”). The Septuagint numbers it Psalm 21:2 and reads `Ὁ θεὸς ὁ θεός μου, πρόσχες μοι· ἵνα τί ἐγκατέλιπές με;`. It includes `πρόσχες μοι` (“attend to me”) and uses `ἵνα τί` before “have you forsaken me.” ([Masoretic Psalm 22](https://www.mechon-mamre.org/p/pt/pt2622.htm); [Septuagint Psalm 21](https://www.die-bibel.de/bibel/LXX/PSA.21))

SBLGNT Mark 15:34 gives Jesus’ cry in Semitic transliteration—`Ἐλωῒ Ἐλωῒ λεμὰ σαβαχθάνι`—and then supplies a Greek interpretation: `Ὁ θεός μου ὁ θεός μου, εἰς τί ἐγκατέλιπές με;`. Mark’s Greek has no equivalent of the Septuagint’s `πρόσχες μοι`, changes the order of “my God,” and uses `εἰς τί` rather than `ἵνα τί`. The transliterated form is not the same as the Hebrew spelling; it is commonly identified as Aramaic, but this review does not adjudicate dialect or manuscript-level reconstruction. ([SBLGNT Mark 15](https://www.thekoinebible.com/text/sblgnt/mark/15.html); [SBL Greek New Testament project](https://www.sbl-site.org/resources/digital-texts/sbl-greek-new-testament/))

These differences are consistent with a direct quotation translated and transliterated across languages, not a verbatim reproduction of the Septuagint Greek. The source is identifiable from the repeated invocation and the distinctive abandonment question. Under BHF’s `direct_quotation` rule, the connection clears the textual threshold: a source passage reproduces identifiable, substantial wording, and the wording is traceable to a particular passage. The citation is limited to the opening verse. It does not establish that all of Psalm 22 is quoted, predicted, or fulfilled by Mark.

## What is directly observed, and what remains interpretive

- **Directly verifiable in Scripture:** Psalm 22 begins with the lament in question; Mark 15:34 places a closely corresponding Semitic cry and Greek rendering on Jesus’ lips. The sentence is explicit in Mark. Psalm numbering differs between the standard English reference and MT/LXX numbering.
- **Scholarly material independently inspected:** Marijke H. de Lang identifies the cry in Mark 15:34 as a quotation of the first half of the Psalm verse and separately argues that Mark 15:34–37 may narrate one cry rather than two. Her article presents an argument about Mark’s composition, not an uncontested textual conclusion. ([de Lang, “One Cry or Two?”](https://bskorea.or.kr/data/pdf/45-10%20One%20cry%20or%20two%20Mark%E2%80%99s%20composition%20of%20Mark%2015.34-37%28Marijke%29.pdf))
- **Scholarly interpretation independently inspected:** Jason Robert Combs argues for an extended inverted allusion to Psalm 22 across Mark 15, while discussing earlier scholarship that disputes the proposed sequence and force of some allusions. This supports the existence of a scholarly reading of the wider Passion narrative; it does not make the whole-Psalm interpretation a fact or enlarge the direct quotation endpoint beyond Mark 15:34. ([Combs, “An Extended Inverted Allusion to Psalm 22 in Mark 15”](https://www.cambridge.org/core/journals/new-testament-studies/article/an-extended-inverted-allusion-to-psalm-22-in-mark-15-reading-reversal-in-the-markan-passion/96C943213FCDCF9A1BBD64A91E5AC75E))
- **Bibliography recorded in CKL but not independently inspected for this exact claim:** Joel Marcus, *Mark 8–16* (Yale University Press, 2009), source ID `marcus-mark-8-16`; and the edited volume *Postcolonial Perspectives in African Biblical Interpretations* (SBL Press, 2012), source ID `postcolonial-mark`. Their presence in `mark#claim:mark-crucifixion` does not prove they support this particular wording or exact endpoint. The relevant Marcus discussion and the relevant chapter in the edited volume remain to be checked. ([Marcus bibliographic record](https://yalebooks.yale.edu/book/9780300141160/mark-8-16/); [Postcolonial volume chapter record](https://www.jstor.org/stable/jj.11589034.31))
- **Debated interpretation:** Whether the quotation principally expresses abandonment, invokes the Psalm’s movement toward trust, or participates in a larger literary pattern is a theological and literary question. This route should state only the textual quotation and leave the interpretation open.
- **Evidence gap:** The current CKL record has broad scripture references `Mark 15:16-41` and `Psalm 22:1`; its source IDs do not identify Mark 15:34 as a specific quotation. It also lacks a verse-specific Hebrew witness/source record. Its description concerns Mark’s crucifixion scene generally. The route eligibility contract requires the supporting record to contain the exact passage scope or to name it expressly; broad overlap is insufficient.

## Record and collision checks

The inspected source record is `mark#claim:mark-crucifixion`, with `claim_type=biblical_text`, `certainty=textually_explicit`, `dispute_status=major_scholarly_disagreement`, scripture references `Mark 15:16-41` and `Psalm 22:1`, and attached IDs `mark-greek`, `marcus-mark-8-16`, and `postcolonial-mark`. It is a composite narrative summary, not a verse-pair claim.

The NE-9C scan found no curated Psalm 22–Mark 15:34 pair. It did find an unrelated Psalm 22:1–31 thematic route from `ckl:what-is-a-psalm` to `ckl:prayer-theme`; that is not a Mark relationship and does not conflict with the proposed quotation route. The NE-10 scan found no exact Psalm 22:1–Mark 15:34 bridge or held candidate. No registry records were changed.

## Evidence-grounded future route contract

After a separately authorized CKL change, an NE10 route may be added only if the new exact CKL record:

1. Uses identity `mark#claim:mark-psalm-22-1-mark-15-34` (or records a documented identity replacement before registry work).
2. Names exactly `Psalm 22:1` and `Mark 15:34` in its Scripture scope and describes the quotation at those endpoints.
3. Attaches `mark-greek` and a resolved source ID for Psalm 22 whose record identifies the Hebrew witness/edition and verse (MT 22:2 / standard 22:1). A broad Psalm-book locator alone does not meet this condition.
4. Supports category `direct_quotation`; records source-to-receiver direction and permits reversible navigation without claiming the quotation runs historically in both directions.
5. Uses an explanation limited to the transliterated cry and Greek rendering in Mark 15:34. It must not say that the entire Psalm is quoted or fulfilled.
6. Keeps the unresolved theological interpretation and manuscript/dialect limitations visible.

Until then, the connection is a documented research decision, not a confirmed Narrative Explorer route.
