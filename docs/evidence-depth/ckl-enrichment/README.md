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

At this checkpoint, **79 objects are enriched**, **82 are unchanged because they
are already sufficient**, **48 are skipped pending source or identity
research**, and **478 remain pending review**.

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

Batch 054 reviewed Mark. The summary, 41 claims, and 78 notes already explain the Gospel's rapid narrative, Roman execution setting, and earliest recoverable ending, while distinguishing textual variants and later canonical reception. Its single typed evidence item carefully reports an abstract-level textual proposal without treating it as settled. No changes were made; single-object validation passed with zero errors and warnings.

Batch 055 reviewed Matthew. Its 46 claims and 72 notes already explain the Gospel's Jewish setting, literary design, and major interpretive disputes in detail; one source-locked evidence item carefully records the narrated movement sequence without adding a speculative itinerary. No changes were made, and single-object validation passed with zero errors and warnings.

Batch 056 reviewed Micah. Its 34 claims and 52 notes already explain the Assyrian horizon, land and leadership critiques, disputed speaker transitions, and the book's varied Jewish and Christian reception. The notes preserve uncertainty around the Isaiah parallel, the Bethlehem ruler, and modern uses of the peace and justice passages. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 057 reviewed Nahum. Its 27 claims and 46 notes already explain the Assyrian setting, violent siege poetry, refuge language, and contested gendered imagery without flattening ethical tension. The one typed evidence record labels an alternative textual reconstruction as low confidence and explains why it does not establish geography or composition date. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 058 reviewed Nehemiah. Its summary and contexts already connect wall rebuilding with the later Torah assembly, economic restitution, covenant commitments, and the unresolved relapse in chapter 13. Eight claims and ten notes explain the Persian setting, disputed wall reconstruction, internal debt crisis, and forceful final reforms. The object was left unchanged after single-object validation passed with zero errors and warnings.

Batch 059 enriched Numbers. The revised summary uses the two censuses to make the generational transition clear, and six claim rationales explain how Kadesh redirects the story and how the closing instructions prepare a new generation for inheritance. The Deir Alla comparison now states what a shared name can show without treating the inscription as verification of Numbers' narrative. No new historical claims were added. Single-object and full-library validation passed with zero errors; the same 14 baseline warnings remain.

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

Obadiah was reviewed and left intact. Its summary, historical and regional context, literary sequence, and interpretive notes already explain the movement from Edom’s humiliation through the Jerusalem accusations and day of YHWH to Zion’s survivors and contested territorial conclusion. The 23 claim rationales preserve clear limits, including the undated historical setting, uncertain Edomite actions, contested grammar, and debated overlap with Jeremiah 49. The object validated with zero errors and warnings; no retrieval test was needed because no content changed.

Batch 074 enriched the Genesis 37–44 Joseph descent and testing record. Its summary and historical/literary framing now explain how Joseph’s rise, the family’s return, and Judah’s changed responsibility connect, while retaining the record’s explicit limits on historical identification and dating. Seventy-eight duplicated evidence relevance fields now explain each observation’s role in its scene. The observation text, sources, Scripture anchors, relationships, and uncertainty classifications remain unchanged. The object validated with zero errors or warnings; full CKL validation remains at 687 valid, zero errors, and the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 075 enriched the Genesis 45–50 Joseph reconciliation and conclusion record. Its overview and context now connect the migration, famine administration, tribal blessings, burial, and Joseph’s final oath while making clear that Egyptian comparisons do not identify the characters or date the events. Eighty-two duplicated evidence relevance fields now explain their scene-level significance, including textual totals and later reception. Source identities, evidence observations, anchors, and relationships remain intact. The object validated with zero errors or warnings; full CKL validation remains at 687 valid, zero errors, and the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 076 reviewed the Genesis 10–11 nations and Babel context. Its 29 evidence explanations already gave specific, source-aware accounts of the table of peoples, Babel’s language and building imagery, and disputed names and chronology, so those remained unchanged. The summary and context fields now describe the sequence in more accessible prose and explain what the Mesopotamian comparisons can and cannot establish. The object validated with zero errors or warnings; full CKL validation remains at 687 valid, zero errors, and the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 077 reviewed the honor-and-shame background object and left it unchanged. It has no passage-specific evidence items or claims, and its broad historical and cultural statements rely on an internal CKL orientation note rather than inspected scholarly support. Future research is needed before expanding claims about honor and shame across ancient societies and periods. The full CKL remains at 687 valid objects, zero errors, and 14 baseline warnings. The single-object path audit reports nine section-status warnings for this unchanged record; those do not appear in the full-library audit. No regression tests were run because no content changed.


