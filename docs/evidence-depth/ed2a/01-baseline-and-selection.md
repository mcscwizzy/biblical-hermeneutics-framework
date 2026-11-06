# ED-2A Psalms Wave 1: baseline and selection

## Prerequisite and research basis

This wave starts from `origin/master` commit `9b8684dc8d2e551331179a7820fb141551f65ef3`. ED-1C is merged there as PR #75 (`fix ed1c evidence discoverability`). The audit read the ED-1A reports under [`../ed1a/`](../ed1a/), the ED-1B enrichment standard and Psalm 72 pilot under [`../ed1b/`](../ed1b/), and the ED-1C additional-record reader and accessibility work under [`../ed1c/`](../ed1c/).

The census was reproduced, rather than copied from the historical reports:

```sh
python3 scripts/audit_ed1a_evidence_depth.py \
  --output-dir /tmp/ed2a-psalms-baseline \
  --study-db .bhf-data/study.sqlite
```

At the ED-1C base, the run validated 687 CKL objects and produced 1,189 chapter rows with zero unmapped record identities. Psalms has 150 chapter rows:

| ED-1A coverage category | Psalms chapters |
| --- | ---: |
| No eligible CKL material | 74 |
| Contextual coverage | 22 |
| Passage-specific evidence | 53 |
| Entity-only coverage | 1 |

The census measures passage-scoped CKL availability under the audit’s eligibility rules. It does not measure scholarly quality or completeness. Historical counts in ED-1A and ED-1B remain useful reference points, not the current baseline. The reproduced CKL inventory fingerprint is `7d5c8b636176b75452f82a7276d1b51a69180414e40ab7ea82527a1fd80f940c`.

The no-eligible Psalms chapters at baseline are 5–7, 11–12, 14–15, 17, 20–21, 25–26, 28, 30, 33, 35, 37–39, 43, 45–49, 52–53, 55–67, 69–71, 75–77, 80–81, 83, 86–87, 91–92, 94, 96–102, 105, 108–109, 111, and 135, 138–145.

## Wave selection

Nine Psalms were selected for genre and research diversity. Eight had no eligible CKL item; Psalm 44 had one existing passage-specific claim and is included to add a distinct, source-backed reading of this particular communal lament. Psalm 72 remains the positive control and is not counted toward the nine new items.

| Psalm | Baseline | Research need and genre range | Exact new item scope |
| --- | --- | --- | --- |
| 6 | No eligible material | Individual lament; body idiom and distress without a medicalized setting | 6:2–8 |
| 15 | No eligible material | Ethical entrance-liturgy proposal; worship access and social conduct | 15:1–5 |
| 30 | No eligible material | Thanksgiving/lament movement; ambiguous dedication superscription and reuse | 30:1–12 |
| 37 | No eligible material | Wisdom-like instruction and alphabetic acrostic; missing ayin unit | 37:1–40 |
| 44 | One passage-specific claim | Communal lament, protest, and debated Book II historical memory | 44:1–26 |
| 47 | No eligible material | Kingship / enthronement hymn and uncertain cultic setting | 47:1–9 |
| 67 | No eligible material | Blessing petition, jussive pattern, nations, and contested harvest reading | 67:1–7 |
| 96 | No eligible material | YHWH-kingship hymn, nations, creation, and a qualified memory reading | 96:1–13 |
| 145 | No eligible material | Alphabetic praise and ancient textual witnesses to a nun strophe | 145:13 |

Psalm 44 is not described as a no-coverage chapter: the existing claim `psalms-lament-praise-range` already includes Psalm 44:1–26. The new evidence does not duplicate its broad claim about the Psalter preserving lament and praise; it makes a narrower, attributed observation about this poem’s communal movement and a clearly qualified Book II redactional proposal.

## Psalm 72 positive control

The existing ED-1B item `psalm-72-royal-justice-setting` remains unchanged, with scope Psalm 72:1–14 and sources `psalms-masoretic` and `human-psalm72-leadership`. It remains medium confidence, marks historical uncertainty, distinguishes textual observation from Human’s royal-ideology interpretation, and leaves the king, occasion, and date unidentified. The book remains `draft`, `in_review`, `reviewed_by: []`, and `human_review_required: true`.

## Selection boundaries

- The nine records do not assert absolute composition dates or reconstruct an exact historical occasion from a superscription or genre label.
- The Psalm 47 item does not claim a divine-council scene. Psalm 96’s reference to the nations’ gods is not used to infer a council scene.
- Psalm 145 records a textual variant without declaring the Masoretic form corrupt or the Qumran/Greek form original.
- No NE-9C or NE-10 relationship decision is part of this wave. Shared imagery or reception history alone creates no route.
