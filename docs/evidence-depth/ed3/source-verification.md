# ED-3 Source Verification

## Scope and limits

This is a machine-assisted source audit, not scholarly approval. The complete
record-by-record reconciliation is in [evidence-review-inventory.csv](evidence-review-inventory.csv).
ED-2's access categories remain in that file as historical assertions. The new
`ed3_source_access_class` and `ed3_inspection_scope` columns report what was
actually opened during ED-3.

The 99 stable evidence IDs were reconciled against the ED-2 merge-parent diff,
book object, research packet, local bibliography entry, source IDs, and exact
locator recorded in the CKL. A fresh review found relevant source material for
29 records. Eight have a full scholarly text available in a legitimate
publisher or institutional repository; three have a useful excerpt; the
remaining inspected records have an abstract, metadata, or a mixture of those
levels. The other 70 records have not had their source text freshly inspected.
Two further records expose only publisher metadata or a partial HTML excerpt,
which does not support the claim at the cited scope. All 99 outcomes are
therefore either **Supported with limitations** or **Unable to independently
verify**; none is human-approved.

The ED-2 source-access categories were 72 full-text-only, 21 abstract-only,
three excerpt-only, and three mixed full-text/abstract-only. ED-3 upgraded
Psalm 17 from abstract to full article, and independently re-opened sources
for all 21 abstract-only records, all three mixed records, and two of the
three excerpt-only records. The Psalm 34 excerpt was not freshly reproduced.
For the 72 reported full-text records, only three additional sources were
freshly re-opened as full text in this batch (Nahum 3, Proverbs 15:25–16:9,
and Psalm 110); the other 69 remain unverified at source-text level.

The committed public-domain ASV corpus resolved all 99 anchors (111 separate
reference spans and 1,112 selected verses; no missing verse in the bundled
corpus). This establishes that the anchors resolve in the application data and
supports an English-text check. It does not independently establish a Hebrew
or Greek reading, verify a critical apparatus, or amount to a full semantic
re-reading of every passage. The row-level `scripture_observation_check`
therefore distinguishes direct anchor resolution from language- and
witness-dependent assertions; all records remain subject to human review.

## What was independently inspected