Batch 078 reviewed the Judean pilgrimage, taxation, and Roman power record and left it unchanged. Its claims and evidence distinguish temple payments, tolls, imperial tribute, Roman jurisdiction, crucifixion, and burial, and carefully bound what the stepped street and Yehohanan remains can establish. The cited excavation report, Josephus passage, and museum object record were inspected. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. Regression tests were not run because no content changed.


Batch 079 reviewed the Judges household religion and regional cult sites record. Its four passage-level explanations already distinguished Micah’s household shrine, the Danite installation, Shiloh, and the Bull Site comparison with clear archaeological limits. The summary now explains the movement among those settings in plain language. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 080 reviewed the kinship, inheritance, and redemption record and left it unchanged. Its two claims and interpretive caution already make clear that Ruth 4 joins property, marriage, and family continuity in its own narrated transaction without equating it with one uniform law from Leviticus or Deuteronomy. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. Regression tests were not run because no content changed.


Batch 081 reviewed the Judges 1–2 and Iron I transition record. Its evidence already distinguished Judges’ varied local outcomes from archaeological settlement patterns and limited what the Merneptah Stele can show. The summary now explains these connections in reader-facing prose without assigning an ethnic identity to each village or using archaeology to verify the campaigns. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 082 reviewed the Genesis and Mesopotamian creation and flood comparison record. Its claims and evidence already distinguished shared motifs from direct borrowing and the date of surviving tablets from the age of a tradition. The summary now describes those comparisons in plain language without implying that Genesis copied a particular tablet. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 083 reviewed the patronage, hospitality, and debt record. Its claims, 20 evidence items, and safeguards were already detailed and passage-specific. The summary now explains how the biblical texts distinguish material support, hospitality, work, sharing with the poor, and collection accountability, without treating these as one system. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 084 reviewed the large Pauline authority and conflict record: all 70 claims, 70 evidence items, and four interpretive notes. Its passage-level explanations were already detailed and carefully qualified, so they remain unchanged. The summary now explains why the letters’ partial accounts and Acts’ later narratives must be kept distinct, and why forgiveness does not automatically restore trust, authority, or contact. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 085 reviewed the Pauline sexuality and restoration record. Its 23 claims and evidence explanations already distinguish ancient wording, disputed legal and rhetorical contexts, modern identity categories, consent, and safeguarding limits. The summary now makes that scope easier to grasp without flattening the passages into a single rule. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 086 reviewed the Pauline death, resurrection, and grief record: all 30 claims, 30 evidence explanations, and five interpretive notes. Its passage-level explanations already distinguish bodily resurrection, metaphorical death, grief, transformation, and disputed passages. The summary now gives readers a plain-language map of those questions while leaving unresolved matters open. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.


