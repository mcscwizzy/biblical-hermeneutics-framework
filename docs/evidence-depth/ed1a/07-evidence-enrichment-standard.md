# ED-1A evidence enrichment standard

This standard reuses the current CKL schema and review workflow. It does not authorize edits to CKL objects, source locks, NE-9C decisions, or NE-10 bridge records. Every addition needs a named reviewer and a traceable scholarly basis.

## Choose the right record and owning domain

1. Add evidence only when the passage raises a useful, answerable historical, cultural, linguistic, literary, textual, geographical, or reception question. Do not fill a checklist category because a chapter has zero records.
2. Use an `evidence_items[]` record for a discrete source-grounded observation. Use a `claims[]` record for a concise, qualified proposition that may synthesize more than one observation. Use `interpretive_notes[]` for a short textual observation, caution, or interpretation that fits the existing note taxonomy. Keep archaeology catalog descriptions, media, rights and excavation records in the archaeology service; point to them through `external_references` when the passage link is warranted.
3. Keep textual observation and scholarly interpretation separate. The existing evidence schema provides `primary_observation`, `scholarly_interpretation`, `assertion_type`, `confidence`, and `confidence_rationale`. Claims and notes have certainty and dispute-status fields; use the existing CKL taxonomies rather than prose labels that imply certainty.

## Required authoring information

Use the current schema fields wherever they fit:

- **Stable identity:** canonical object ID and stable kebab-case child `id`. Do not derive identity from display text. For interpretive notes without a local ID, the runtime uses a stable content hash; changing the note text changes its projected identity.
- **Precise Scripture scope:** `scripture_references` on the child record. An evidence passage link records `reference`, `relationship`, `temporal_relation`, `relevance_rationale`, and `weight`. Cite the narrowest scope the source actually supports. Broad parent references do not substitute for a passage-level child scope.
- **Type:** an allowed `claim_type`, `evidence_type`, or `note_type`. Choose categories by the record's actual scholarly work, not by terms appearing in its prose. In particular, `biblical_text` and `textual-observation` are not substitutes for lexical study or textual criticism.
- **Factual description:** a concise, non-rhetorical `description`, `primary_observation`, or claim text. State what the source is or what the text says before explaining what it may mean.
- **Relevance:** evidence `passage_relevance` plus the passage link's `relevance_rationale`; claim or note rationale when helpful. Explain the inferential step and why the item matters to this exact passage.
- **Chronology:** `temporal_scope` distinguishes dated evidence, periods, narrative setting, and source-composition dates. Record approximate dates as approximate and keep the date of an ancient event, artifact, textual witness, source composition, and later reception distinct.
- **Sources:** use stable parent `sources[]` entries with `title`, `author`, `publisher`, `year`, `locator`, `url`, `source_type`, and `supports` where available. Child `source_ids` or note `sources` must refer to a source on that parent object. Include a specific page, section, line, inscription number, manuscript shelfmark, accession number, verse, or catalog locator whenever the consulted source provides one. A bibliography entry on its own does not identify which child claim it supports.
- **External-domain identity:** use `external_references` with the existing domain and stable ID; do not duplicate an archaeology item, media asset, map geometry, or manuscript catalog record in CKL.
- **Uncertainty and alternatives:** record `certainty`, `dispute_status`, and evidence `confidence`/`confidence_rationale` as supported. For consequential disagreements, summarize the major options with representative support and limits; do not manufacture alternatives where there is no meaningful dispute.
- **Review governance:** the CKL object has `content_status`, `review_status`, `reviewed_by`, `last_reviewed`, `confidence`, and `human_review_required`. Apply existing governance rules at object level and do not imply a child-level approval that the schema does not record. Preserve machine-readable provenance and authoring history where the existing object uses them.
- **Relationships:** only add `related_objects`, `related_evidence`, or a reviewed passage bridge when the relationship type and endpoints pass their current criteria. An evidence citation, shared topic, or lexical overlap is not itself a narrative connection.

## Citation, rights and chronology rules

- Never invent bibliographic details, quotations, manuscript readings, artifact identifications, or page locators. If a source cannot be checked, list the question as unresolved instead of filling in missing metadata.
- Do not reproduce proprietary commentary, lexicon definitions, paid database records, or licensed datasets. Cite a lawfully consulted source in original wording. Record licensing/attribution in the owning data service where required.
- Treat royal inscriptions and monumental art as evidence of ancient royal self-presentation as well as evidence about events. Identify their date and genre.
- Label later reception (Second Temple, rabbinic, Christian, or modern) explicitly. Do not attribute later concepts to a text's original audience without evidence.
- Comparative literature can illuminate shared motifs or cultural vocabulary. It cannot establish borrowing, common authorship, or a direct historical link without specific evidence.
- A lack of material evidence is a limit to a claim, not an automatic defect in CKL. A map coordinate does not prove the ancient identity of a site.

## Review checklist for each proposed addition

Before approval, a reviewer should be able to answer:

1. Is this genuinely useful for understanding this passage and its original audience?
2. Does the child record have its own precise canonical scope, or is any broader contextual scope clearly labeled?
3. Can a reader trace every substantive claim to a named source and a specific locator?
4. Does the source support this particular claim and the proposed certainty, rather than merely mentioning the same subject?
5. Are primary observation, scholarly interpretation, and later reception distinguishable?
6. Have meaningful alternatives and uncertainty been retained without manufacturing consensus?
7. Is the record in the right domain, with stable IDs and any required external link?
8. Does the current CKL validator, source integrity tooling, and Narrative Explorer projection accept the record without weakening a gate?
9. Are existing accepted, held and excluded NE-9C/NE-10 states preserved?

Counts are not acceptance criteria. A research finding may be that existing material is sufficient, that a presentation link is needed, that a source cannot be established, or that the passage does not warrant the proposed evidence type.
