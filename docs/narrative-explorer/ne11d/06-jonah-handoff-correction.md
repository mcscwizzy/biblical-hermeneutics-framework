# NE-11D1 Jonah source-side handoff correction

## Result

The NE-11D1 source-side handoff is implemented and the requested real-data API, browser, regression, CKL, and packaging checks pass. The correction branch is based on `origin/master` at `817e80369e3bee41bf2fbfc022dd65e991a15d03`. Required report commit `e2f996088ec129011041c62871fe2ea2537a4a10` is an ancestor of that baseline. Work is on `fix/ne11d1-jonah-discovery-handoff`; this change is not merged or deployed.

The baseline review included all five NE-11D acceptance reports (01–05) and NE-11B's Jonah review. No CKL object, source lock, NE-9C curation, NE-10 bridge, or held-candidate input was edited.

## Root cause and diagnostic trace

The defect occurs at card allocation. It is not passage eligibility, candidate ranking, semantic exclusion, identity serialization, or the verified route projection.

The actual CKL-backed `CompanionContextService` request for Jonah 1:17 builds an EvidenceBundle with 23 items. Its structured Jonah claims include:

| CKL identity | Role | Anchor |
|---|---|---|
| `jonah#claim:jonah-date-composition` | historical context | Jonah 1:1–4:11 |
| `jonah#claim:jonah-double-structure` | language/literary | Jonah 1:1–4:11 |
| `jonah#claim:jonah-genre` | language/literary | Jonah 1:1–4:11 |
| `jonah#claim:jonah-great-fish` | historical context | Jonah 1:17 |
| `jonah#claim:jonah-multireligious-reception` | dig deeper | Jonah 1:1–4:11 |
| `jonah#claim:jonah-numbering` | language/literary | Jonah 1:17 |
| `jonah#claim:jonah-prayer-composition` | language/literary | Jonah 1:17 |
| `jonah#claim:jonah-textual-witnesses` | language/literary | Jonah 1:1–4:11 |
| `jonah#claim:jonah-three-days` | dig deeper | Jonah 1:17 |
| `jonah#claim:jonah-twelve-placement` | language/literary | Jonah 1:1–4:11 |
| `jonah#claim:jonah-yom-kippur-reception` | dig deeper | Jonah 1:1–4:11 |

The remaining 12 bundle items are CKL interpretive notes. Their internal parent is `jonah`, but the presentation identity serializer only emits verified identities for structured `claim` and `evidence` records; interpretive notes have no card-level `ckl_record_identity` and cannot authorize a handoff. There are no other non-CKL items in this 23-item bundle.

The deterministic ranking uses the existing eight-item candidate limit and 0.36 minimum score. The target is inside that shortlist at rank 4, with a score of 0.645. Its evidence item retains `DIRECT_CONTEXT` metadata and a verse-level Jonah 1:17 anchor. Ranking adds comparative-context and dig-deeper penalties; neither penalty removes it. The refined presentation relationship is `COMPARATIVE_CONTEXT`, which is allowed as supporting evidence by the narrow card-support check.

| Rank | Evidence | Score | Allocation before correction |
|---:|---|---:|---|
| 1 | `jonah#claim:jonah-great-fish` | 0.765 | visible card 1 |
| 2 | `jonah#claim:jonah-numbering` | 0.765 | visible card 2 |
| 3 | `jonah#claim:jonah-prayer-composition` | 0.730 | visible card 3 |
| 4 | `jonah#claim:jonah-three-days` | 0.645 | excluded after the three-card allocation |
| 5 | Jonah interpretive note 11 | 0.645 | outside the three-card allocation |
| 6 | Jonah interpretive note 15 | 0.645 | outside the three-card allocation |
| 7 | Jonah interpretive note 16 | 0.645 | outside the three-card allocation |
| 8 | Jonah interpretive note 14 | 0.610 | outside the three-card allocation |