Batch 087 reviewed the Pauline authorities and civic life record: all 52 claims, 52 typed evidence items, and six interpretive notes. Their explanations already distinguish Romans’ ethical sequence, Corinthian disputes and metaphors, Philippi’s civic language, Thessalonian hope, and Acts’ later legal narratives. The summary now explains these connections in reader language while leaving disputed imperial resonance open. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 088 reviewed the Pauline food, conscience, and shared meals record: all 49 claims, 49 typed evidence items, and seven interpretive notes. Their explanations already distinguish temple participation, market purchase, private hospitality, assembly meals, and the Antioch conflict, while preserving Jewish practice diversity and uncertainty about disputed details. The summary now traces these settings in reader language. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 089 reviewed the Pauline Israel and Jewish-gentile relations record: all 40 claims, 40 typed evidence items, and six interpretive notes. Their explanations already preserve Israel’s scriptural gifts and hope, distinguish gentile inclusion from identity erasure, and qualify debates about Torah, election, hardening, and “all Israel.” The summary now gives readers a clearer map of the different arguments across Romans, Galatians, Corinthians, Philippians, and Acts. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 090 reviewed the Pauline kinship, guardianship, slavery, and inheritance record: all 19 claims, 19 typed evidence items, and six interpretive notes. The explanations already distinguish Galatians’ household-heir analogy from Romans 8’s movement through adoption, Spirit, co-heirship, suffering, and bodily hope, while limiting Roman legal comparisons. The summary now makes those differences clearer to readers. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 091 reviewed the Pauline mission and interassembly networks record: all 74 claims, 74 typed evidence items, and six interpretive notes. Their explanations already make coworkers, hosts, messengers, women’s labor, changing plans, support, correction, and local agency visible, while distinguishing the letters from Acts’ later narrative. The summary now gives readers a concise map of that network. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 092 reviewed the Pauline prayer, thanksgiving, lament, and communal memory record: all 58 claims, 54 typed evidence items, and four interpretive notes. Their explanations already hold prayer and hope together with grief, uncertainty, conflict, practical aid, consent, and safeguarding. The summary now describes these functions in plain language and identifies Acts as a later narrative. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 093 reviewed the Pauline Spirit, gifts, prophecy, healing, and assembly-order record: all 34 claims, 34 typed evidence items, and six interpretive notes. The explanations already distinguish diverse Spirit-related language and gifts, and connect them to common benefit, intelligibility, testing, and accountable care. The summary now makes that structure easier to follow without resolving later disputes about which gifts continue. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 094 reviewed the Pauline suffering, weakness, disability, healing, and apostolic legitimacy record: all 28 claims, 28 typed evidence items, and five interpretive notes. Their explanations already distinguish illness, injury, disability, persecution, poverty, imprisonment, rhetorical weakness, and cross-shaped power, and explicitly leave Paul’s thorn unidentified. The summary now gives readers that distinction in plain language. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 095 reviewed the Pauline women coworkers and assembly authority record: all 20 claims, 20 typed evidence items, and five interpretive notes. The explanations already distinguish named work, prophecy, hospitality, disputed silence instructions, Junia’s debated apostolic description, and later office systems. The summary now shows readers how Romans, Corinthians, Philippians, and Acts contribute without flattening their differences. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 096 reviewed the Pauline work, wages, poverty, giving, and economic solidarity record: all 50 claims, 50 typed evidence items, and six interpretive notes. Their explanations already distinguish support rights from voluntary nonuse, generosity from coercion, equality from enforced destitution, and unwillingness from inability to work. The summary now guides readers through those distinctions and identifies Acts as a later witness. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 097 reviewed the Persian restoration and Yehud administration record: all four claims, four typed evidence items, and three interpretive notes. The explanations already distinguish Ezra’s multi-reign account from the Cylinder’s Babylonian text, Yehud’s stamp evidence, and a later Elephantine petition. The summary now states what each source contributes without treating comparative evidence as direct confirmation. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 098 reviewed the ritual purity and communal holiness record: all 20 claims, 20 typed evidence items, and five interpretive notes. The explanations already distinguish Levitical impurity categories, Mark’s Jewish hand-purity dispute, Acts’ interpretation of Peter’s vision, and the separate Pauline food cases. The summary now explains those differences without turning comparative evidence into a universal menu. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 099 reviewed the Roman Athens and Areopagus record: all 12 claims, 16 typed evidence items, and four interpretive notes. The explanations already distinguish the Classical and Roman Agoras, an ambiguous Areopagus setting, layered cult practice, philosophical comparanda, and the limits of the unknown-god altar evidence. The summary now gives readers the scene’s progression without claiming an exact venue or artifact. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 100 reviewed the Roman citizenship and legal process record and left it unchanged. Its summary and two claims already distinguish Acts’ repeated citizenship portrayal from independent confirmation and limit what can be inferred about Roman procedure from the narrated scenes. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. Regression tests were not run because no content changed.

