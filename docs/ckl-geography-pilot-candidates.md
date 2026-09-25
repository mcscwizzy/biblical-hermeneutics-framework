# CKL Geography Pilot Candidate Dry Run

## Source lock input

- Statuses: {'LOCKED': 30, 'REJECTED': 6, 'UNRESOLVED': 5}
- Eligible LOCKED claims: 28
- Excluded claims: 13

## Candidates

- Generated: 28
- Accepted: 20; rejected: 8; duplicate existing: 0; duplicate pilot: 0; complementary: 8; conflicting: 0
- Relationship types: {'campaign-against': 1, 'campaign-location-context': 1, 'deployment-from-to': 1, 'encirclement-context': 1, 'immersed-in': 1, 'local-population-context': 1, 'located-in': 2, 'movement-and-settlement': 1, 'narrated-travel-stages': 4, 'physical-marine-context': 1, 'physical-setting': 3, 'settlement-access-context': 1, 'settlement-context': 1, 'travel-between': 1}

## Dry run

- Full-library validation: PASS
- Transaction: DRY_RUN_PASS; wrote production CKL: False
- Objects: ['1-samuel', '2-kings', 'acts', 'bethlehem-1', 'genesis', 'isaiah', 'jericho-1', 'john', 'judges', 'matthew', 'nazareth', 'ruth']
- Files: ['framework/canonical_library/objects/books/1-samuel.json', 'framework/canonical_library/objects/books/2-kings.json', 'framework/canonical_library/objects/books/acts.json', 'framework/canonical_library/objects/books/genesis.json', 'framework/canonical_library/objects/books/isaiah.json', 'framework/canonical_library/objects/books/john.json', 'framework/canonical_library/objects/books/judges.json', 'framework/canonical_library/objects/books/matthew.json', 'framework/canonical_library/objects/books/ruth.json', 'framework/canonical_library/objects/places/bethlehem-1.json', 'framework/canonical_library/objects/places/jericho-1.json', 'framework/canonical_library/objects/places/nazareth.json']

## Changed references

- Direct: ['1 Samuel 17:2-3', '2 Kings 5:10', '2 Kings 5:14', '2 Kings 5:5-6', '2 Kings 5:9-10', 'Acts 27:13-15', 'Acts 27:20', 'Acts 27:7-8', 'Genesis 13:1', 'Genesis 13:10', 'Genesis 13:11-12', 'Genesis 13:3', 'Genesis 34:20-21', 'Genesis 34:30', 'Isaiah 36:1', 'Isaiah 36:2', 'John 4:3-4', 'John 4:43', 'Joshua 6:1', 'Joshua 6:15', 'Joshua 6:3-4', 'Judges 20:1-3', 'Judges 20:19-20', 'Matthew 2:1', 'Matthew 2:13-15', 'Matthew 2:19-23', 'Matthew 2:22-23', 'Matthew 2:8-11', 'Ruth 1:1-2', 'Ruth 1:19-22']
- Dependent: []

## Commentary v1.2 preview

- EvidenceBundles and syntheses that would rebuild: 11
- No production Commentary artifacts were modified.

## Protected chapters

- Acts 16: 0 candidate writes
- Mark 5: 0 candidate writes
- Psalms 76: 0 candidate writes
- Revelation 18: 0 candidate writes
- Zechariah 2: 0 candidate writes

## Apply readiness

NOT READY TO APPLY

Eight source-locked claims require entity bootstrap or a typed target-value representation that the current CKL schema cannot preserve. No production apply was run.
