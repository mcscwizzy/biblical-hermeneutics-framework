# CKL Explanation Enrichment Progress

This directory tracks the library-wide explanation review requested for the
CKL. The machine-readable inventory in `progress.json` has one row for every
CKL object. Rows remain `pending_review` until all applicable explanatory fields
in that object have been examined. `in_progress` marks a record with a reviewed
and validated field batch but unfinished object-level coverage. It is not
counted as a fully enriched, unchanged, or skipped object.

## Baseline

- Branch: `feat/ckl-explanation-enrichment`
- Base: `origin/master` at `0c9c78afeccc210d7e81f55e32a980c1c4673df4`
- Inventory: 687 objects
- CKL validation: 687 valid, 0 errors, 14 pre-existing warnings
- Protected-field hashes are compared with the fetched base revision.
- ED-7 currently classifies 71 evidence records as withheld from reader
  promotion. Those classifications, NE-9C curations, NE-10 bridges, and held
  candidates remain protected inputs.

## Current checkpoint

At this checkpoint, **10 objects are enriched**, **47 are unchanged because they
are already sufficient**, **42 are skipped pending source or identity
research**, and **588 remain pending review**.

Batch 001 clarified four existing Genesis 5 claim rationales: the genealogy's
repeated pattern, its mortality refrain, Enoch's distinct ending, and the
transition toward Noah. Batch 002 completed the Genesis object review. It
strengthened the book summary, clarified additional claim rationales, and
replaced repetitive wording in nine Genesis 2 passage-relevance explanations.
The detailed historical and literary contexts were already careful and were
left intact. The ancient Near Eastern comparison claim and Genesis 5 textual
variant evidence were not expanded because their source arguments were not
independently rechecked.

Both Genesis validation runs passed with 1 valid object, 0 errors, and 0
warnings. The full CKL validator reports 687 valid objects, 0 errors, and the
same 14 warnings as baseline. CKL schema, packaging, retrieval, service, and
precision regressions passed 107 tests and 4 subtests. Source-lock and claim
scope checks passed 35 tests; NE-9C/NE-10 projection and curation regressions
passed 73 tests. API test collection remains unavailable because `fastapi` is
not installed. Per-batch results and protected-field fingerprints are in
`progress.json`.

The first archaeology record, Arad Ostraca, was reviewed and left unchanged.
Its CKL summary and literary context refer to Lachish, Jerusalem, and Joshua;
its Scripture references do not establish an Arad artifact connection; and its
four source entries lack bibliographic locators and claim support. A reliable
explanation needs new source research identifying the artifact, excavation,
publication, and any relevant biblical connection. The object has 10 existing
section-status warnings, unchanged from baseline.

The Babylonian Chronicles object was also reviewed and left intact: it already
explains the 597 BCE notice, the limits of what BM 21946 records, its
Babylonian chronicle setting, and the qualified identification of the city of
Judah. The Balaam Inscription object was skipped for the same source-integrity
reason as Arad: its title and generic text do not match its source records and
biblical anchors. Research must establish which inscription the entry intends
before any explanatory prose can be safely written.

The Bronze Snake record was also held. Its title points to the serpent in
Numbers 21, while its summary and historical context describe the Merneptah
Stele and its reference to Israel. Its source records do not resolve that
subject mismatch. The CKL needs a reviewed correction or separate records
before either topic can be enriched safely.

The Mount Ebal Altar Discovery entry was held because its content instead
describes Qumran and the Dead Sea Scrolls, including unrelated Scripture
anchors and source IDs. The entry needs object identity reconciliation before
any archaeological explanation can be written.

The Nimrud Reliefs record was held because its summary describes the Lachish
relief cycle, while the title and generic source IDs point to Nimrud/Nineveh.
It needs the relief cycle identified precisely before the record can be
expanded.

The Pool of Bethesda entry was held because its current references and sources
point to unrelated creation/City of David material rather than John 5 and the
pool. Site identification and relevant excavation publications need to be
verified before any connection is written.

The Pool of Siloam Discovery entry was also held: its explanatory notes and
source IDs describe the tunnel inscription, while the title names the pool.
The pool and inscription need distinct, verified evidence and passage links.