Batch 101 reviewed the Roman Corinth civic, household, and association record: all 10 claims, 10 typed evidence items, and three interpretive notes. Their explanations already connect ports, civic space, cult, households, status inequality, and meals to the letters while limiting what archaeology can establish. The summary now makes those connections easier to follow and preserves uncertainty about specific people and venues. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 102 reviewed the Roman Ephesus civic, cultic, and household record: all 12 claims, 12 typed evidence items, and three interpretive notes. The explanations already distinguish Acts’ Ephesian settings from archaeology, Revelation’s named assembly, the disputed destination of Ephesians, and First Timothy’s narrated setting. The summary now gives readers a concise map without turning local cult evidence into a universal explanation. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 103 reviewed the Roman Galatia regions, roads, cities, and audience record: all 19 claims, 19 typed evidence items, and five interpretive notes. The explanations already distinguish Roman provincial Galatia from older regional identities, document the southern city sequence and road network, and preserve uncertainty about which assemblies received Galatians. The summary now makes those distinctions easier to follow. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 104 reviewed the Roman Macedonia road network and city diversity record: all 11 claims, 11 typed evidence items, and two interpretive notes. Their explanations already distinguish the Via Egnatia trunk route from Beroea’s branches, the cities’ civic statuses, and Acts’ itinerary from the letters’ accounts. The summary now puts those points in a clear sequence. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 105 reviewed Roman Philippi: all 12 claims, 12 typed evidence items, nine interpretive notes, contextual fields, anchors, and source identities. The summary now connects Acts’ travel, household welcome, exploitation, and civic conflict to Philippi’s Roman-colony setting, while distinguishing the archaeological setting from verification of narrated events and preserving uncertainty about the traditional prison site and letter provenance. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

The next work unit is `framework/canonical_library/objects/cultural_background/roman-rome-jewish-civic-household-and-imperial-life.json`.
Batch 106 reviewed Roman Rome: all 16 claims, 17 typed evidence items, three interpretive notes, contextual fields, anchors, and source identities. The summary now distinguishes Romans’ greetings and Acts’ guarded lodging from the city evidence and later traditions, keeping Claudius’s action, the audience, and meeting sites qualified. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 107 reviewed the Second Temple priesthood and temple authority record: all four claims, four typed evidence items, three interpretive notes, contextual fields, anchors, and source identities. Its summary now explains how priestly authority, imperial appointment power, the temple boundary relevant to Acts 21, and a proposed Caiaphas identification relate, while preserving uncertainty. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 108 reviewed the Second Temple synagogues, scribes, and sectarian groups record: all five claims, five typed evidence items, three interpretive notes, contextual fields, anchors, and source identities. The summary now distinguishes the different contributions of Luke-Acts, the Theodotus inscription, Ben Sira, Josephus, and 4QMMT, without treating one synagogue pattern or sect label as universal. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 109 reviewed the synagogue-life and exclusion record: both claims, its interpretive note, contextual fields, anchors, sources, and the absence of typed evidence. The summary now clarifies synagogue settings in Luke-Acts and the limits of John’s exclusion language without proposing a universal decree or rupture. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 110 reviewed the tabernacle presence, access, and mobility record: all four claims, four typed evidence items, two interpretive notes, contextual fields, anchors, and source identities. Its summary now connects the tabernacle’s stated purpose, ordered access, construction sequence, and the cloud’s guidance in Exodus and Numbers. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 111 reviewed the Thessalonian civic and funerary context record: all 15 claims, 16 typed evidence items, two interpretive notes, contextual fields, anchors, and source identities. The summary now connects the city’s route and free-city setting to the community described in Acts and the letters, while distinguishing later burial evidence and retaining disputed political readings as proposals. Only the summary changed. The object and full CKL validated with zero errors; the library retains the same 14 baseline warnings. The focused cultural-context and retrieval regression passed 17 tests with 4 subtests.

