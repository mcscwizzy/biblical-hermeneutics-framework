# Commentary 1.5 scale-pilot evaluation

Status: **STOPPED_AFTER_WAVE_A**
Classification: **COMMENTARY_1_5_SCALE_NEEDS_CONTRACT_HARDENING**

Prompt 1.5, schema 1.2, synthesis compiler 1.1, and Gate v2.1 remained frozen. ReaderSynthesisPlan: NOT IMPLEMENTED / NOT REQUIRED.

Renderer: GPT-5 Codex; reasoning effort: NOT_EXPOSED.

## Wave A

Generated 20; validated 17; rejected 3; safety failures 0.
Gate distribution: {'PASS': 15, 'QUALITY_FAIL': 1, 'PASS_WITH_WARNING': 1}
Availability: {'THIN': 4, 'AVAILABLE': 14, 'DATA_GAP': 2}
Density: {'1-5': 4, '11-20': 6, '21-40': 4, '41+': 1, '6-10': 3, '0': 2}
Literary: {'Prophets': 5, 'Gospels/Acts': 4, 'Genealogy/list/administrative': 1, 'Epistles': 2, 'Historical narrative': 3, 'Pentateuch': 3, 'Poetry/Wisdom': 1, 'Apocalyptic / highly symbolic': 1}
Structural rejection codes: {'VALIDATION_FAILED': 3, 'MALFORMED_SECTION': 2, 'MALFORMED_VERSE_REFERENCE': 3}
Dump distribution: {'NONE': 16, 'LOW': 1}

## Stop decision

Structural-reference variance: {'repeated': True, 'codes': {'VALIDATION_FAILED': 3, 'MALFORMED_SECTION': 2, 'MALFORMED_VERSE_REFERENCE': 3}}. The pilot stopped before the next wave because unrelated repeated malformed verse/section references indicate contract variance. No malformed response was repaired or rerendered.

Full-Bible generation remains unauthorized.