The target's exact ranking reasons are: direct passage relationship; verse Scripture anchor; high confidence; comparative context penalty; exact passage overlap; deeper comparative context penalty; source provenance available; and distinctive evidence. It remains above threshold and is not rejected by semantic classification. The deterministic allocator selects ranks 1–3 and then reaches the existing three-card maximum, so rank 4 is omitted.

All 23 bundle items score above the 0.36 threshold in this reproduction. The eight-item ranking limit truncates ranks 9–23; ranks 9–15 are the remaining structured claims (scores 0.535–0.495), and ranks 16–23 are interpretive notes (scores 0.415–0.375). The target survives that candidate limit and is lost only when the three-card packet is allocated.

Before and after, the visible card IDs and order remain:

1. `did-you-know-jonah-great-fish`
2. `did-you-know-jonah-numbering`
3. `did-you-know-jonah-prayer-composition`

Before the correction, the fish card cited `jonah-great-fish`. Afterward it cites `jonah-great-fish` and `jonah-three-days`; the other two cards and their evidence IDs are unchanged. Ranking positions and scores are unchanged.

## Correction and relevance boundary

`attach_relevant_support_evidence` adds at most one already-ranked structured CKL record to an existing Did You Know card. The record must share the card's CKL parent, exact verse anchors, at least one source, and a substantive subject term. The primary evidence must be a direct-context structured CKL record; the support must be passage-scoped and classified as later reception, comparative context, or intertextual reuse. The support must already be in the ranked shortlist.

For Jonah, the fish claim and the three-days claim both belong to `jonah`, both anchor specifically to Jonah 1:17, share `jonah-masoretic` and `graybill-kaltner-mckenzie-jonah`, and share the subject “fish.” The primary card remains the direct textual/historical claim about the great fish. The support remains the separate `reception_history` claim with `dig_deeper` role; it says that the narrated duration later becomes important in Matthew 12:40 and preserves the caution against deriving a precise biological chronology. This exposes its actual identity as support without presenting later canonical reception as a first-audience fact.

The change does not add a card, change ranking or card order, alter confidence or interpretation labels, change Walk the Land, or boost reception claims in general. The three-card limit remains enforced.

## Real CKL-backed Companion response and cache

The API regression calls `/api/study/companion-context` for Jonah 1:17 through the real default CKL-backed service. The following are selected fields from its actual response shape:

```json
{
  "presentation_packet": {
    "cards": [{
      "id": "did-you-know-jonah-great-fish",
      "evidence_ids": ["jonah-great-fish", "jonah-three-days"]
    }]
  },
  "presentation_evidence": [{
    "id": "jonah-three-days",
    "ckl_record_identity": {
      "object_id": "jonah",
      "record_kind": "claim",
      "record_id": "jonah-three-days"
    }
  }]
}
```

The serialized support claim retains the sources `jonah-masoretic` and `jonah-new-testament`. The real application reproduction used `deterministic_fallback`; no existing presentation-cache entry was present at the default local cache path. A separate API regression seeds the production SQLite cache adapter with a packet generated from the real CKL bundle, confirms an actual `cached` engine result, and verifies that the same exact identity is serialized through the Companion API. Thus cache reuse also receives the support identity without replacing the claim's original identity.

## Verified route and browser results

The actual Narrative Explorer projection resolves `jonah-1-17-matthew-12-40-sign-of-jonah` and identifies `ckl:jonah#claim:jonah-three-days` as supporting evidence. The route category is `later_canonical_reception`; its historical direction remains Jonah 1:17 → Matthew 12:40 when started at either endpoint. Route details retain source provenance and the stated uncertainty about chronology, idiom, and “heart of the earth.” The browser uses the exact visible “Explore this connection” action, follows the route to the other passage, and returns with the original verse selection and trail intact.

The focused Selenium tests started a local app with Narrative Explorer enabled and copied the actual canonical library into an isolated temporary data root. They did not inject a Jonah presentation fixture.