Batch 112 reviewed the creation-doctrine framework’s summary, canonical contexts, Scripture references, source identities, two interpretive notes, and its absence of atomic claims and typed evidence. The summary now traces creation from Genesis and the Psalms through the New Testament’s Christological language to Revelation’s renewal, without adding unsupported historical comparisons. Only the summary changed. The object had nine pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 113 reviewed the Abrahamic covenant record’s summary, contexts, four biblical source entries, two interpretive notes, and its absence of atomic claims or typed evidence. The summary now distinguishes Genesis 15’s ceremony from Genesis 17’s sign and notes the later, distinct arguments in Romans and Galatians. It adds no new historical comparison. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 114 reviewed the annunciation-to-Mary record’s summary, contexts, biblical source entries, one interpretive note, and its absence of atomic claims or typed evidence. The summary now connects Gabriel’s Davidic announcement, Mary’s response, the Spirit’s role, and the promise to David while keeping later devotional traditions distinct. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 115 reviewed and corrected the Ark Brought to Jerusalem event record, whose summary and contextual fields had mistakenly described land-taking and generic cross-book themes. The revised prose follows 2 Samuel 6 and distinguishes the procession from the promise in 2 Samuel 7. The object’s broad Joshua, Judges, and 1 Samuel anchors and curated edges were preserved; their relevance needs separate review. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 116 reviewed and corrected the Ascension record’s Gospel framing. The summary now distinguishes Luke’s departure scene, Matthew’s commission, John’s resurrection appearances, and Mark’s ascension in the longer ending, whose textual history remains qualified. Acts 1 is missing from the object’s preserved anchors and remains a research follow-up. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 117 reviewed the Assyrian exile record and left its explanation unchanged. The historical context names Sargon II’s inscriptions and a deportation chronology, but the recorded sources are biblical texts only; those historical details need source-specific research before further enrichment. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. Regression tests were not run because content did not change.

Batch 118 reviewed the Babel event record and left it unchanged. Its summary identifies the builders’ aims, and its context separates narrative setting from composition history while treating ziggurats as a bounded analogy rather than a specific monument. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. Regression tests were not run because content did not change.

Batch 119 reviewed the Babylonian exile record and left it unchanged. Its explanation already distinguishes the 597 BCE deportation, Jerusalem’s destruction in 587/586 BCE, continued life in Judah and Babylonia, and the limits of the surviving evidence. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. Regression tests were not run because content did not change.

Batch 120 reviewed the Baptism of Jesus object and held it unchanged. Its anchors point to Gospel endings and appearances rather than baptism narratives, so the object needs source and identity reconciliation before a passage-specific explanation can be written. It had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. Regression tests were not run because content did not change.

Batch 121 reviewed the Binding of Isaac record’s contexts, anchors, sources, and interpretive notes. Its summary now explains the command concerning Isaac, the interruption, the ram offered in his place, and the reaffirmed promise; Hebrews 11 is identified as a later reading. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 122 reviewed the birth-of-Isaac record’s contexts, references, sources, and interpretive note. Its summary now connects Sarah’s laughter at the promise in Genesis 18 with Isaac’s birth in Genesis 21, while distinguishing the later readings in Romans and Hebrews. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 123 reviewed the birth-of-Jesus record’s contexts, references, sources, and interpretive notes. Its summary now distinguishes Matthew’s and Luke’s birth narratives, their shared relation to Davidic hope, and the different purposes of later Pauline references. Historical questions about census chronology remain unresolved rather than being harmonized. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 124 reviewed the burial-of-Jesus record and left it unchanged. Its summary explains the burial’s place between death and the empty-tomb accounts; context distinguishes Sabbath timing and regional tomb evidence from identifying Jesus’ tomb. No archaeology publication is recorded, so no further archaeological explanation was added. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. Regression tests were not run because content did not change.