The Siloam Inscription and Taylor Prism entries were held because their source
records lack artifact identifiers, locators, and source-supported claims. The
Siloam entry needs a verified inscription text and tunnel connection; Taylor
Prism should be reconciled with the better-supported Sennacherib Prism record.

The Tel Dan Stele and Tel Rehov Honey Workshop entries were both held because
their source records and Scripture links instead describe the Tel Dan Stele.
The named objects need separate, site-specific records and verified excavation
sources before contextual prose can be added.

Tell Dan Excavations, Tell es-Safi Excavations, Temple Mount Area Finds, and
Wadi Murabba'at Scrolls were held because their records respectively repeat
stele material, mix site identities, describe Qumran material, or lack
site-specific manuscript evidence. The Temple Warning Inscription entry was
left unchanged; it already explains the warning's placement, its relation to
the temple boundary, and the limited connection to Acts 21 with a museum source.
All five records passed object validation with zero errors and the same ten
pre-existing section-status warnings.

The Merneptah Stele and Jerusalem Stepped Street explanations were left intact.
Their recorded inscription, scholarly volume, and Israel Antiquities Authority
excavation report support the existing descriptions, contextual connections,
and interpretive limits. The Moabite Stone and Pilate Stone entries were held:
their explanatory notes refer to significant inscriptions, but the recorded
source lists are title-only placeholders without locators, URLs, or support
links. All four objects passed validation with zero errors and ten existing
section-status warnings each.

Samaria Palace was held because the title names Samaria but the summary and
source record describe Nineveh. Its other contextual fields and biblical
anchors are generic or unrelated, so the intended artifact must be established
before any explanation can be responsibly written.

The Exile and Return Storyline summary and contexts now connect the named
passages more concretely: Deuteronomy 30's promised gathering, Jerusalem's fall
in 2 Kings 25, Jeremiah's address to people living in exile, and Ezra's account
of return are set beside later restoration language. The updated wording also
clarifies that biblical return language can describe both historical return
and a wider canonical hope. Scripture anchors, source identities, claims, and
relationships were unchanged.
The updated object and full library both validate with zero errors; the full
validator reports the same 14 pre-existing warnings, including this object's
section-status warning. The targeted content-quality and retrieval test command
was interrupted after 20 passing test markers because it continued at roughly
30 seconds per test and had not produced a summary. No failure appeared before
interruption; the final test result remains unavailable.

Shiloh Excavations was held because its sources and Scripture links point to
Jerusalem and general creation texts rather than site-specific Shiloh evidence.
The record needs excavation phases and relevant biblical anchors reviewed.

Qumran Archaeological Site, Qumran Caves, and Samaria Ostraca were also held:
their records lack manuscript/site-specific evidence or contain mismatched
source and Scripture links. The Sennacherib Prism entry was left unchanged
because it already explains the annals and Lachish reliefs as separate Assyrian
royal presentations, distinguishes artifact dates from the 701 BCE campaign,
and qualifies comparison with Kings and Isaiah.

Beth Shean was skipped because its source entries lack bibliographic details
and its brief summary does not identify the excavation contexts behind its
period labels. The Black Obelisk explanation was left unchanged: it already
connects the tribute register with Jehu's reign while distinguishing the
Assyrian imperial display from the biblical account and preserving uncertainty
about the figure and the designation "House of Omri."

Seven more archaeology records were held for research because their source
entries lack locators or claim support, or their titles, summaries, and
Scripture anchors identify different subjects. These include Caesarea,
Caiaphas, City of David, Dead Sea Scrolls, Ein Gedi, Elephantine, and Gezer.
The Cyrus Cylinder record was left unchanged because its object identity,
inscription setting, comparison with Ezra, and policy limits are already
explained with source-linked qualifications. All eight objects validated with
zero errors and the same ten pre-existing section-status warnings each.

Eight additional archaeology objects were held: Gibeon wine jars, Hazor,
Herodium, Hezekiah's tunnel inscription, the James Ossuary, the Ketef Hinnom
silver scrolls, the Kurkh Monolith, and the Lachish city gate. Their records
either use generic or mismatched sources, omit the relevant excavation or
inscription evidence, or lack a verified link between the artifact and the
passages. Each passed single-object validation with zero errors and the same
ten pre-existing section-status warnings.