| Browser journey | Result | Companion requests | Narrative Explorer passage requests |
|---|---:|---:|---:|
| Jonah 1:17 → Matthew 12:40 → return | Pass | 3 | 3 |
| Direct Matthew 12:40 → Jonah 1:17 → return | Pass | 3 | 3 |
| Genesis 1:1–5 → John 1:1–5 → return | Pass | 7 | 3 |
| Psalm 22:1 negative control | Pass; no action | 2 | 1 |
| Deuteronomy 32:8–9 held-route control | Pass; no action | 3 | 1 |

The counts are browser resource requests across verse selection and the full journey. Genesis selects five individual verses, so it causes additional Companion refreshes. The four browser tests pass together.

Genesis retains its existing route `genesis-1-john-1-creation-word`, its `john#claim:john-logos` identity, and its interpretive-association/uncertainty details. Psalm 22 / Mark 15 has no projected route or action. Deuteronomy 32 / Psalm 82 remains held and has no projected route or action. Actual CKL-backed service regressions also compare Genesis 1, Acts 2, Psalm 22, and Deuteronomy 32 against their unchanged deterministic cards.

The existing frontend suite passes its fail-closed controls for source-only and topic-only matches, wrong parent/kind/local ID, duplicate route IDs, partial or failed projections, and history changes before route verification.

## Validation and protected research inputs

| Check | Result |
|---|---|
| Companion, presentation, Narrative Explorer, API, projection, passage, and curation backend set | 660 passed, 8 skipped, 3 subtests passed |
| Jonah actual CKL API, SQLite cache, and unrelated-passage regressions | 3 passed |
| Presentation ranking, deterministic fallback, and integrity boundary | 68 passed |
| NE-9C curation, Vercel startup/package/index, and Tyndale provisioning | 35 passed |
| `npm test` | 14 frontend test files passed |
| Real CKL-backed browser journeys | 4 passed |
| `python -m framework.canonical_library --root framework/canonical_library --json` | 687 objects; zero errors; inventory fingerprint matches |
| `python tools/ckl_validate.py --root framework/canonical_library --json` | 687 valid objects; zero errors; 14 existing warnings |
| Protected CKL, lock, NE-9C, and NE-10 paths compared with `origin/master` | No differences |

Protected fingerprints compare as follows:

| Input | Baseline | After correction |
|---|---|---|
| CKL inventory (687 objects) | `90fa7547ea4146328ab1fc4f9e4ca1b262f810e0e503c589b64a5f9b8c4a08c6` | Same; revalidated |
| CKL object/source tree | `e186df409fb6231c0e93f13d14677826e31684a355b4681aa3ca98bf299a6766` | Same; recomputed |
| NE-9C curation tree | `691c9201d50eb0cceccac1b1a6d1beaa58f65b96cac54241cc856c8e2bc87a31` | Same; protected paths unchanged |
| NE-9C active identities | `528f6a36dd729a90d16beaa023400bb80821f021f25417076d3b8f831e016dd0` | Same; protected paths unchanged |
| NE-10 registry tree | `6dfe864406a2b28fa2ec7c997f7cb66decabf645f483706d25c76058512649b6` | Same; protected paths unchanged |
| NE-10 active identities | `c0c329dd1002a5519a1bc5301975b7821a81802b98eec6ebd837e473c97e919f` | Same; protected paths unchanged |
| NE-10 held candidates | `ad1a754affefdcb5bfe7aff0b7c059d0624521b85ecd42c7cda7f870656608d3` | Same; protected paths unchanged |

The unchanged curation inputs retain all 44 verified NE-10 bridges, all seven held candidates, and the 3,925 reviewed NE-9C decisions (408 curated, 1,895 held, and 1,622 excluded). No new or modified canonical relationship was introduced.

## Remaining issues and delivery boundary

The merged-master integrity report documents six presentation structured-output test failures, one CKL governance test failure, and 24 release-path sanitizer findings as pre-existing baseline issues. Those unrelated gates were not modified or weakened and were not rerun here. CKL validation continues to report its 14 existing warnings.

NE-11D1 acceptance work is complete for review. NE-11D2 remains the later integrated acceptance step. This branch is not merged or deployed.