Batch 125 corrected the Burning Bush event record, whose summary described the whole Exodus and whose other contexts were generic placeholders. The revised fields explain Moses’ encounter and commission in Exodus 3 and distinguish that scene from the later Sinai covenant. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 126 reviewed the Call of Abraham record’s contexts, references, sources, and interpretive notes. Its summary now traces Genesis 12’s departure and promises through the blessing for the nations, then distinguishes later arguments in Romans, Galatians, and Hebrews. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 127 reviewed the Calling of the Twelve record’s contexts, passages, sources, and interpretive note. Its summary now explains the significance of the number twelve, distinguishes the group from Jesus’ wider circle of disciples, compares the Gospel accounts, and treats Matthias’s later selection in Acts as a separate event. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 128 corrected the Conquest of Jericho event record, whose summary and context fields had described a generic land-taking event. The revised prose follows Joshua’s sequence, including Rahab’s rescue, and distinguishes the narrative from archaeological questions. The existing passage anchors omit Joshua 2 and 6; they remain unchanged for research review. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 129 corrected generic context in the Conversion of Paul record. The revised account explains Saul’s reversal, Ananias’s role, Acts’ later retellings, and why conversion, call, and commissioning are overlapping descriptions. Acts 15 and Ephesians 2 remain later discussions of gentile inclusion. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 130 reviewed the Cornelius household record’s contexts, anchors, sources, and interpretive note. The summary now follows the sequence from the paired visions through the Spirit’s arrival before baptism, then the retelling in Acts 11 and later discussion in Acts 15. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 131 corrected generic church-event prose in the Council of Jerusalem record. The revised account follows Acts 15’s dispute, testimonies, scriptural argument, and decision for Gentile believers. Its existing Acts 9 anchor is unrelated to the council and remains unchanged for review. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 132 reviewed the covenant-renewal-at-Shechem record’s contexts, anchors, sources, and interpretive note. Its summary now traces Joshua’s recital of God’s acts through Israel’s response, the warning about covenant responsibility, and the stone witness, linking Shechem to its wider narrative setting. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 133 reviewed the Creation event record’s summary, contexts, references, sources, and interpretive notes. The summary now explains Genesis 1’s sequence of separations, the goodness refrain, human vocation, and seventh-day rest, keeping the chapter’s literary design central. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 134 reviewed the Crossing the Jordan record’s contexts, references, sources, and interpretive note. Its summary now explains how the ark-led crossing and memorial stones connect the event with communal memory, and distinguishes Psalm 114’s later poetic echo from the Joshua narrative. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 135 reviewed the Crucifixion event record’s contexts, references, sources, and interpretive notes. The summary now explains “atoning” in accessible language while preserving the different New Testament images used to interpret the cross. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 136 reviewed the David and Goliath record and left it unchanged. Its summary explains the scene’s military and rhetorical contrasts; the claims and evidence connect weapon materials to a Gath workshop with explicit limits on what archaeology can establish. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. Regression tests were not run because content did not change.

Batch 137 corrected generic event language in the David Anointed record. The revised prose follows 1 Samuel 16’s selection of David, the anointing and Spirit, and the fact that Saul still reigns. The object’s existing anchors omit 1 Samuel 16 and include unrelated passages; they remain preserved for review. The object had eight pre-existing section-status warnings; the full CKL retained the same 14 baseline warnings and no errors. The focused regression passed 17 tests with 4 subtests.

Batch 138 enriched the Davidic covenant record. Its explanation now follows the chapter’s house-and-dynasty wordplay, distinguishes the temple-building descendant from the enduring royal promise, and traces later hope alongside Psalm 89’s crisis. A generalized ancient Near Eastern comparison was removed because the recorded sources do not support it. All source identities, Scripture anchors, and relationships remain unchanged; structural validation passed with the same 14 baseline warnings, and the focused regression passed 17 tests with 4 subtests.

Batch 139 enriched the Solomon temple dedication record. The explanation now follows the ark-and-cloud scene into Solomon’s prayer: the temple is a focus for prayer but does not contain God, and the prayer anticipates exile, repentance, return, and even foreign worshippers. No unsupported comparison with neighboring royal dedication rites was retained. Protected metadata and relationships remain intact; the full CKL validator reported the same 14 baseline warnings, and the focused regression passed 17 tests with 4 subtests.