In the next review group, the Lachish Reliefs explanation was already
sufficient: it describes the Assyrian visual account and its royal purpose,
then distinguishes that evidence from Kings and Isaiah. Lachish Ostraca,
Masada, Megiddo, and the Mesha Stele were held because the current CKL entries
lack specific artifact or stratigraphic references tied to their biblical
anchors. Their source details need repair or review before expansion.

Batch 035 reviewed Exodus, Ezekiel, Ezra, and Galatians. Five Exodus claim rationales now explain how the book moves beyond departure from Egypt toward covenant and divine presence, how the Merneptah reference is useful but limited, and how ancient Near Eastern parallels provide comparison without proving dependence. Ezekiel, Ezra, and Galatians already have accessible book summaries and context, detailed claim explanations, and specific interpretive notes that preserve uncertainty; their prose was left unchanged. All four objects validate with zero errors or warnings, and the full CKL remains at 687 valid objects, zero errors, and the same 14 baseline warnings. No retrieval test was run because the only edits were claim rationales, which are not used by the retrieval index or standard reader modal. The next pending object is `habakkuk.json`.

Batch 036 reviewed Habakkuk. Its summary, historical and literary context, 28 claims, and 46 interpretive notes already explain the Chaldean horizon, the book's complaints and woes, disputed Hebrew and textual questions, Second Temple reception, and limits on modern analogy in accessible, source-aware language. It was left unchanged after single-object validation passed with zero errors and warnings. The next pending object is recorded in the manifest.

Batch 037 reviewed Haggai. Its summary and contextual sections, 28 claims, and 49 interpretive notes already explain the Persian-period setting, dated oracles, priestly exchange about ritual status, and debated restoration language with detailed distinctions between text, historical reconstruction, and later reception. It was left unchanged after single-object validation passed with zero errors and warnings.

Batch 038 enriched Hebrews. Its 32 claim rationales previously repeated one generic sentence; they now explain the work's argument through Scripture, the movement from warning to communal practice, and where historical or theological interpretation remains open. The detailed summary, contexts, and 40 interpretive notes were retained. Single-object and full-library validation passed with zero errors; the full validator still reports the same 14 baseline warnings. Retrieval tests were not run because claim rationale is not indexed or rendered by the standard modal. The 40 note-level rationale fields remain unchanged because the notes themselves already explain their cautions.

Batch 039 reviewed Hosea. Its summary and contexts already explain the eighth-century northern setting, the book's layered literary form, and later Jewish and Christian reception. Its 20 claims and 32 notes distinguish the text from disputed reconstructions of marriage language, fertility practice, composition, and reuse. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 040 reviewed Isaiah. Its summary and context explain the book's Assyrian, Babylonian, Persian, and postexilic horizons, while its 19 claims and 26 notes distinguish historical referents, textual evidence, and later reception. Three typed evidence items are source-locked and were not altered; the remaining evidence explanation is already source-grounded and careful about inference. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 041 reviewed James. The summary, context, 32 claims, and 42 notes already explain its exhortative form, uncertain sender and audience, Jewish scriptural setting, economic critique, and debated faith-and-works language without flattening disagreement. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 042 reviewed Jeremiah. The summary and contexts orient readers to the book's chronology, literary plurality, and distinct Hebrew and Greek editions. Its 18 claims and 26 notes connect details to the historical crisis, clarify the limits of reconstruction, and carefully distinguish later reuse from historical referent. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 043 reviewed Job. Its summary and context already guide readers through the gap between the heavenly prologue and Job's knowledge, the long poetic debate, and the unresolved tension in the epilogue. Eight claims and 14 notes explain the friends' failed diagnosis, Job's protest, the divine speeches, and the limits of restoration language. It was left unchanged after single-object validation passed with zero errors and warnings.