| Records | Source and exact inspected scope | Result and limitation |
|---|---|---|
| `psalm-17-textual-proposals-verses-11-and-14` | Bazyliński, *The Biblical Annals* 11(3) (2021), pp. 387–410; relevant discussion pp. 398–402 and 406–407. [Official article and PDF](https://czasopisma.kul.pl/index.php/ba/article/view/12435) | The Italian full text confirms the conjecture at v. 11 and the preferred *qere* at v. 14, while reporting no consensus. The author says the BHK/BHS citation of a Hebrew manuscript for the conjecture is almost certainly unfounded. No BHK/BHS volume or manuscript image was independently examined. The CKL source note claiming that the Italian article had not been read is stale and is listed for correction. |
| `proverbs-15-25-to-16-9-mt-lxx-redaction-debate` | Macchi, *Études Théologiques et Religieuses* 99(2) (2024), pp. 381–394; text differences and 4QProvb, pp. 382–383. [University of Geneva repository copy](https://access.archive-ouverte.unige.ch/access/metadata/3a00d42d-f97b-457e-bff6-199c9845ecc9/download) | The full French article supports the described relocation/redaction proposal and preserves alternative text-history explanations. The Qumran witness is reported through the article; no fragment photograph or DJD apparatus was examined. |
| `nahum-3-8-9-one-city-text-critical-proposal` | Grütter, “A Tale of One City,” *Journal of Septuagint and Cognate Studies* 50 (2017), pp. 160–175. [Full article PDF](https://septuaginta.uni-goettingen.de/static/ioscs/pdf/volumes/jscs50.pdf) | The article supports the attributed one-city/Nineveh reconstruction and discusses the Masoretic, Greek, and Qumran data. This is the author's text-critical reconstruction, not consensus or archaeological confirmation. No witness image or critical edition was independently examined. |
| `psalm-110-order-of-melchizedek-debate` | Corley, *Salmanticensis* 64(1) (2017), pp. 41–71; phrase discussion pp. 53–54. [University repository article](https://summa.upsa.es/high.raw?id=0000128643&name=00000001.original.pdf) | Full article supports preserving multiple renderings of the Hebrew phrase and the later history of interpretation. No manuscript apparatus was examined. |
| `psalm-98-yhwh-kingship-in-book-four-cluster` | Blunda Grubert, *Salmanticensis* 67(1) (2020), pp. 11–34. [University repository article](https://summa.upsa.es/high.raw?id=0000128664&name=00000001.original.pdf) | The Spanish article supports an attributed literary/liturgical proposal about Psalms 93–100, including 96 and 98. Any dating or performance setting remains the author's reconstruction. |
| `psalm-20-amherst63-parallel-and-direction-debate` | Ward, UCLA dissertation (2023), ch. 3, pp. 81–109, especially pp. 82–83; competing models pp. 20–22. [UCLA repository record and dissertation](https://escholarship.org/uc/item/4mg6x6q4) | The dissertation gives a Demotic transcription, Aramaic normalization, translation, and commentary for col. XII, lines 11–19. It documents the parallel but presents difficult readings and divine-name identification as uncertain; it reviews opposing direction-of-dependence models. Kister (2020), pp. 426–457, was verified only through the institutional record and abstract. Neither the papyrus nor a facsimile was examined. |
| `psalm-143-in-galatians-argument-debate` | Bachmann, *New Testament Studies* 70 (2024), pp. 125–130, especially pp. 125–127. [Cambridge open-access article](https://doi.org/10.1017/S0028688523000231); Moore (2022), pp. 461–473, [publisher abstract](https://www.cambridge.org/core/journals/new-testament-studies/article/abs/psalm-1432-and-the-argument-of-galatians-310/32ACF463774FCB186B43211586B20D9B) | Bachmann explicitly contests Moore's use of Psalm 143:2 as a premise in Galatians 3:10 while retaining the echo in Galatians 2:16c. The CKL appropriately preserves disagreement; no NE-9C/NE-10 relationship was created. |
| `psalm-7-cush-superscription-and-setting-limits` | Obiorah, *Verbum et Ecclesia* 42(1) (2021), article a2141, full open article; Berger (2014), pp. 279–296, [SAGE abstract and metadata](https://journals.sagepub.com/doi/abs/10.1177/0309089214527206) | Obiorah's article and Berger's abstract support distinct, competing historical/literary proposals. Berger's full article and relevant ancient-version editions were not inspected; neither proposal is treated as a biography of David. |

Fresh abstract/metadata checks for other access-limited records are described in
the CSV by evidence ID, source URL, and exact scope. These include the official
KCI record for 2 Chronicles 25, Cambridge's Mark 7 abstract and displayed
footnote, Peeters abstracts for Psalms 40, 58, 109, 141, and 73, Mohr's
abstracts for Psalms 61 and 63, the USP abstract for Psalm 4, and publisher or
institutional records for John 10:22, Psalm 18, Psalm 21, Psalm 49, Psalm 70,
Psalm 75, Psalm 105, and Psalm 23. Abstracts are treated as support only for
the conclusion they actually state. For Psalm 23, the current publisher page
exposed bibliographic metadata but no abstract or article argument; its
hospitality proposal remains unable to be independently verified in this
batch. For Psalm 144, the publisher page exposed metadata and partial HTML, but
not enough of the cited argument to independently verify the interpretation.

The authorized Augsburg Fortress sample for Psalm 80 exposes pp. 16–17 of
Streett's chapter, where the psalm's communal lament form and ambiguity around
the vine/son figure are introduced. The full chapter was unavailable. Gilbert's
Proverbs 28 article was checked against the Peeters abstract and opening page
(p. 313), not its full argument. The Psalm 34 excerpt reported by ED-2 was not
freshly inspected. No restricted book or article was accessed through a
third-party mirror.

## Primary textual and material evidence

No ancient artifact, papyrus, scroll image, inscription, or manuscript
facsimile was independently examined. No critical-edition apparatus was used
to decide a disputed reading. The following limits therefore remain:

- **Mark 7:3:** the Cambridge abstract and a displayed footnote were checked;
  the cited witnesses were not checked in a critical edition or manuscript
  image. The alternate reading remains Burkett's proposal.
- **Psalm 17:** the author's comparison of witnesses was read in Italian; the
  cited Hebrew manuscript apparatus was not independently inspected. The
  article itself warns that a reported manuscript support for its conjecture
  may be unfounded.
- **Psalm 58, Psalm 141, Ezekiel 22, and Ecclesiastes 10:1:** the relevant
  lexical/text-critical claims remain secondary-source dependent. Whybray's
  Ecclesiastes commentary was not opened from the unauthorized mirror linked
  in the CKL; a legitimate full copy is still needed.
- **Nahum 3:8–9 and Proverbs 15:25–16:9:** full scholarly arguments were read,
  but the 4Q385a/Greek and 4QProvb witnesses were not independently checked in
  an edition or image. The article-level reconstructions remain attributed.
- **Psalm 20:** Ward's full dissertation was read; the Morgan Library catalog
  record and BnF edition catalog were found, but the papyrus and published
  facsimile were not viewed. The parallel is not described as a manuscript of
  Psalm 20, and direction of dependence remains open.
- **Psalm 61 and Psalm 63:** LeMon's publisher abstract and an institutional
  discovery report were checked. The Hezekiah bulla's excavation context and
  primary excavation-report chapter were not inspected. The bulla does not
  independently establish the psalms' speaker.
- **Psalm 145 missing Nun:** the Israel Antiquities Authority's Leon Levy
  Digital Library catalog identifies 11Q5/11QPsa, and published contents
  records locate Psalm 145 in that scroll. The interactive catalog did not
  expose the exact column image in this review. The Nun-line attestation and
  its priority remain for direct edition/image review; no claim about the
  original reading was added or changed.

The Morgan Library catalog record for Papyrus Amherst 63 and the National
Library of Israel record for the Ophel excavation report were located as
institutional records. They confirm bibliographic/object pathways, not the
inscription readings or historical interpretations. Archaeology-service
catalog ownership remains unchanged.

## Outcome counts and human-review status

| ED-3 outcome | Records | Meaning |
|---|---:|---|
| Supported at inspected scope | 0 | No item was marked as fully supported because each record still has an unverified passage-text or primary-witness component. |
| Supported with limitations | 27 | The consulted article, abstract, or excerpt supports the already-qualified claim at the inspected scope; stated gaps remain. |
| Correction required | 0 | No demonstrated defect in the scholarly interpretation itself was established in this batch. A stale Psalm 17 source-access note is a provenance correction, not a human review decision. |
| Insufficiently substantiated | 0 | No claim was found to contradict its source; lack of access is recorded separately as unable to verify. |
| Unable to independently verify | 72 | No sufficiently relevant source text was freshly inspected, or the accessible material did not expose enough of the cited argument. |

All 99 records remain draft, in review, and human-review required. The machine
assessment does not confer approval, and all human decisions remain blank in
the review queue.