Batch 140 enriched the division of the kingdom record with the Shechem succession crisis, Rehoboam’s decision, the northern break, and Jeroboam’s worship centers. It distinguishes the narrative’s political events from its theological interpretation and leaves the ancient Near Eastern field blank because no comparative source is recorded. The full CKL again validated with zero errors and the same 14 baseline warnings; focused regression passed 17 tests with 4 subtests.

Batch 141 corrected the Elijah on Mount Carmel event record, replacing unrelated exile-and-restoration template text with the 1 Kings 18 confrontation and its role in the Elijah narrative. The generic ancient Near Eastern placeholder was cleared for lack of comparative sourcing. Existing anchors and relationships remain untouched, though they do not point to Carmel and need research review. Structural validation retained the same 14 baseline warnings; focused regression passed 17 tests with 4 subtests.

Batch 142 reviewed Fall of Babylon and skipped enrichment pending source and scope research. Its anchors cover Assyrian exile, a Babylon oracle, and restoration material but do not directly narrate Babylon’s capture; no independent historical source is recorded. The unchanged library validates with zero errors and the same 14 baseline warnings.

Batch 143 reviewed Fall of Jerusalem and left it unchanged. Its history distinguishes the 597 BCE capture from the later destruction, qualifies the 587/586 BCE date, and explicitly limits what the Babylonian Chronicle establishes. The object and library validated with no errors and the same 14 baseline warnings.

Batch 144 reviewed Fall of Samaria and left it unchanged. Its historical section qualifies the Shalmaneser V/Sargon II chronology; its ANE section separates Assyrian royal claims from administrative evidence; and its covenantal and canonical fields distinguish the fall of Israel from Judah’s later exile. The library retains zero errors and the same 14 baseline warnings.

Batch 145 corrected the Feeding of the Five Thousand record, explaining the shared scene and the differences in Gospel placement, including John’s sign and bread-of-life discourse. It removed a generic unsupported ANE placeholder. Its anchors point to Gospel endings rather than the feeding scenes, a research follow-up preserved in the manifest. The full library retains zero errors and the same 14 baseline warnings; regression passed 17 tests with 4 subtests.

Batch 146 corrected the First Missionary Journey event record, grounding the explanation in Acts 13–14 and distinguishing that journey from the later Acts 15 discussion. Its current Scripture anchors point elsewhere and remain flagged for review; the generic ANE placeholder was cleared. Structural validation kept zero errors and the same 14 baseline warnings; regression passed 17 tests with 4 subtests.

Batch 147 enriched Giving of the Law. The prose now connects the commandments to the exodus narrative and communal life, compares Exodus and Deuteronomy’s Sabbath rationales, and situates Matthew 5 as later interpretation. The uncited generic comparison with ancient law collections and treaties was removed. Structural validation retained zero errors and the same 14 baseline warnings; focused regression passed 17 tests with 4 subtests.

Batch 148 reviewed Golden Calf and skipped enrichment pending direct source verification. Its Scripture anchors and listed source ranges omit Exodus 32–34, where the event is narrated. The unchanged object validates with zero errors and its 8 pre-existing section-status warnings; full CKL validation retains the same 14 baseline warnings.

Batch 149 enriched Great White Throne Judgment with the scene’s opened books, universal judgment, defeat of death, and literary connection to Daniel 7. It preserves uncertainty about apocalyptic chronology and adds no unsourced ancient Near Eastern comparison. The full CKL retains zero errors and the same 14 baseline warnings; focused regression passed 17 tests with 4 subtests.

Batch 150 reviewed Hannah’s Prayer and skipped enrichment pending source review. Its anchors and sources concern Gospel resurrection appearances, and it contains no direct material from 1 Samuel 2. No CKL content changed; the object and full library retain zero errors and the same 14 baseline warnings.

The next work unit is `framework/canonical_library/objects/events/hezekiahs-reforms.json`.
Record field paths, actual outcomes, validation evidence, and checkpoint commit
IDs in `progress.json`.
