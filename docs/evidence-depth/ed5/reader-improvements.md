# ED-5 reader improvements

Two bounded overview changes respond to reproduced presentation opportunities:

1. For a **completed** CKL lookup with zero eligible passage material, the
   overview now explains that this is a limit in current BHF coverage, says it
   does not imply a lack of historical significance, and offers the existing
   “Understand the Passage” route. Failed or incomplete lookups do not receive
   this completed-empty message.
2. A collapsed native disclosure offers plain-language explanations for
   recurring research terminology. It stays out of the initial reading flow
   until opened and explicitly says definitions do not decide how a term
   applies to a passage.

Regression coverage confirms the empty notice appears only for completed
`not_represented` CKL coverage, preserves the six existing categories, and
keeps the terminology guide collapsed initially. Source data, source IDs,
reader ranking, exact anchors, location quick glance, category count, and
relationship curation did not change.

No new model calls, services, or dependencies were added. Existing Ask BHF and
Dig Deeper actions remain available. See [before/after results](before-after-results.md)
for the measurable outcome and its browser limitation.
