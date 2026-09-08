# Commentary 1.5 scale-pilot evaluation

Status: **COMPLETE**
Classification: **COMMENTARY_1_5_SCALE_PILOT_COMPLETE**

Prompt 1.5, schema 1.2, synthesis compiler 1.1, and Gate v2.1 remained frozen. ReaderSynthesisPlan: NOT IMPLEMENTED / NOT REQUIRED.

Renderer: GPT-5 Codex; reasoning effort: NOT_EXPOSED.

## Wave A

Generated 20; validated 20; rejected 0; safety failures 0.
Gate distribution: {'PASS': 18, 'QUALITY_FAIL': 1, 'PASS_WITH_WARNING': 1}
Availability: {'THIN': 4, 'AVAILABLE': 14, 'DATA_GAP': 2}
Density: {'1-5': 4, '11-20': 6, '21-40': 4, '41+': 1, '6-10': 3, '0': 2}
Literary: {'Prophets': 5, 'Gospels/Acts': 4, 'Genealogy/list/administrative': 1, 'Epistles': 2, 'Historical narrative': 3, 'Pentateuch': 3, 'Poetry/Wisdom': 1, 'Apocalyptic / highly symbolic': 1}
Structural rejection codes: {}
Dump distribution: {'NONE': 19, 'LOW': 1}

## Wave B

Generated 20; validated 19; rejected 1; safety failures 0.
Gate distribution: {'PASS_WITH_WARNING': 3, 'PASS': 15, 'QUALITY_FAIL': 1}
Availability: {'AVAILABLE': 13, 'THIN': 5, 'DATA_GAP': 2}
Density: {'21-40': 2, '11-20': 3, '41+': 5, '6-10': 3, '1-5': 5, '0': 2}
Literary: {'Pentateuch': 3, 'Genealogy/list/administrative': 3, 'Gospels/Acts': 4, 'Epistles': 3, 'Prophets': 3, 'Historical narrative': 1, 'Poetry/Wisdom': 3}
Structural rejection codes: {'VALIDATION_FAILED': 1, 'MALFORMED_VERSE_REFERENCE': 1}
Dump distribution: {'LOW': 2, 'NONE': 15, 'MODERATE': 2}

## Wave C

Generated 20; validated 20; rejected 0; safety failures 0.
Gate distribution: {'PASS': 17, 'PASS_WITH_WARNING': 3}
Availability: {'AVAILABLE': 13, 'DATA_GAP': 4, 'THIN': 3}
Density: {'41+': 4, '21-40': 4, '0': 4, '1-5': 3, '6-10': 4, '11-20': 1}
Literary: {'Epistles': 5, 'Historical narrative': 5, 'Poetry/Wisdom': 3, 'Genealogy/list/administrative': 2, 'Prophets': 2, 'Pentateuch': 2, 'Apocalyptic / highly symbolic': 1}
Structural rejection codes: {}
Dump distribution: {'NONE': 17, 'LOW': 3}

## Stop decision

Structural-reference variance: {'repeated': False, 'codes': {'VALIDATION_FAILED': 1, 'MALFORMED_VERSE_REFERENCE': 1}}. All planned waves completed without repeated structural-reference variance. No malformed response was repaired or rerendered.

Full-Bible generation remains unauthorized.