Batch 044 reviewed Joel. Its summary, contexts, 22 claims, and 33 notes already explain the agrarian crisis, uncertain date, locust and army imagery, broad participation in the spirit oracle, and the book's later reuse. The notes carefully separate ecological reflection from claims about modern disasters and distinguish quotation from allusion. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 045 reviewed John. Its 45 claims and 87 notes already explain the Gospel's structure, Jewish setting, Greek textual questions, and contested readings while keeping narrative, historical reconstruction, and reception distinct. The two typed evidence records include one source-locked item and one low-confidence proposal reported with explicit limits. No changes were made, and single-object validation passed with zero errors and warnings.

Batch 046 reviewed Jonah. Its 24 claims and 44 notes already unpack the narrative's repeated structure and unresolved final question, and distinguish the eighth-century namesake from the later literary book. The notes also give careful treatment to Nineveh, the fish, plant, Hebrew idioms, Jewish liturgy, and later Gospel and Islamic reception. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 047 enriched Joshua. The reader-facing summary now draws together the transition from campaigns to allotment and covenant, including the book's own tension between broad victory summaries and notices of land still unconquered. Five claim rationales explain why that tension, Rahab's preservation, Torah-shaped leadership, and the final Shechem covenant matter. No new archaeological or conquest chronology claims were added. Single-object and full-library validation passed with zero errors; the same 14 baseline warnings remain.

Batch 048 reviewed Jude. Its 29 claims and 39 notes already explain the letter's polemical form, Second Temple Jewish traditions, textual variants, and the difference between literary use of Enoch and claims about an entire work's status. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 049 enriched Judges. The summary now makes the book's decline visible: the repeated deliverance pattern gives way to internal idolatry, sexual violence, and civil war. Six claim rationales clarify that the episodes vary, show distinct roles in Deborah's story, leave Samson's deliverance incomplete, and raise but do not settle the kingship question. No archaeological or historical reconstruction was added, and the source-locked geography evidence remains untouched. Full-library validation passed with the same 14 baseline warnings.

Batch 050 reviewed Lamentations. Its summary and contexts guide readers through the changing voices, alphabetic forms, destruction setting, and textual witnesses; 27 claims and 33 notes explain the relationship between complaint, fragile hope, trauma, and the unresolved final petition. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 051 enriched Leviticus. The summary now connects the book to Exodus's closing scene, framing its instructions around how Israel worships and lives in God's presence. Five claim rationales explain the movement from sacrifice and sanctuary toward purity, atonement, neighbor-care, and communal ethics while retaining the distinction between ritual impurity and moral wrongdoing. Single-object and full-library validation passed with zero errors; the same 14 baseline warnings remain.

Batch 052 reviewed Luke. Its summary, 44 claims, and 68 notes already explain the Gospel's Jewish setting, distinct narrative contributions, and debated textual forms while preserving uncertainty. The three typed evidence records are passage-specific: each separates a direct Greek observation from its attributed scholarly interpretation and limits the conclusion. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 053 reviewed Malachi. Its 34 claims and 67 notes already explain the disputation form, Persian-period setting, difficult marriage and tithing passages, and the relationship between Torah, Elijah, and later reception. They distinguish historical claims from later Jewish and Christian readings and guard against unsupported modern application. The object was left unchanged after single-object validation passed with zero errors and warnings.

## Reader reachability

Canonical object detail responses serialize summaries and evidence items.
Retrieval indexes evidence title, description, primary observation, scholarly
interpretation, passage relevance, and confidence rationale. Claim rationales
are serialized in canonical object detail, but the standard canonical browser
modal does not render them, and retrieval indexes claim text rather than
rationale. This batch improves the CKL research layer without claiming direct
reader display. Evidence presentation depends on the Narrative Explorer
evidence packet.

## Resume and validation

Refresh the inventory while preserving existing progress, then validate it:

```sh
python3 tools/ckl_enrichment_progress.py --sync
python3 tools/ckl_enrichment_progress.py --check
```

Validate the full CKL after each content batch:

```sh
python3 tools/ckl_validate.py
```

First Chronicles was left unchanged. Its summary and contexts already explain
the book's structure and postmonarchic setting; six interpretive notes clearly
separate textual observations from historical reconstruction and preserve
disagreement. The claims are tied to passages, and its Psalter evidence item
distinguishes the observable reuse of Psalm 106:48 from a debated proposal
about the Psalter's collection history. The object passed validation with zero
errors and zero warnings.

