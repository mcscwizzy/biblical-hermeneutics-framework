# ED-2 Release Readiness Review

**Outcome: READY WITH REVIEW CONDITIONS**

Review date: 2026-11-10.

The branch passes the technical and reader checks below against `origin/master` at `04eed56ece941f9efce2f7f05b3908baf0197648`. The 99 additions remain drafts. They must not be presented as human-approved research or promoted to accepted status until an independent scholarly review is recorded. This is a content-review condition, not a failing technical gate.

## Readiness matrix

| Area | Result | Evidence and remaining action |
|---|---|---|
| Python/API/integration/release validation | Pass | Supported Python 3.12.3 environment installed from documented `.[dev,gui]` setup; focused batch 697 tests and 109 subtests passed; Validate-workflow release set 50 passed. |
| CKL, manifest, source integrity, chapter census | Pass with inherited findings | 687 CKL objects; strict validation 0 errors and 14 inherited incomplete-section warnings; generated manifest is semantically equal. Final ED-1A census maps all 1,189 chapters. Two inherited child source references and heuristic warnings remain; details below. |
| Narrative Explorer desktop/mobile review | Pass | Five new records, one per wave, checked at desktop and narrow mobile width (500 CSS px, Firefox's minimum effective viewport in this environment). Exact scope, source locator, uncertainty, draft notice, full review state, single display, and overflow were checked. |
| Source-access audit | Pass with review priorities | All 99 records were reconciled with their research packets and source register. 72 full-text-only, 3 mixed full-text/abstract, 3 excerpt-only, 21 abstract-only, 0 unusable-source-only. Eight records rely on secondary reporting for artifact or witness details and need direct-source review where feasible. |
| Draft/human-review governance | Pass after a narrow reader fix | Preview cards now label draft items as awaiting human review before provenance is expanded. The existing detail disclosure remains. Regression test and browser checks pass. All 99 still require human review; none has an approval recorded. |
| NE-9C/NE-10 and protected evidence | Pass | No protected curation, bridge, checkpoint, source-lock, or accepted CKL evidence changed. Counts remain 433 accepted, 44 verified, 7 held; no held decision was promoted. |
| Scholarly readiness | Review required | Prioritize textual-critical, disputed-language, artifact-comparison, dating, and access-limited items listed below. Keep items in draft/in-review pending scholarly approval. |

## Environment and verification

The documented setup is a project virtual environment with `python -m pip install -e ".[dev,gui]"`. The repository declares compatible dependency ranges rather than a fully pinned lock file. This review used Python 3.12.3, FastAPI 0.115.14, httpx 0.27.2, pytest 9.1.1, Selenium 4.46.0, and uvicorn 0.34.3. The initial isolated build could not reach the package index for build-isolation dependencies; installation succeeded using the environment's cached setuptools with `--no-build-isolation`. No dependency constraint was changed.

- Focused API, Narrative Explorer, CKL integration, and release batch: **697 passed; 109 subtests passed** (430.64 seconds).
- Validate-workflow release-focused Python set: **50 passed** (106.24 seconds).
- `python tools/validate.py framework/`: **94 modules valid**.
- Full frontend Node suite: **17 files passed, 0 failed**; the new draft-preview regression is included.
- `python -m build --no-isolation`: wheel and sdist built; installed-wheel smoke check loaded the default CKL (**687 objects**) and passed CLI/application imports. Existing setuptools license deprecation and absent optional commentary SQLite glob warnings were emitted; packaging gates passed (1,052 wheel entries; 1,242 sdist entries).
- Artifact-content gate passed; the retired generated-commentary payload was absent.
- The full ED-1A census passed: 1,189/1,189 chapters, 0 unmapped identities, 19 deterministic samples, and 16 targeted service builds.
- `git diff --check` and profile-generation cleanliness checks passed. No profile output changed.

The main history's earlier note that FastAPI tests were uncollectable described the original incomplete environment. The tests have now been collected and passed in the supported environment above. The historical wave-by-wave entries remain as contemporaneous run notes.

## Reader acceptance and governance fix

Headless Firefox exercised one new evidence record from each wave at desktop and a narrow mobile-width viewport: Psalm 61:4–7, Ecclesiastes 10:1, 2 Chronicles 18:1–34, Nahum 3:8–9, and Mark 7:3. Each case checked the selected passage and exact evidence relationship, one rendered card, source identity and locator, primary observation, attributed interpretation, confidence/dispute disclosure, and review state. The preview showed `Draft evidence — awaiting human review.` before expanding provenance. Expanded details showed `review state: in_review`, `content state: draft`, `human review required: yes`, and `human scholarly approval: not recorded in CKL`. No horizontal overflow was observed. Firefox reported a 500 CSS-pixel effective width when configured for 390 pixels; the narrow-width cases used that measured value and the mobile responsive layout.

The first browser inspection demonstrated that a collapsed preview could show scholarly content without a visible draft notice. The smallest correction adds the existing governance wording to draft/review-required preview cards. It does not change projections, CKL records, review states, or published-item behavior. The Node regression asserts both draft disclosure and no extra notice on a published item. The follow-up browser cases confirmed the notice in the reader.

## Source-access audit of the 99 additions

Classification is per evidence record, based on the research packets and cited scholarly material actually consulted. “Full text” means the relevant source text and cited locator were available; it does not mean that an underlying archaeological artifact, papyrus, or manuscript image was independently examined. Access classes are mutually exclusive and total 99.

| Access class | Records | Assessment |
|---|---:|---|
| Relevant full text only | 72 | The cited scholarly discussion was inspected at the recorded locator; interpretations remain attributed to the author. |
| Mixed: full text plus an abstract-only source | 3 | A full source supports the item, while a second cited source contributes only abstract-level context. |
| Excerpt only | 3 | A useful publisher/book excerpt was available; the complete cited chapter or work was not. |
| Abstract only | 21 | Claims are restricted to the accessible abstract/metadata, use attributed language and low confidence where indicated, and remain open to full-text review. |
| No usable source text (inaccessible-only) | 0 | No addition relies solely on a source for which no relevant text, abstract, excerpt, or usable report was available. |

**Mixed full-text/abstract records:** `psalm-20-amherst63-parallel-and-direction-debate`, `psalm-7-cush-superscription-and-setting-limits`, `psalm-143-in-galatians-argument-debate`.

**Excerpt-only records:** `psalm-80-vine-lament-and-son-ambiguity`, `psalm-34-instruction-and-wisdom-rhetoric`, `psalm-144-reworked-royal-victory-song`.

**Abstract-only records:** `2chronicles-25-amaziah-and-kings-parallel`; `john-10-22-dedication-term-and-winter`; `mark-7-3-pugme-pukna-variant`; `proverbs-28-rulers-and-poor-structure`; `psalm-75-proposed-wordplay-in-judgment-poem`; `psalm-17-textual-proposals-verses-11-and-14`; `psalm-21-request-language-diplomatic-proposal`; `psalm-49-wisdom-poem-and-chiastic-focus`; `psalm-105-history-recounted-as-liturgy`; `psalm-61-royal-voice-proposal`; `psalm-63-royal-voice-proposal`; `psalm-70-concentric-structure-proposal`; `psalm-98-yhwh-kingship-in-book-four-cluster`; `psalm-109-speaker-and-reported-speech-debate`; `psalm-58-opening-word-and-versional-readings`; `psalm-141-suffixes-and-fabrications`; `psalm-4-dialogue-and-stanza-delimitation`; `psalm-18-distinctive-opening-and-samuel-parallel`; `psalm-23-host-hospitality-and-return-reading`; `psalm-40-reception-in-4q160`; `psalm-73-ring-composition-proposal`.

**Relevant full-text-only record IDs (72):**

`first-chronicles-16-36-five-book-psalter`; `2chronicles-14-cushites-and-rhetorical-setting`; `2chronicles-18-jehoshaphat-and-micaiah`; `acts-15-29-eu-prassete-range`; `ecclesiastes-10-1-flies-of-death-translation`; `ezekiel-22-prophets-princes-textual-reading`; `ezekiel-31-pharaoh-cedar-and-sheol`; `isaiah10-5-8-assyrian-agency-and-polemical-contrast`; `luke-13-10-17-sabbath-healing-necessity`; `luke-5-30-grumbling-and-wilderness-language`; `luke-8-1-3-women-scope`; `nahum-3-8-9-one-city-text-critical-proposal`; `proverbs-15-25-to-16-9-mt-lxx-redaction-debate`; `proverbs-2-conditional-argument-structure`; `proverbs-6-surety-and-stranger`; `psalm-100-worship-and-the-psalter-sequence`; `psalm-101-royal-voice-and-community-justice`; `psalm-102-created-or-set-apart-people`; `psalm-108-head-imagery-and-royal-victory-metaphor`; `psalm-11-refuge-and-spatial-argument`; `psalm-110-order-of-melchizedek-debate`; `psalm-111-acrostic-praise-and-scribal-learning`; `psalm-12-speech-poor-and-wisdom-polarity`; `psalm-135-exodus-motifs-and-servants`; `psalm-138-praise-in-final-davidic-psalter`; `psalm-139-imprecation-and-ambiguity-in-prayer`; `psalm-14-psalm53-revision-debate`; `psalm-140-selah-and-petition-structure`; `psalm-142-cave-superscription-and-historical-limits`; `psalm-16-wisdom-contentment-and-psalter-context`; `psalm-25-individual-prayer-and-collective-epilogue`; `psalm-26-walking-integrity-and-wisdom-structure`; `psalm-27-bqr-temple-reflection-reading`; `psalm-28-lament-praise-and-final-petition`; `psalm-29-ugaritic-comparison-method`; `psalm-31-hand-imagery-and-cluster-exhortation`; `psalm-32-two-stanza-wisdom-structure`; `psalm-33-sea-and-deep-imagery`; `psalm-35-battlefield-and-courtroom-movement`; `psalm-38-embodied-distress-and-prayer-for-wholeness`; `psalm-39-wisdom-reflection-and-delayed-retribution`; `psalm-43-refrain-and-stanza-structure`; `psalm-45-sound-and-performance-of-royal-poem`; `psalm-46-chaos-waters-and-stream-imagery`; `psalm-48-zion-security-and-remembered-space`; `psalm-5-morning-motif-and-setting-limits`; `psalm-52-wealth-critique-and-wisdom-intertexts`; `psalm-53-adaptation-and-cluster-context`; `psalm-55-betrayal-and-historical-setting-limits`; `psalm-56-superscription-and-editorial-frame`; `psalm-57-reuse-in-psalm108-reframes-praise`; `psalm-59-evening-threat-and-morning-confidence`; `psalm-60-communal-defeat-and-book-context`; `psalm-62-community-address-and-wealth-warning`; `psalm-64-attack-to-vindication-narrative-movement`; `psalm-65-zion-to-earth-praise-sequence`; `psalm-66-collective-and-individual-praise`; `psalm-69-restoration-stanza-and-servants`; `psalm-71-old-age-and-generational-witness`; `psalm-76-zion-hymn-and-unspecified-battle`; `psalm-77-lament-memory-and-exodus-reframing`; `psalm-78-introduction-and-historical-didactic-recitations`; `psalm-81-hinge-lines-and-colometry-proposal`; `psalm-83-coalition-imagery-and-setting-limits`; `psalm-86-korah-collection-lament-frame`; `psalm-87-zion-status-reading-dispute`; `psalm-91-wisdom-language-and-protection-instruction`; `psalm-92-creation-order-and-sabbath-song`; `psalm-94-weekday-song-and-poetic-sequence`; `psalm-97-kingship-and-book-four-narrative`; `psalm-99-zion-and-kingship-sequence`; `revelation-13-land-beast-as-asian-elite-network`.

### Secondary-report-only issues

The following items report a secondary scholar's discussion of artifact, witness, or versional evidence without independently inspecting the underlying object/facsimile or full apparatus. This classification overlaps the access table; the scholarly article itself may have been read in full.

- `mark-7-3-pugme-pukna-variant`: abstract and displayed apparatus note only; manuscript images and full witness discussion were unavailable.
- `psalm-17-textual-proposals-verses-11-and-14`: abstract reports the conjecture and *qere* preference; the full comparison of manuscripts and versions was not reviewed.
- `psalm-20-amherst63-parallel-and-direction-debate`: Ward's dissertation and transcription were inspected; Papyrus Amherst 63 itself was not independently inspected, and Kister was available only as an abstract.
- `psalm-61-royal-voice-proposal` and `psalm-63-royal-voice-proposal`: LeMon's abstract reports the bulla argument; article reasoning, object, and archaeological context were not inspected.
- `proverbs-15-25-to-16-9-mt-lxx-redaction-debate`: Macchi's article reports the fragmentary 4QProvb evidence; the original fragment was not independently examined.
- `nahum-3-8-9-one-city-text-critical-proposal`: Grütter's full article reports the 4Q385a and Greek-version evidence; the manuscript artifact itself was not inspected.
- `revelation-13-land-beast-as-asian-elite-network`: Friesen's full chapter synthesizes inscriptions; the cited inscription corpus was not independently surveyed for this review.

The assertions in these records are framed as reported proposals and do not claim independent artifact verification. Independent review should confirm the relevant apparatus, edition, or primary-source publication before preferring a reading or historical reconstruction.

## Independent scholarly review priorities

All 99 additions require human scholarly review before acceptance. Prioritize review in this order; the lists are risk-based, not a claim that unlisted records need no review.

1. **Textual criticism and disputed language:** `mark-7-3-pugme-pukna-variant`; `psalm-17-textual-proposals-verses-11-and-14`; `psalm-58-opening-word-and-versional-readings`; `psalm-141-suffixes-and-fabrications`; `nahum-3-8-9-one-city-text-critical-proposal`; `ezekiel-22-prophets-princes-textual-reading`; `proverbs-15-25-to-16-9-mt-lxx-redaction-debate`; `ecclesiastes-10-1-flies-of-death-translation`; `psalm-20-amherst63-parallel-and-direction-debate`. Check the actual text editions and witness data; abstract-only proposals remain provisional.
2. **Artifact, inscription, and archaeological comparisons:** Psalm 61 and 63 bulla proposals; `revelation-13-land-beast-as-asian-elite-network`; `psalm-20-amherst63-parallel-and-direction-debate`; `nahum-3-8-9-one-city-text-critical-proposal`; `proverbs-15-25-to-16-9-mt-lxx-redaction-debate`; `mark-7-3-pugme-pukna-variant`. Verify primary editions/artifact data where possible and retain service ownership of archaeological catalog metadata.
3. **Source-access-limited interpretations:** review all 21 abstract-only and 3 excerpt-only records listed above, beginning with Psalm 61/63, Psalm 17/58/141, Psalm 75, Proverbs 28, 2 Chronicles 25, Mark 7, and John 10:22. Obtain full text before widening the claim; do not infer an article's detailed reasoning from its abstract.
4. **Dating and historical reconstruction:** check the attributed setting/composition proposals in `psalm-7-cush-superscription-and-setting-limits`, `psalm-105-history-recounted-as-liturgy`, `2chronicles-14-cushites-and-rhetorical-setting`, and `isaiah10-5-8-assyrian-agency-and-polemical-contrast`. The records preserve uncertainty; reviewers should verify chronology independently and distinguish the event narrated, literary setting, proposed composition horizon, and later reception.

## Final census, provenance, and protected state

| Metric | Final result |
|---|---:|
| CKL objects / claims / typed evidence items | 687 / 2,329 / 1,408 |
| Source occurrences / unique source identities / external source occurrences | 5,348 / 2,897 / 2,340 |
| Passage-specific / contextual-only / entity-only / no-eligible / incomplete-unknown chapters | 1,089 / 56 / 2 / 41 / 1 (of 1,189) |
| New evidence records | 99 unique IDs; all exact references and source links passed strict validation |
| New records by type | 84 literary-convention; 5 ancient-text; 4 cultural-practice; 3 manuscript; 1 worldview-concept; 1 historical-event; 1 institution |
| New-record review state | 99 draft; 99 `in_review`; 99 require human review; 0 human approvals recorded |

Strict CKL validation has 0 errors and 14 inherited `incomplete_section_status` warnings. The separate heuristic report has 63 error-severity findings and 1,093 warnings; it added no new heuristic errors. Those are heuristic signals, not strict CKL failures. Existing inherited provenance signals include two unresolved child source references (`harland-associations`, `glancy-slavery`), one inherited expected missing locator (`patristic-minor-prophets`), 102 source-support-target heuristic findings, and 16 weak-bibliography notices. No new record has a missing locator or confidence rationale. There are 558 source IDs without full title/bibliography detail, mostly Scripture/reference identities; no new evidence source identity is being represented as fully bibliographic when it is not.

Exact item identity was checked by comparing the 99 branch additions with their CKL records and research packets. The source register contained three documentation-only spelling mismatches, corrected to match the canonical CKL source IDs: `jonker-cushites-chronicles-2023`, `dillard-chronicles-jehoshaphat-1986`, and `hwang-amaziah-kings-chronicles-2025`. The independently counted total is 2,897 unique source IDs; previous ledger mentions of 2,898 were corrected. No CKL source identity or evidence record was changed for these corrections.

NE-9C/NE-10 files and historical checkpoints are unchanged. Compatibility checks passed without regenerating checkpoints. The 7 held bridge candidates remain held, including the Ezekiel 40–48 / Revelation 21–22 temple candidate. Existing accepted CKL objects and source locks were not rewritten.

## Release conditions and remaining actions

- Preserve the 99 records as draft/in-review with the visible reader notice until a qualified human reviewer assesses and records approval under the existing governance process.
- Give first review to disputed text readings, artifact/version comparisons, dating claims, and abstract/excerpt-only work listed above. Full locators and summaries are in [sources.md](sources.md), [deferred-research.md](deferred-research.md), and the per-wave research packets.
- Revisit inherited unresolved child-source references and sparse inherited source metadata through normal source-integrity maintenance; these are not new ED-2 defects and do not invalidate strict CKL validation.
- No new evidence, scholarly assertion, accepted decision, API contract, or reader architecture change was made in this readiness pass. The only runtime change is the pending-review label on draft evidence previews.