For 1 Corinthians, six claim rationales were expanded to show how Paul’s
argument connects the cross with status, the assembly with temple language,
embodied conduct with belonging to Messiah, idol meals with table allegiance
and conscience, Israel’s wilderness story with warning, and idol claims with
participation in sacrificial meals. The surrounding book summary, claims,
sources, Scripture anchors, and 88 cautious interpretive notes were retained.
The object and full library validate with zero errors and the same 14 existing
warnings. Claim rationales are available in canonical detail but are not
rendered in the standard browser modal or retrieval index.

First John was also left intact. Its summary, contexts, 33 claims, and 41
interpretive notes already give readers specific explanations while carefully
qualifying authorship and community reconstructions, lexical disputes, textual
variants, and later reception. The book validated with zero errors and zero
warnings.

Four 1 Kings claim rationales were expanded. They now explain how the child
judgment illustrates Solomon's discernment, why the temple prayer is followed
by a warning against assuming the building guarantees security, how the
Carmel episode moves from public allegiance to the end of drought, and how
Naboth's vineyard episode exposes royal injustice and seizure of inherited
land. The text of the claims, references, and six existing interpretive notes
were retained. The object and library validate without new errors or warnings.

First Peter was left intact. Its summary and context fields already connect
the letter's themes to its Jewish scriptural inheritance and Roman provincial
setting while limiting claims about authorship, audience, and persecution.
Thirty-two claims and 43 interpretive notes provide specific explanations and
guard against harmful overreadings. The object passed validation with zero
errors and zero warnings.

The next three book objects, 1 Samuel, 1 Thessalonians, and 1 Timothy, were
left intact. Their summaries and contexts already explain the narrative or
letter-level movement and distinguish explicit textual claims from disputed
historical, literary, and lexical reconstruction. Their claims and interpretive
notes are specific and carefully qualified; the 1 Samuel geography evidence
also remains source-locked. All three objects validated with zero errors and
zero warnings.

Second Chronicles, 2 Corinthians, and 2 John were left intact. Their summaries
and contexts already explain each book's main literary and historical setting.
Their claims, notes, and typed evidence are detailed and careful about debated
authorship, literary reconstruction, textual interpretation, and modern
application. All three objects validated with zero errors and zero warnings.

Second Kings, 2 Peter, and 2 Samuel were left intact. Their summaries and
contexts already explain the main narrative or epistolary sequence, and their
claims and notes make careful distinctions between textual observation,
historical reconstruction, and theological interpretation. Locked Naaman
geography evidence remains unchanged. All three objects validated with zero
errors and zero warnings.

Second Thessalonians, 2 Timothy, and 3 John were left unchanged. Their
summaries and contexts clearly distinguish letter-level observations from
disputed authorship, chronology, community history, and interpretation. Their
claims and notes already provide accessible explanations, source-aware
uncertainty, and careful limits on modern application. All three validated
with zero errors and zero warnings.

Acts, Amos, Colossians, and Daniel were left intact. Their summaries and
contexts already provide detailed historical and literary framing; claims and
notes carefully separate text, source evidence, scholarly reconstruction,
and later reception. Source-locked Acts geography and the four objects all
validated with zero errors and zero warnings.

Deuteronomy, Ecclesiastes, and Esther were left intact because their summaries,
claims, and notes already explain their literary and historical contexts while
carefully qualifying text, dating, and reception questions. Ephesians had 28
claim rationales that all repeated a generic sentence. Those rationales now
explain the specific textual basis or interpretive limit for each claim,
including grace and good works, Jewish-gentile reconciliation, temple imagery,
household instruction, and the armor metaphor. Claims, notes, sources, and
anchors were preserved. The four objects and full library validate with zero
errors and the same 14 baseline warnings. Claim rationales are not currently
rendered in the standard browser modal or indexed by retrieval.

The next work unit is `objects/books/exodus.json`.
Record field paths, actual outcomes, validation evidence, and checkpoint commit
IDs in `progress.json`.
