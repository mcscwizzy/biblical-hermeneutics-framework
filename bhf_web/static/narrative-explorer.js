/* Passage-scoped, source-grounded Narrative Explorer view and request lifecycle. */
(function (root, factory) {
  const explorer = factory(root);
  if (typeof module === "object" && module.exports) module.exports = explorer;
  root.BHFNarrativeExplorer = explorer;
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  "use strict";

  const PAGE_SIZE = 12;
  const MAX_RELATIONSHIP_HOPS = 3;
  const MAX_TRAIL_NODES = 12;
  const CONNECTION_PAGE_SIZE = 12;
  const pendingRequests = new Map();
  const SECTIONS = [
    {
      id: "biblical_narrative",
      title: "Biblical Narrative",
      description: "Notice how this passage is told: its sequence, structure, and literary features.",
    },
    {
      id: "archaeology_ancient_history",
      title: "Archaeology & Ancient History",
      description: "Explore material remains, inscriptions, historical records, and ancient writings with evidence types kept clear.",
    },
    {
      id: "biblical_geography",
      title: "Biblical Geography",
      description: "Explore physical places and routes with the identification limits recorded by BHF.",
    },
    {
      id: "divine_council_cosmic_geography",
      title: "Divine Council & Cosmic Geography",
      description: "Explore source-based readings of sacred space, divine assembly, and ancient cosmology. These do not establish physical locations.",
    },
    {
      id: "themes_biblical_connections",
      title: "Themes & Biblical Connections",
      description: "Explore themes and documented relationships between biblical passages.",
    },
    {
      id: "people_events_relationships",
      title: "People, Events & Relationships",
      description: "Explore people, events, groups, and institutions linked by the sources.",
    },
  ];
  const SOURCE_LABELS = {
    canonical_knowledge_library: "Evidence library",
    passage_maps: "Maps",
    archaeology_passage_resolver: "Archaeology sources",
  };
  const PHYSICAL_GEOGRAPHY = new Set([
    "physical_place", "physical_region", "political_territory", "route", "archaeological_site",
  ]);

  function urlFor(selection) {
    const book = String(selection?.book || "").trim();
    const chapter = Number(selection?.chapter || 0);
    if (!book || !Number.isInteger(chapter) || chapter < 1) {
      throw new Error("A book and chapter are required to explore this passage.");
    }
    const url = `/api/narrative-explorer/v1/passages/${encodeURIComponent(book)}/${chapter}`;
    const startVerse = positiveInteger(selection?.startVerse ?? selection?.verse_start);
    const endVerse = positiveInteger(selection?.endVerse ?? selection?.verse_end);
    if (endVerse && !startVerse) {
      throw new Error("A verse range requires a starting verse.");
    }
    const parameters = new URLSearchParams();
    if (startVerse) parameters.set("verse_start", String(startVerse));
    if (endVerse) parameters.set("verse_end", String(endVerse));
    return parameters.size ? `${url}?${parameters.toString()}` : url;
  }

  function positiveInteger(value) {
    const number = Number(value || 0);
    return Number.isInteger(number) && number > 0 ? number : 0;
  }

  function findVerifiedPassageRoute(projection, routeId, identity, passageReference) {
    const related = projection?.related_passages;
    if (related?.state !== "available" || related?.query_status !== "complete") return null;
    if (normalizePassageRouteReference(projection?.passage?.reference) !== normalizePassageRouteReference(passageReference)) return null;
    const requestedIdentity = normalizedCklRecordIdentity(identity);
    const requestedRouteId = typeof routeId === "string" ? routeId : "";
    if (!requestedRouteId || requestedRouteId.trim() !== requestedRouteId || !requestedIdentity) return null;

    const routes = [
      ...(Array.isArray(related.authored_relationships) ? related.authored_relationships : [])
        .map((route) => ({route, kind: "authored"})),
      ...(Array.isArray(related.evidence_backed_bridges) ? related.evidence_backed_bridges : [])
        .map((route) => ({route, kind: "bridge"})),
    ];
    const matches = routes.filter(({route}) => readerText(route?.id) === requestedRouteId);
    if (matches.length !== 1) return null;
    const {route, kind} = matches[0];
    if (!readerText(route?.source_passage)
      || !readerText(route?.destination_passage)
      || !readerText(route?.relationship_category)
      || !readerText(route?.explanation)
      || !readerText(route?.uncertainty)) return null;

    const supports = kind === "bridge"
      ? (Array.isArray(route.supporting_records) ? route.supporting_records : [])
        .map((record) => normalizedCklRecordIdentity(record))
      : (Array.isArray(route.supporting_record_ids) ? route.supporting_record_ids : [])
        .map(parseCklRecordIdentity)
        .filter(Boolean);
    return supports.some((support) => sameCklRecordIdentity(support, requestedIdentity)) ? route : null;
  }

  function normalizedCklRecordIdentity(value) {
    const objectId = value?.object_id;
    const recordKind = value?.record_kind;
    const recordId = value?.record_id;
    if ([objectId, recordKind, recordId].some((part) => typeof part !== "string" || !part || part.trim() !== part)
      || !["claim", "evidence"].includes(recordKind)) return null;
    return {object_id: objectId, record_kind: recordKind, record_id: recordId};
  }

  function parseCklRecordIdentity(value) {
    if (typeof value !== "string" || !value || value.trim() !== value) return null;
    const match = value.match(/^ckl:([^#]+)#(claim|evidence):(.+)$/);
    if (!match) return null;
    return {object_id: match[1], record_kind: match[2], record_id: match[3]};
  }

  function sameCklRecordIdentity(left, right) {
    return Boolean(left && right)
      && left.object_id === right.object_id
      && left.record_kind === right.record_kind
      && left.record_id === right.record_id;
  }

  function normalizePassageRouteReference(value) {
    return readerText(value).toLocaleLowerCase().replace(/[‐‑‒–—−]/g, "-").replace(/\s+/g, " ");
  }

  function selectionSnapshot(value) {
    const book = readerText(value?.book);
    const chapter = positiveInteger(value?.chapter);
    if (!book || !chapter) return null;
    const selectedVerses = Array.isArray(value?.selectedVerses)
      ? [...new Set(value.selectedVerses.map(positiveInteger).filter(Boolean))].sort((a, b) => a - b)
      : [];
    const startVerse = selectedVerses[0] || positiveInteger(value?.startVerse ?? value?.verseStart) || null;
    const endVerse = selectedVerses.at(-1) || positiveInteger(value?.endVerse ?? value?.verseEnd) || startVerse;
    const reference = readerText(value?.reference) || formatSelectionReference(book, chapter, selectedVerses, startVerse, endVerse);
    return {
      book,
      chapter,
      startVerse,
      endVerse: endVerse || null,
      selectedVerses,
      selectedText: readerText(value?.selectedText ?? value?.text),
      translation: readerText(value?.translation).toLowerCase(),
      selectedWord: value?.selectedWord && typeof value.selectedWord === "object" ? {...value.selectedWord} : null,
      reference,
    };
  }

  function formatSelectionReference(book, chapter, verses, startVerse, endVerse) {
    if (verses.length) {
      const ranges = [];
      let start = verses[0];
      let end = start;
      verses.slice(1).forEach((verse) => {
        if (verse === end + 1) end = verse;
        else {
          ranges.push(start === end ? String(start) : `${start}-${end}`);
          start = verse;
          end = verse;
        }
      });
      ranges.push(start === end ? String(start) : `${start}-${end}`);
      return `${book} ${chapter}:${ranges.join(",")}`;
    }
    if (startVerse) return `${book} ${chapter}:${startVerse}${endVerse > startVerse ? `-${endVerse}` : ""}`;
    return `${book} ${chapter}`;
  }

  function createTrail(selection) {
    const originSelection = selectionSnapshot(selection);
    if (!originSelection) throw new Error("A selected passage is required to start an evidence trail.");
    const origin = {
      kind: "passage",
      id: `passage:${originSelection.reference}`,
      label: originSelection.reference,
      reference: originSelection.reference,
      selection: originSelection,
      relationshipHops: 0,
      focusControlId: "",
    };
    return {originSelection, nodes: [origin], activeIndex: 0};
  }

  function trailNodes(trail) {
    if (!trail || !Array.isArray(trail.nodes) || !trail.nodes.length) return [];
    const activeIndex = Math.min(Math.max(0, Number(trail.activeIndex) || 0), trail.nodes.length - 1);
    return trail.nodes.slice(0, activeIndex + 1);
  }

  function activeTrailStep(trail) {
    return trailNodes(trail).at(-1) || null;
  }

  function trailCurrentSelection(trail) {
    const nodes = trailNodes(trail);
    for (let index = nodes.length - 1; index >= 0; index -= 1) {
      if (nodes[index].kind === "passage" && nodes[index].selection) return nodes[index].selection;
    }
    return selectionSnapshot(trail?.originSelection);
  }

  function currentRelationshipHops(trail) {
    return Number(activeTrailStep(trail)?.relationshipHops || 0);
  }

  function appendTrailStep(trail, step) {
    const nodes = trailNodes(trail);
    const boundedNodes = nodes.length >= MAX_TRAIL_NODES
      ? [nodes[0], ...nodes.slice(-(MAX_TRAIL_NODES - 2))]
      : nodes;
    return {
      originSelection: selectionSnapshot(trail?.originSelection),
      nodes: [...boundedNodes, step],
      activeIndex: boundedNodes.length,
    };
  }

  function addEvidenceStep(trail, item, focusControlId = "") {
    const itemId = readerText(item?.id);
    if (!itemId) throw new Error("A projected item ID is required to inspect evidence.");
    const current = activeTrailStep(trail);
    const parentObjectId = readerText(item.parent_object_id || item.object_id);
    return appendTrailStep(trail, {
      kind: "evidence",
      id: itemId,
      label: readerText(item.title || item.claim_text || item.description) || itemId,
      parentObjectId,
      selection: trailCurrentSelection(trail),
      relationshipHops: currentRelationshipHops(trail),
      focusControlId: readerText(focusControlId),
    });
  }

  function followEvidence(trail, item, relationship, focusControlId = "") {
    const itemId = readerText(item?.id);
    const parentObjectId = readerText(item?.parent_object_id || item?.object_id);
    const localId = readerText(item?.evidence_id || item?.local_id);
    if (item?.record_kind !== "evidence" || !parentObjectId || !localId
      || itemId !== `ckl:${parentObjectId}#evidence:${localId}`
      || readerText(item?.evidence_id) !== localId || readerText(item?.local_id) !== localId
      || !Array.isArray(item?.applicable_passage_anchors) || !item.applicable_passage_anchors.length) {
      return {state: trail, error: "invalid_target"};
    }
    const relation = relationshipSnapshot(relationship);
    const sourceLocalId = readerText(relation.localRecordId);
    const expectedSourceId = sourceLocalId ? `ckl:${parentObjectId}#evidence:${sourceLocalId}` : "";
    const current = activeTrailStep(trail);
    if (relation.basisKind !== "ckl_related_evidence"
      || relation.targetId !== itemId
      || relation.targetEvidenceId !== localId
      || relation.parentObjectId !== parentObjectId
      || relation.targetResolutionStatus !== "eligible"
      || relation.sourceId !== expectedSourceId
      || !["one_way", "reciprocal"].includes(relation.direction)
      || current?.kind !== "evidence"
      || current.id !== expectedSourceId) {
      return {state: trail, error: "invalid_relationship"};
    }
    if (currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) return {state: trail, error: "depth_limit"};
    if (trailNodes(trail).some((node) => node.kind === "evidence" && node.id === itemId)) {
      return {state: trail, error: "cycle"};
    }
    return {
      state: appendTrailStep(trail, {
        kind: "evidence",
        id: itemId,
        label: readerText(item.title || item.claim_text || item.description) || itemId,
        parentObjectId,
        selection: trailCurrentSelection(trail),
        relationship: relation,
        relationshipHops: currentRelationshipHops(trail) + 1,
        focusControlId: readerText(focusControlId),
      }),
      error: null,
    };
  }

  function followSubject(trail, subject, relationship, focusControlId = "") {
    const targetId = readerText(subject?.targetId || subject?.id);
    if (!targetId) return {state: trail, error: "missing_target"};
    if (currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) return {state: trail, error: "depth_limit"};
    const visited = trailNodes(trail).flatMap((node) => [
      readerText(node.subjectId), readerText(node.parentObjectId),
    ]).filter(Boolean);
    if (visited.includes(targetId)) return {state: trail, error: "cycle"};
    const current = activeTrailStep(trail);
    return {
      state: appendTrailStep(trail, {
        kind: "subject",
        id: `ckl:${targetId}`,
        targetId,
        subjectId: targetId,
        label: readerText(subject.title || subject.name) || targetId,
        relationship: relationshipSnapshot(relationship),
        selection: trailCurrentSelection(trail),
        relationshipHops: currentRelationshipHops(trail) + 1,
        focusControlId: readerText(focusControlId),
      }),
      error: null,
    };
  }

  function followPassage(trail, destination, relationship, focusControlId = "") {
    if (currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) return {state: trail, error: "depth_limit"};
    const selection = selectionSnapshot(destination?.selection || {});
    const reference = readerText(destination?.reference || selection?.reference);
    if (!selection || !reference) return {state: trail, error: "invalid_reference"};
    const normalizedReference = normalizeReference(reference);
    if (trailNodes(trail).some((node) => node.kind === "passage" && normalizeReference(node.reference) === normalizedReference)) {
      return {state: trail, error: "cycle"};
    }
    selection.reference = reference;
    return {
      state: appendTrailStep(trail, {
        kind: "passage",
        id: `passage:${reference}`,
        label: reference,
        reference,
        selection,
        relationship: relationshipSnapshot(relationship),
        relationshipHops: currentRelationshipHops(trail) + 1,
        focusControlId: readerText(focusControlId),
      }),
      error: null,
    };
  }

  function returnToOrigin(trail) {
    if (!trail || !Array.isArray(trail.nodes) || !trail.nodes.length) return trail;
    return {...trail, nodes: trail.nodes.slice(), activeIndex: 0};
  }

  function trailReturnFocusId(trail) {
    const activeIndex = Math.min(Math.max(0, Number(trail?.activeIndex) || 0), (trail?.nodes?.length || 1) - 1);
    return readerText(trail?.nodes?.[activeIndex + 1]?.focusControlId);
  }

  function relationshipSnapshot(value) {
    if (!value || typeof value !== "object") return {};
    const basis = value.basis && typeof value.basis === "object" ? value.basis : value;
    return {
      id: readerText(value.id),
      provenance: readerText(value.provenance),
      sourcePassage: readerText(value.source_passage || value.sourcePassage),
      destinationPassage: readerText(value.destination_passage || value.destinationPassage),
      relationshipCategory: readerText(value.relationshipCategory || value.relationship_category || value.connectionType || value.connection_type),
      evidenceLayer: readerText(value.evidenceLayer || value.evidence_layer),
      explanation: readerText(value.explanation),
      uncertainty: readerText(value.uncertainty),
      humanScholarlyApproval: readerText(value.humanScholarlyApproval || value.human_scholarly_approval),
      supportingRecordIds: (Array.isArray(value.supporting_records)
        ? value.supporting_records.map((record) => record?.id || record?.record_locator)
        : Array.isArray(value.supportingRecordIds)
          ? value.supportingRecordIds
          : Array.isArray(value.supporting_record_ids) ? value.supporting_record_ids : []).map(readerText).filter(Boolean),
      supportingSourceIds: (Array.isArray(value.supporting_sources)
        ? value.supporting_sources.map((source) => source?.id)
        : Array.isArray(value.supportingSourceIds)
          ? value.supportingSourceIds
          : Array.isArray(value.supporting_ckl_sources) ? value.supporting_ckl_sources.map((source) => source?.source_id) : []).map(readerText).filter(Boolean),
      sourceId: readerText(value.sourceId || value.source_id),
      targetId: readerText(value.targetId || value.target_id),
      connectionType: readerText(value.connectionType || value.connection_type),
      originalRelationshipType: readerText(value.originalRelationshipType || value.original_relationship_type || value.relationship),
      direction: readerText(value.direction),
      relationshipMode: readerText(value.relationshipMode || value.relationship_mode),
      temporalLayer: readerText(value.temporalLayer || value.temporal_layer),
      basisKind: readerText(value.basisKind || basis.kind),
      parentObjectId: readerText(value.parentObjectId || basis.parent_object_id),
      localRecordId: readerText(value.localRecordId || basis.local_record_id),
      targetEvidenceId: readerText(value.targetEvidenceId || basis.target_evidence_id),
      targetResolutionStatus: readerText(value.targetResolutionStatus || basis.target_resolution_status),
      notes: readerText(value.notes || basis.notes),
      weight: metadataText(value.weight ?? basis.weight),
      anchor: readerText(value.anchor || value.reference || basis.reference),
      curation: curationSnapshot(value.curation),
    };
  }

  function curationSnapshot(value) {
    if (!value || typeof value !== "object") return null;
    const sourceList = Array.isArray(value.supporting_ckl_sources) ? value.supporting_ckl_sources : [];
    const certainty = value.ckl_evidence_certainty && typeof value.ckl_evidence_certainty === "object"
      ? value.ckl_evidence_certainty
      : {};
    return {
      classification: readerText(value.classification),
      textual_observation: readerText(value.textual_observation),
      why: readerText(value.why),
      applicable_passages: Array.isArray(value.applicable_passages) ? value.applicable_passages.map(readerText).filter(Boolean) : [],
      supporting_passages: Array.isArray(value.supporting_passages) ? value.supporting_passages.map(readerText).filter(Boolean) : [],
      supporting_comparative_material: Array.isArray(value.supporting_comparative_material)
        ? value.supporting_comparative_material.map((material) => ({
          kind: readerText(material?.kind),
          reference: readerText(material?.reference),
          label: readerText(material?.label),
          source_id: readerText(material?.source_id),
        })).filter((material) => material.reference && material.kind)
        : [],
      supporting_records: Array.isArray(value.supporting_records) ? value.supporting_records.map(readerText).filter(Boolean) : [],
      supporting_ckl_sources: sourceList.map((source) => ({
        object_id: readerText(source?.object_id),
        source_id: readerText(source?.source_id),
        title: readerText(source?.title),
        author: readerText(source?.author),
        year: metadataText(source?.year),
      })).filter((source) => source.object_id && source.source_id),
      uncertainty: readerText(value.uncertainty),
      curation_confidence: readerText(value.curation_confidence),
      curation_status: readerText(value.curation_status),
      ckl_evidence_certainty: {
        status: readerText(certainty.status),
        records: Array.isArray(certainty.records) ? certainty.records.map((record) => ({
          record_id: readerText(record?.record_id),
          certainty: readerText(record?.certainty),
          dispute_status: readerText(record?.dispute_status),
        })).filter((record) => record.record_id && record.certainty) : [],
      },
      human_scholarly_approval: readerText(value.human_scholarly_approval),
    };
  }

  function appendCurationSummary(document, parent, value, navigation = {}) {
    const curation = curationSnapshot(value);
    if (!curation || !curation.classification) return;
    appendTextElement(document, parent, "p", `Curated classification: ${connectionCategoryLabel(curation.classification)}.`, "narrative-explorer-curation-label");
    if (curation.textual_observation) {
      appendTextElement(document, parent, "p", `Textual observation: ${curation.textual_observation}`, "narrative-explorer-curation-observation");
    }
    if (curation.why) appendTextElement(document, parent, "p", `Why this connects: ${curation.why}`, "narrative-explorer-curation-explanation");
    if (curation.applicable_passages.length) {
      appendTextElement(document, parent, "p", `Curated passage scope: ${curation.applicable_passages.join(" · ")}.`, "narrative-explorer-curation-scope");
    }
    if (curation.supporting_passages.length) {
      appendTextElement(document, parent, "p", `Supporting Scripture passages: ${curation.supporting_passages.join(" · ")}.`, "narrative-explorer-curation-support");
      appendCurationPassageNavigation(
        document,
        parent,
        curation.supporting_passages,
        navigation.trail,
        navigation.options,
        navigation.relationship,
      );
    }
    if (curation.supporting_comparative_material.length) {
      const labels = curation.supporting_comparative_material.map((material) => (
        `${material.reference}${material.label ? ` (${material.label})` : ""}${material.source_id ? ` [CKL source: ${material.source_id}]` : ""}`
      ));
      appendTextElement(document, parent, "p", `Ancient comparative material (not Scripture): ${labels.join(" · ")}.`, "narrative-explorer-curation-comparative");
    }
    if (curation.supporting_ckl_sources.length) {
      const labels = curation.supporting_ckl_sources.map((source) => {
        const title = source.title || source.source_id;
        const author = [source.author, source.year].filter(Boolean).join(", ");
        return `${title}${author ? ` (${author})` : ""} [${source.object_id}/${source.source_id}]`;
      });
      appendTextElement(document, parent, "p", `CKL source records: ${labels.join("; ")}.`, "narrative-explorer-curation-sources");
    }
    if (curation.uncertainty) {
      appendTextElement(document, parent, "p", `Interpretive uncertainty: ${curation.uncertainty}`, "narrative-explorer-curation-uncertainty narrative-explorer-caution");
    }
    if (curation.curation_confidence) appendTextElement(document, parent, "p", `Curation confidence: ${curation.curation_confidence}.`, "narrative-explorer-curation-certainty");
    if (curation.ckl_evidence_certainty.status === "recorded") {
      const certaintyLabels = curation.ckl_evidence_certainty.records.map((record) => (
        `${record.record_id}: ${record.certainty}${record.dispute_status ? ` (${record.dispute_status})` : ""}`
      ));
      appendTextElement(document, parent, "p", `CKL evidence certainty: ${certaintyLabels.join(" · ") || "recorded; record details unavailable"}.`, "narrative-explorer-curation-evidence-certainty");
    } else {
      appendTextElement(document, parent, "p", "CKL evidence certainty: not recorded for this object relationship.", "narrative-explorer-curation-evidence-certainty");
    }
    if (curation.curation_status) {
      appendTextElement(document, parent, "p", `Curation status: ${curation.curation_status} (registry annotation; not human scholarly approval).`, "narrative-explorer-curation-status");
    }
    if (curation.human_scholarly_approval) {
      appendTextElement(document, parent, "p", `Human scholarly approval: ${curation.human_scholarly_approval.replace(/_/g, " ")}.`, "narrative-explorer-curation-approval");
    }
  }

  function appendCurationPassageNavigation(document, parent, references, trail, options, relationship) {
    if (typeof options?.onOpenPassage !== "function") return;
    const controls = element(document, "div", "narrative-explorer-curation-passage-actions");
    const seen = new Set();
    const currentReference = normalizeReference(trailCurrentSelection(trail)?.reference);
    references.forEach((reference) => {
      const resolved = validateScriptureReference(reference, options.knownBooks || []);
      if (!resolved.valid) {
        appendTextElement(document, controls, "p", `Passage navigation unavailable: ${resolved.reason}`, "narrative-explorer-missing-provenance");
        return;
      }
      const normalizedReference = normalizeReference(resolved.reference);
      if (seen.has(normalizedReference)) return;
      seen.add(normalizedReference);
      if (currentReference === normalizedReference) {
        appendTextElement(document, controls, "span", `Current passage: ${resolved.reference}`, "narrative-explorer-current-passage");
      } else if (passageIsInTrail(trail, normalizedReference)) {
        appendTextElement(document, controls, "span", `This passage already appears in the trail: ${resolved.reference}`, "narrative-explorer-trail-cycle");
      } else {
        appendActionButton(
          document,
          controls,
          `Open supporting passage: ${resolved.reference}`,
          `scripture:${resolved.reference}`,
          (button) => options.onOpenPassage(resolved, relationshipSnapshot(relationship), button),
        );
      }
    });
    if (controls.children.length) parent.append(controls);
  }

  function applyProjectionCurationsToSubject(subject, projection) {
    if (!subject || typeof subject !== "object") return subject;
    const sourceId = `ckl:${readerText(subject.id)}`;
    if (sourceId === "ckl:") return subject;
    const connections = Array.isArray(projection?.connections) ? projection.connections : [];
    const relatedObjectLinks = Array.isArray(subject.related_object_links) ? subject.related_object_links : [];
    return {
      ...subject,
      related_object_links: relatedObjectLinks.map((link) => {
        const targetId = `ckl:${readerText(link?.id)}`;
        const exactMatches = connections.filter((edge) => (
          edge?.source_id === sourceId
          && edge?.target_id === targetId
          && edge?.basis?.kind === "ckl_related_object"
          && edge?.original_relationship_type === readerText(link?.relationship)
          && edge?.basis?.notes === readerText(link?.notes)
          && Number(edge?.basis?.weight) === Number(link?.weight)
          && edge?.curation
        ));
        if (exactMatches.length !== 1) return link;
        const edge = exactMatches[0];
        return {
          ...link,
          source_id: edge.source_id,
          target_id: edge.target_id,
          connection_type: edge.connection_type,
          original_relationship_type: edge.original_relationship_type,
          relationship_mode: edge.relationship_mode,
          temporal_layer: edge.temporal_layer,
          direction: edge.direction,
          reverse_edge_id: edge.reverse_edge_id,
          basis: edge.basis,
          curation: edge.curation,
        };
      }),
    };
  }

  function normalizeReference(value) {
    return readerText(value).toLowerCase().replace(/\s+/g, " ");
  }

  function passageIsInTrail(trail, normalizedReference) {
    return trailNodes(trail).some((node) => node.kind === "passage"
      && normalizeReference(node.reference) === normalizedReference);
  }

  function validateScriptureReference(reference, bookOptions = []) {
    const match = readerText(reference).match(/^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$/);
    if (!match) return {valid: false, reason: "The Scripture reference format is not supported."};
    const normalizeBook = (value) => String(value || "").toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
    const requestedBook = normalizeBook(match[1]);
    let option = bookOptions.find((entry) => normalizeBook(entry?.value || entry?.label || entry) === requestedBook);
    if (!option && ["psalm", "psalms"].includes(requestedBook)) {
      option = bookOptions.find((entry) => ["psalm", "psalms"].includes(
        normalizeBook(entry?.value || entry?.label || entry),
      ));
    }
    if (!option) return {valid: false, reason: "This book name is not in the reader's canonical book list."};
    const book = readerText(option?.value || option?.label || option);
    const chapter = positiveInteger(match[2]);
    const chapterCount = positiveInteger(option?.chapters ?? option?.dataset?.chapters);
    const startVerse = match[3] ? positiveInteger(match[3]) : null;
    const endVerse = match[4] ? positiveInteger(match[4]) : startVerse;
    if (!chapter || !chapterCount || chapter > chapterCount) return {valid: false, reason: "This chapter is outside the reader's canonical book range."};
    if ((match[3] && !startVerse) || (match[4] && !endVerse) || (endVerse && startVerse && endVerse < startVerse)) {
      return {valid: false, reason: "This verse range is invalid."};
    }
    const canonicalReference = `${book} ${chapter}${startVerse ? `:${startVerse}${endVerse > startVerse ? `-${endVerse}` : ""}` : ""}`;
    return {valid: true, book, chapter, startVerse, endVerse, reference: canonicalReference};
  }

  function subjectMatchesId(expectedId, subject) {
    return Boolean(
      readerText(expectedId)
      && subject
      && typeof subject === "object"
      && readerText(subject.id) === readerText(expectedId)
      && readerText(subject.type)
      && subject.type !== "archaeology_compatibility"
      && subject.status !== "deprecated",
    );
  }

  function createSubjectLoader(options = {}) {
    const pending = new Map();
    const fetcher = options.fetcher || root.fetch?.bind(root);
    const resolveUrl = options.resolveUrl || resolveBackendUrl;

    async function get(objectId, signal) {
      const id = readerText(objectId);
      if (!id) throw new Error("A CKL target ID is required.");
      if (signal?.aborted) throw abortError();
      const path = `/api/canonical/objects/${encodeURIComponent(id)}`;
      let entry = pending.get(path);
      if (!entry) {
        if (typeof fetcher !== "function") throw new Error("Canonical subject details are unavailable in this browser.");
        const controller = new AbortController();
        entry = {url: path, controller, subscribers: 0, settled: false, promise: null};
        const startedAt = now();
        entry.promise = Promise.resolve()
          .then(() => fetcher(resolveUrl(path), {
            signal: controller.signal,
            cache: "no-store",
            headers: {Accept: "application/json"},
          }))
          .then(async (response) => {
            const raw = await response.text();
            dispatchMetric({
              phase: "subject-response",
              request_url: path,
              target_id: id,
              response_ms: elapsed(startedAt),
              payload_bytes: byteLength(raw),
              status: Number(response.status || 0),
              network_requests: 1,
            });
            if (!response.ok) {
              let message = "";
              try { message = String(JSON.parse(raw)?.error || ""); } catch (_error) { message = ""; }
              const error = new Error(message || `HTTP ${response.status}`);
              error.status = response.status;
              throw error;
            }
            const subject = JSON.parse(raw);
            if (!subjectMatchesId(id, subject)) {
              throw new Error(`Canonical subject identity did not match requested target ${id}.`);
            }
            return subject;
          })
          .finally(() => {
            entry.settled = true;
            if (pending.get(path) === entry) pending.delete(path);
          });
        pending.set(path, entry);
      }
      return subscribe(entry, signal, pending);
    }

    return Object.freeze({get});
  }

  async function load(selection, options = {}) {
    const url = urlFor(selection);
    const signal = options.signal;
    if (signal?.aborted) return Promise.reject(abortError());
    let entry = pendingRequests.get(url);
    if (!entry) {
      const controller = new AbortController();
      entry = {url, controller, subscribers: 0, settled: false, promise: null};
      entry.promise = fetchProjection(url, controller.signal, options)
        .finally(() => {
          entry.settled = true;
          if (pendingRequests.get(url) === entry) pendingRequests.delete(url);
        });
      pendingRequests.set(url, entry);
    }
    return subscribe(entry, signal);
  }

  async function fetchProjection(url, signal, options) {
    const fetcher = options.fetcher || root.fetch?.bind(root);
    if (typeof fetcher !== "function") throw new Error("Narrative Explorer is unavailable in this browser.");
    const resolveUrl = options.resolveUrl || resolveBackendUrl;
    const resolvedUrl = resolveUrl(url);
    const startedAt = now();
    const response = await fetcher(resolvedUrl, {
      signal,
      cache: "no-store",
      headers: {Accept: "application/json"},
    });
    const raw = await response.text();
    const responseMs = elapsed(startedAt);
    const payloadBytes = byteLength(raw);
    if (!response.ok) {
      let apiError = "";
      try {
        apiError = String(JSON.parse(raw)?.error || "");
      } catch (_error) {
        apiError = "";
      }
      const error = new Error(apiError || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    const parseStartedAt = now();
    const projection = JSON.parse(raw);
    const parseMs = elapsed(parseStartedAt);
    validateEnvelope(projection);
    dispatchMetric({
      phase: "response",
      passage: projection.passage?.reference || "",
      request_url: url,
      response_ms: responseMs,
      projection_parse_ms: parseMs,
      payload_bytes: payloadBytes,
      network_requests: 1,
    });
    return projection;
  }

  function resolveBackendUrl(url) {
    if (typeof root.BHFApi?.resolveUrl === "function") return root.BHFApi.resolveUrl(url);
    if (typeof root.BHFBackendRouting?.resolveUrl === "function") {
      return root.BHFBackendRouting.resolveUrl(url, root.BHFRuntimeConfig || {});
    }
    if (String(root.BHFRuntimeConfig?.backendMode || "same-origin") === "remote") {
      throw new Error("BHF backend is not configured for this deployment.");
    }
    return url;
  }

  function validateEnvelope(value) {
    if (!value || typeof value !== "object" || value.schema_version !== "1.0") {
      throw new Error("Narrative Explorer returned an unsupported response.");
    }
    for (const key of ["passage", "coverage", "sections", "items", "connections", "navigation"]) {
      if (key === "passage" ? !value[key] || typeof value[key] !== "object" : !Array.isArray(value[key])) {
        throw new Error("Narrative Explorer returned an incomplete response.");
      }
    }
  }

  function subscribe(entry, signal, requestMap = pendingRequests) {
    entry.subscribers += 1;
    return new Promise((resolve, reject) => {
      let complete = false;
      const finish = (aborted) => {
        if (complete) return false;
        complete = true;
        signal?.removeEventListener?.("abort", onAbort);
        entry.subscribers = Math.max(0, entry.subscribers - 1);
        if (aborted && entry.subscribers === 0 && !entry.settled) {
          if (requestMap.get(entry.url) === entry) requestMap.delete(entry.url);
          entry.controller.abort();
        }
        return true;
      };
      const onAbort = () => {
        finish(true);
        reject(abortError());
      };
      if (signal?.aborted) {
        onAbort();
        return;
      }
      signal?.addEventListener?.("abort", onAbort, {once: true});
      entry.promise.then((value) => {
        if (finish(false)) resolve(value);
      }, (error) => {
        if (finish(false)) reject(error);
      });
    });
  }

  function abortError() {
    const error = new Error("The Narrative Explorer request was cancelled.");
    error.name = "AbortError";
    return error;
  }

  function createSession(options = {}) {
    const enabled = options.enabled === true;
    const fetchProjection = options.fetchProjection || load;
    const onlineTarget = options.eventTarget || root.window;
    let sequence = 0;
    let controller = null;
    let activeKey = "";
    let activePromise = null;
    let activeSelection = null;
    let open = false;
    let lastResult = null;

    async function openPassage(selection, behavior = {}) {
      if (!enabled) return {status: "disabled"};
      const key = urlFor(selection);
      if (open && key === activeKey && activePromise && !behavior.force) return activePromise;
      if (open && key === activeKey && lastResult?.status === "ready" && !behavior.force) return lastResult;

      const requestSequence = ++sequence;
      controller?.abort();
      controller = new AbortController();
      activeKey = key;
      activeSelection = {...selection};
      open = true;
      lastResult = null;
      options.onLoading?.(activeSelection);
      const requestController = controller;
      const pending = Promise.resolve()
        .then(() => fetchProjection(activeSelection, {signal: requestController.signal}))
        .then((projection) => {
          if (requestSequence !== sequence || requestController.signal.aborted) return {status: "stale"};
          options.onReady?.(projection, activeSelection);
          lastResult = {status: "ready", projection};
          return lastResult;
        })
        .catch((error) => {
          if (requestSequence !== sequence || requestController.signal.aborted || error?.name === "AbortError") {
            return {status: "stale"};
          }
          const state = classifyError(error);
          options.onError?.(state, error, activeSelection);
          lastResult = {status: "error", state, error};
          return lastResult;
        })
        .finally(() => {
          if (requestSequence === sequence) activePromise = null;
        });
      activePromise = pending;
      return pending;
    }

    function close() {
      sequence += 1;
      open = false;
      activeKey = "";
      activePromise = null;
      activeSelection = null;
      lastResult = null;
      controller?.abort();
      controller = null;
    }

    function retry() {
      if (!open || !activeSelection) return Promise.resolve({status: "stale"});
      return openPassage(activeSelection, {force: true});
    }

    function handleOnline() {
      if (open && lastResult?.status === "error" && lastResult.state === "offline") {
        void retry();
      }
    }
    onlineTarget?.addEventListener?.("online", handleOnline);

    return Object.freeze({
      open: openPassage,
      close,
      retry,
      isOpen: () => open,
      currentKey: () => activeKey,
    });
  }

  function classifyError(error) {
    if (error?.name === "AbortError") return "cancelled";
    if (root.navigator?.onLine === false || error instanceof TypeError) return "offline";
    return "failed";
  }

  function renderOverview(projection, options = {}) {
    const document = options.document || root.document;
    if (!document) throw new Error("A document is required to render Narrative Explorer.");
    const rootElement = element(document, "div", "narrative-explorer");
    rootElement.dataset.narrativeExplorer = "";

    const view = normalizeNarrativeView(options.view);
    const passage = readerText(projection?.passage?.reference);
    const definition = view.kind === "category" ? SECTIONS.find((entry) => entry.id === view.categoryId) : null;
    const header = element(document, "header", `narrative-explorer-header${definition ? " is-focused" : ""}`);
    const heading = appendTextElement(document, header, "h3", definition?.title || "Explore this passage");
    heading.setAttribute("tabindex", "-1");
    heading.dataset.narrativePrimary = "true";
    appendTextElement(document, header, "p", definition?.description
      || "Choose a topic to explore records linked to the selected Scripture passage.");
    if (passage) appendTextElement(document, header, "p", `Current passage: ${passage}`, "narrative-explorer-passage");
    rootElement.append(header);

    if (trailNodes(options.trail).length > 1) rootElement.append(renderTrailHeader(options.trail, options));
    const itemsById = new Map((Array.isArray(projection?.items) ? projection.items : []).map((item) => [item.id, item]));
    const connectionsByItem = groupConnections(projection?.connections);
    const sectionsById = new Map((Array.isArray(projection?.sections) ? projection.sections : []).map((section) => [section.id, section]));
    const coverageBySource = new Map((Array.isArray(projection?.coverage) ? projection.coverage : []).map((entry) => [entry.source_domain, entry]));

    if (view.kind === "overview" || !definition) {
      const intro = element(document, "section", "narrative-explorer-discovery");
      appendTextElement(document, intro, "h4", "Follow a Connection");
      appendTextElement(document, intro, "p", "Explore passage relationships recorded in CKL or documented through CKL evidence. Similarity alone is not a verified connection.");
      const related = projection?.related_passages || {};
      const routeState = routeAvailabilityState(related);
      intro.append(renderAvailability(document, routeState, categoryAvailabilityLabel(routeState), routeCountLabel(related, routeState)));
      const follow = element(document, "button", "narrative-explorer-follow-connection");
      follow.type = "button";
      follow.textContent = "Follow a Connection";
      follow.setAttribute("aria-label", passage ? `Follow a Connection from ${passage}` : "Follow a Connection");
      follow.addEventListener("click", (event) => options.onOpenCategory?.("themes_biblical_connections", event.currentTarget || follow));
      intro.append(follow);
      rootElement.append(intro);

      const choices = element(document, "section", "narrative-explorer-topic-choices");
      choices.setAttribute("aria-labelledby", "narrative-explorer-topics-title");
      const choicesHeading = appendTextElement(document, choices, "h4", "Explore by Topic");
      choicesHeading.id = "narrative-explorer-topics-title";
      const cards = element(document, "div", "narrative-explorer-sections");
      SECTIONS.forEach((category) => {
        const section = sectionsById.get(category.id) || {state: "unknown", item_ids: []};
        const state = normalizeState(section.state);
        const itemIds = Array.isArray(section.item_ids) ? section.item_ids : [];
        const card = element(document, "button", "narrative-explorer-category-card");
        card.type = "button";
        card.dataset.sectionId = category.id;
        const icon = renderCategoryIcon(document, category.id);
        const text = element(document, "span", "narrative-explorer-category-copy");
        appendTextElement(document, text, "span", category.title, "narrative-explorer-category-title");
        appendTextElement(document, text, "span", categoryCardDescription(category.id), "narrative-explorer-category-description");
        appendTextElement(document, text, "span", categoryAvailabilityLabel(state), `narrative-explorer-category-availability is-${state}`);
        if (state === "available" || state === "partial") {
          appendTextElement(document, text, "span", state === "partial"
            ? `${itemIds.length} linked record${itemIds.length === 1 ? "" : "s"} in incomplete results`
            : `${itemIds.length} linked record${itemIds.length === 1 ? "" : "s"}`, "narrative-explorer-category-count");
        }
        card.append(icon, text);
        card.addEventListener("click", (event) => options.onOpenCategory?.(category.id, event.currentTarget || card));
        cards.append(card);
      });
      choices.append(cards);
      rootElement.append(choices);
      return rootElement;
    }

    const back = element(document, "button", "secondary narrative-explorer-back-topics");
    back.type = "button";
    back.textContent = "Back to topics";
    back.addEventListener("click", (event) => options.onBackToOverview?.(event.currentTarget || back));
    const returnToPassage = element(document, "button", "secondary narrative-explorer-return-passage");
    returnToPassage.type = "button";
    returnToPassage.textContent = `Return to ${readerText(options.trail?.originSelection?.reference) || passage || "passage"}`;
    returnToPassage.addEventListener("click", (event) => options.onReturnToOrigin?.(event.currentTarget || returnToPassage));
    const controls = element(document, "nav", "narrative-explorer-category-controls");
    controls.setAttribute("aria-label", "Passage topic navigation");
    controls.append(back, returnToPassage);
    rootElement.append(controls);

    const section = sectionsById.get(definition.id) || {id: definition.id, state: "unknown", item_ids: [], source_domains: []};
    const items = (Array.isArray(section.item_ids) ? section.item_ids : []).map((id) => itemsById.get(id)).filter(Boolean);
    let hasConnectionPreview = false;
    if (definition.id === "themes_biblical_connections") {
      rootElement.append(renderRelatedPassages(document, passage, projection?.related_passages, options));
      const candidates = selectConnectionPreviews(connectionPreviewCandidates(
        [...itemsById.values()], connectionsByItem, sectionsById,
      ));
      hasConnectionPreview = candidates.length > 0;
      rootElement.append(renderConnectionDiscovery(
        document, passage, [...itemsById.values()], connectionsByItem, coverageBySource, sectionsById, options,
      ));
    }
    rootElement.append(renderSection(document, definition, section, items, coverageBySource, connectionsByItem, options, {
      focused: true,
      hidePreviews: definition.id === "themes_biblical_connections" && hasConnectionPreview,
    }));
    return rootElement;
  }

  function normalizeNarrativeView(value) {
    const categoryId = typeof value?.categoryId === "string" ? value.categoryId : "";
    return value?.kind === "category" && SECTIONS.some((section) => section.id === categoryId)
      ? {kind: "category", categoryId}
      : {kind: "overview"};
  }

  function categoryCardDescription(id) {
    return ({
      biblical_narrative: "Story, structure, and literary observations.",
      archaeology_ancient_history: "Material finds and ancient historical sources.",
      biblical_geography: "Physical places, regions, and routes.",
      divine_council_cosmic_geography: "Source-based readings of sacred and cosmic space.",
      themes_biblical_connections: "Themes and documented passage relationships.",
      people_events_relationships: "People and events linked in the sources.",
    })[id] || "Explore records linked to this passage.";
  }

  function categoryAvailabilityLabel(state) {
    return ({
      available: "Source lookup complete",
      partial: "Some results may be missing",
      not_represented: "No linked records returned",
      unknown: "Availability could not be checked",
    })[state] || "Availability could not be checked";
  }

  function routeAvailabilityState(related) {
    const state = normalizeState(related?.state);
    const queryStatus = readerText(related?.query_status);
    if (state === "available" && queryStatus !== "complete") return queryStatus === "partial" ? "partial" : "unknown";
    if (state === "not_represented" && queryStatus !== "complete") return "unknown";
    return state;
  }

  function routeCountLabel(related, state = routeAvailabilityState(related)) {
    if (state !== "available" && state !== "partial") return "";
    if (state === "partial" && related?.query_status !== "partial") return "";
    const count = (Array.isArray(related?.authored_relationships) ? related.authored_relationships.length : 0)
      + (Array.isArray(related?.evidence_backed_bridges) ? related.evidence_backed_bridges.length : 0);
    return `${count} documented passage connection${count === 1 ? "" : "s"}${state === "partial" ? " in incomplete results" : ""}`;
  }

  function renderAvailability(document, stateValue, label, countLabel = "") {
    const state = normalizeState(stateValue);
    const status = element(document, "div", "narrative-explorer-connection-status");
    appendTextElement(document, status, "span", label, `narrative-explorer-availability is-${state}`);
    if (countLabel) appendTextElement(document, status, "span", countLabel, "narrative-explorer-category-count");
    return status;
  }

  function renderCategoryIcon(document, categoryId) {
    const paths = {
      biblical_narrative: "M4 5h16M4 10h16M4 15h10M4 20h8",
      archaeology_ancient_history: "M4 19h16M6 16l2-7 4 2 3-7 3 12",
      biblical_geography: "M4 6l5-2 6 3 5-2v13l-5 2-6-3-5 2zM9 4v13m6-10v13",
      divine_council_cosmic_geography: "M12 3l2.2 5.3L20 10l-5.8 1.7L12 17l-2.2-5.3L4 10l5.8-1.7zM19 16v5m-2.5-2.5h5",
      themes_biblical_connections: "M9 12a4 4 0 0 1 0-5.7l2-2a4 4 0 0 1 5.7 5.7l-1.2 1.2M15 12a4 4 0 0 1 0 5.7l-2 2a4 4 0 0 1-5.7-5.7l1.2-1.2M8 16l8-8",
      people_events_relationships: "M16 20v-1.5a4.5 4.5 0 0 0-4.5-4.5h-3A4.5 4.5 0 0 0 4 18.5V20m6-9a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7m7-6a3 3 0 0 1 0 6m2 2a4 4 0 0 1 3 4v1",
    }[categoryId] || "M4 12h16M12 4v16";
    const icon = document.createElementNS?.("http://www.w3.org/2000/svg", "svg") || document.createElement("span");
    icon.setAttribute("viewBox", "0 0 24 24");
    icon.setAttribute("aria-hidden", "true");
    icon.setAttribute("focusable", "false");
    icon.setAttribute("class", "narrative-explorer-category-icon");
    const path = document.createElementNS?.("http://www.w3.org/2000/svg", "path") || document.createElement("span");
    path.setAttribute("d", paths);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "1.7");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    icon.append(path);
    return icon;
  }

  function renderRelatedPassages(document, passage, related, options) {
    const section = element(document, "section", "narrative-explorer-related-passages");
    section.setAttribute("aria-labelledby", "narrative-explorer-related-passages-title");
    const heading = appendTextElement(document, section, "h4", "Related Biblical Passages");
    heading.id = "narrative-explorer-related-passages-title";
    const routes = related && typeof related === "object" ? related : {};
    const state = normalizeState(routes.state);
    section.dataset.coverageState = state;
    appendTextElement(document, section, "p", readerText(routes.description)
      || `Passage route coverage for ${readerText(passage) || "the selected passage"} is unknown.`,
    state === "partial" || state === "unknown" ? "narrative-explorer-missing-provenance" : "narrative-explorer-section-heading");

    const authored = Array.isArray(routes.authored_relationships) ? routes.authored_relationships : [];
    const bridges = Array.isArray(routes.evidence_backed_bridges) ? routes.evidence_backed_bridges : [];
    if (authored.length) {
      appendTextElement(document, section, "h5", "Existing authored CKL relationships");
      appendTextElement(document, section, "p", "These routes retain relationships explicitly recorded in CKL and their reviewed classifications.", "narrative-explorer-section-heading");
      renderPassageRouteList(document, section, authored, "authored", options);
    }
    if (bridges.length) {
      appendTextElement(document, section, "h5", "CKL-documented passage routes");
      appendTextElement(document, section, "p", "These routes come from exact CKL claims, evidence items, or interpretive notes. They are not authored CKL relationship edges; human scholarly approval is not recorded.", "narrative-explorer-section-heading");
      renderPassageRouteList(document, section, bridges, "bridge", options);
    }
    if (!authored.length && !bridges.length && state === "available") {
      appendTextElement(document, section, "p", "No verified route is available in this response; route coverage may be incomplete.", "narrative-explorer-missing-provenance");
    }
    return section;
  }

  function renderPassageRouteList(document, parent, routes, routeKind, options) {
    const list = element(document, "div", "narrative-explorer-related-passage-list");
    const pageSize = 4;
    const selectedRouteId = String(options.selectedRouteId || "");
    let visible = 0;
    let moreButton = null;
    const currentReference = normalizeReference(trailCurrentSelection(options.trail)?.reference || "");
    const addPage = () => {
      const next = Math.min(routes.length, visible + pageSize);
      routes.slice(visible, next).forEach((route) => {
        const article = element(document, "article", "narrative-explorer-related-passage");
        const isSelected = Boolean(selectedRouteId) && route.id === selectedRouteId;
        article.dataset.routeId = readerText(route.id);
        if (isSelected) {
          article.className += " is-selected";
          article.setAttribute("aria-current", "true");
        }
        const routeHeading = appendTextElement(
          document,
          article,
          "h6",
          `Connection to ${readerText(route.destination_passage)}`,
          "narrative-explorer-related-passage-heading",
        );
        routeHeading.setAttribute("tabindex", "-1");
        routeHeading.dataset.narrativeRouteFocusId = readerText(route.id);
        if (isSelected) {
          const status = appendTextElement(document, article, "p", "Selected connection from Study Companion.", "narrative-explorer-related-passage-selected");
          status.setAttribute("role", "status");
        }
        const layer = passageEvidenceLayerLabel(route.evidence_layer);
        const category = connectionCategoryLabel(route.relationship_category) || readerText(route.relationship_category).replace(/_/g, " ");
        const labels = [...new Set([layer, category].filter(Boolean).map((value) => value.trim()))];
        appendTextElement(document, article, "p", labels.join(" · "), "narrative-explorer-related-passage-kind");
        if (route.direction === "source_to_receiving_text"
          && readerText(route.source_text_passage)
          && readerText(route.receiving_text_passage)) {
          appendTextElement(
            document,
            article,
            "p",
            `Textual direction: ${readerText(route.source_text_passage)} → ${readerText(route.receiving_text_passage)}. This route can be followed from either passage.`,
            "narrative-explorer-related-passage-direction",
          );
        }
        const destination = validateScriptureReference(route.destination_passage, options.knownBooks || []);
        const inCurrent = destination.valid && currentReference === normalizeReference(destination.reference);
        const inTrail = destination.valid && passageIsInTrail(options.trail, normalizeReference(destination.reference));
        const hopsAtLimit = currentRelationshipHops(options.trail) >= MAX_RELATIONSHIP_HOPS;
        if (inCurrent) {
          appendTextElement(document, article, "p", `Current passage: ${destination.reference}`, "narrative-explorer-current-passage");
        } else if (inTrail) {
          appendTextElement(document, article, "p", `This passage already appears in the trail: ${destination.reference}`, "narrative-explorer-trail-cycle");
        } else if (hopsAtLimit) {
          appendTextElement(document, article, "p", `This connection trail has reached its ${MAX_RELATIONSHIP_HOPS}-link limit.`, "narrative-explorer-trail-limit");
        } else if (!destination.valid) {
          appendTextElement(document, article, "p", `Passage navigation unavailable: ${destination.reason}`, "narrative-explorer-missing-provenance");
        } else if (typeof options.onOpenPassage === "function") {
          appendActionButton(
            document,
            article,
            `Open related passage: ${destination.reference}`,
            `related-passage:${readerText(route.id)}`,
            (button) => options.onOpenPassage(destination, relationshipSnapshot({
              ...route,
              connection_type: route.relationship_category,
              basis: {kind: routeKind === "authored" ? route.basis?.kind : "ckl_documented_passage_bridge", notes: route.explanation},
            }), button),
          );
        }
        appendTextElement(document, article, "p", readerText(route.explanation), "narrative-explorer-related-passage-explanation");
        appendPassageRouteDetails(document, article, route, routeKind);
        list.append(article);
      });
      visible = next;
      if (moreButton) {
        const remaining = routes.length - visible;
        moreButton.hidden = remaining <= 0;
        moreButton.textContent = `Show ${Math.min(pageSize, remaining)} more passages`;
      }
    };
    addPage();
    if (routes.length > pageSize) {
      moreButton = element(document, "button", "secondary narrative-explorer-more-passages");
      moreButton.type = "button";
      moreButton.textContent = `Show ${Math.min(pageSize, routes.length - visible)} more passages`;
      moreButton.addEventListener("click", addPage);
      const selectedIndex = routes.findIndex((route) => route.id === selectedRouteId);
      while (selectedIndex >= visible) addPage();
      parent.append(list, moreButton);
    } else {
      parent.append(list);
    }
  }

  function appendPassageRouteDetails(document, parent, route, routeKind) {
    const details = element(document, "details", "narrative-explorer-related-passage-details");
    appendTextElement(document, details, "summary", routeKind === "authored" ? "Inspect CKL relationship and sources" : "Inspect CKL records and sources");
    appendTextElement(document, details, "p", `Provenance: ${routeKind === "authored" ? "authored CKL relationship" : "CKL-documented interpretation; not an authored relationship"}.`, "narrative-explorer-related-passage-provenance");
    appendTextElement(document, details, "p", `Relationship category: ${connectionCategoryLabel(route.relationship_category) || readerText(route.relationship_category)}.`);
    if (routeKind === "authored") {
      appendTextElement(document, details, "p", `Original CKL relationship: ${readerText(route.source_id)} → ${readerText(route.target_id)} · ${readerText(route.direction)} · ${readerText(route.relationship_mode)} · ${readerText(route.temporal_layer)}.`);
      if (route.original_relationship_type) appendTextElement(document, details, "p", `Original relationship type: ${readerText(route.original_relationship_type)}.`);
      const sources = Array.isArray(route.supporting_ckl_sources) ? route.supporting_ckl_sources : [];
      appendTextElement(document, details, "p", `Supporting CKL record IDs: ${(route.supporting_record_ids || []).join("; ") || "not recorded"}.`);
      appendTextElement(document, details, "p", `Supporting CKL source IDs: ${sources.map((source) => `${readerText(source.object_id)}:${readerText(source.source_id)}`).join("; ") || "not recorded"}.`);
      appendTextElement(document, details, "p", `Curation explanation: ${readerText(route.curation?.why || route.explanation) || "not recorded"}`);
    } else {
      appendTextElement(document, details, "p", "Human scholarly approval: not recorded.", "narrative-explorer-related-passage-approval");
      (Array.isArray(route.supporting_records) ? route.supporting_records : []).forEach((record) => {
        const identity = readerText(record.id) || `${readerText(record.object_id)} · ${readerText(record.record_locator) || "record ID unavailable"}`;
        appendTextElement(document, details, "h6", `CKL ${readerText(record.record_kind)}: ${identity}`);
        if (record.identity_status === "no_standalone_id") {
          appendTextElement(document, details, "p", "This CKL interpretive note has no standalone record ID; its content hash identifies the recorded note.");
        }
        if (readerText(record.statement)) appendTextElement(document, details, "p", readerText(record.statement), "narrative-explorer-original-claim");
        if (record.certainty) appendTextElement(document, details, "p", `Recorded certainty: ${readerText(record.certainty)}.`);
        if (record.dispute_status) appendTextElement(document, details, "p", `Recorded dispute status: ${readerText(record.dispute_status)}.`);
        appendTextElement(document, details, "p", `Record-attached source IDs: ${(record.source_ids || []).join("; ") || "not recorded"}.`);
      });
      appendBibliography(document, details, route.supporting_sources, (route.supporting_sources || []).map((source) => source.id));
    }
    appendTextElement(document, details, "p", `Interpretive uncertainty: ${readerText(route.uncertainty)}`, "narrative-explorer-caution");
    parent.append(details);
  }

  function passageEvidenceLayerLabel(value) {
    const labels = {
      direct_textual_relationship: "Direct textual relationship",
      thematic_interpretation: "Thematic interpretation",
      later_reception: "Later canonical reception",
      historical_background: "Historical background",
      ancient_comparative_evidence: "Ancient comparative evidence",
      textual_critical_evidence: "Textual-critical evidence",
      lexical_comparison: "Lexical comparison",
      literary_parallel: "Literary parallel",
    };
    return labels[readerText(value)] || "Documented passage comparison";
  }

  function renderConnectionDiscovery(document, passage, items, connectionsByItem, coverageBySource, sectionsById, options) {
    const section = element(document, "section", "narrative-explorer-connection-discovery");
    section.setAttribute("aria-labelledby", "narrative-explorer-connection-discovery-title");
    const heading = appendTextElement(document, section, "h4", `Evidence about ${readerText(passage) || "the selected passage"}`);
    heading.id = "narrative-explorer-connection-discovery-title";
    appendTextElement(
      document,
      section,
      "p",
      "A Scripture reference shows where evidence applies. It doesn't automatically mean two passages are connected. Historical comparisons offer context, but do not by themselves show borrowing or direct dependence.",
      "narrative-explorer-section-heading",
    );

    const candidates = connectionPreviewCandidates(items, connectionsByItem, sectionsById);
    const previewItems = selectConnectionPreviews(candidates);
    const coverage = coverageBySource.get("canonical_knowledge_library");
    if (previewItems.length) {
      if (coverage?.state === "partial") {
        appendTextElement(document, section, "p", "Some linked source records may not be available in this preview.", "narrative-explorer-missing-provenance");
      } else if (!coverage || coverage.state === "unknown" || coverage.query_status !== "complete") {
        appendTextElement(document, section, "p", "The source lookup did not finish; these previews may be incomplete.", "narrative-explorer-missing-provenance");
      }
      const previews = element(document, "div", "narrative-explorer-previews");
      previewItems.forEach((candidate) => {
        previews.append(renderItem(
          document,
          candidate.item,
          connectionsByItem.get(candidate.item.id) || [],
          options,
          candidate,
        ));
      });
      section.append(previews);
      return section;
    }

    if (!coverage || coverage.state === "unknown" || (coverage.state !== "partial" && coverage.query_status !== "complete")) {
      appendTextElement(document, section, "p", "Evidence previews are unavailable because the source lookup did not finish.", "narrative-explorer-missing-provenance");
    } else if (coverage.state === "partial") {
      appendTextElement(document, section, "p", "No source-linked previews are available among the returned records.", "narrative-explorer-missing-provenance");
    } else {
      appendTextElement(document, section, "p", "No evidence preview with a source explanation is available for this passage.", "narrative-explorer-missing-provenance");
    }
    return section;
  }

  function connectionPreviewCandidates(items, connectionsByItem, sectionsById) {
    const focusedItemIds = new Set([...sectionsById.values()]
      .filter((section) => section.id !== "themes_biblical_connections")
      .flatMap((section) => Array.isArray(section.item_ids) ? section.item_ids : []));
    const geographyItemIds = new Set(sectionsById.get("biblical_geography")?.item_ids || []);
    return items.flatMap((item) => {
      if (readerText(item?.record_kind) !== "evidence") return [];
      const hasSourceIdentity = (Array.isArray(item.source_ids) && item.source_ids.some((sourceId) => readerText(sourceId)))
        || (Array.isArray(item.sources) && item.sources.some((source) => readerText(source?.id)));
      if (!hasSourceIdentity) return [];
      const anchors = Array.isArray(item.applicable_passage_anchors) && item.applicable_passage_anchors.length
        ? item.applicable_passage_anchors
        : (Array.isArray(item.passage_anchors) ? item.passage_anchors : []);
      if (!anchors.length) return [];
      const evidenceEdges = (connectionsByItem.get(item.id) || [])
        .filter((edge) => edge.source_id === item.id
          && ["ckl_related_evidence", "ckl_related_object"].includes(readerText(edge?.basis?.kind))
          && readerText(edge?.basis?.notes));
      if (!evidenceEdges.length) return [];
      evidenceEdges.sort((left, right) => {
        const leftEvidence = left.basis.kind === "ckl_related_evidence" ? 0 : 1;
        const rightEvidence = right.basis.kind === "ckl_related_evidence" ? 0 : 1;
        return leftEvidence - rightEvidence || String(left.id || "").localeCompare(String(right.id || ""));
      });
      const anchor = anchors.find((entry) => readerText(entry.relationship).toLowerCase() === "comparative") || anchors[0];
      return [{item, edge: evidenceEdges[0], anchor, focused: focusedItemIds.has(item.id), geography: geographyItemIds.has(item.id)}];
    });
  }

  function selectConnectionPreviews(candidates) {
    const geography = candidates.filter((candidate) => candidate.geography);
    const focused = candidates.filter((candidate) => candidate.focused);
    const source = geography.length >= 2 ? geography : (focused.length >= 2 ? focused : candidates);
    const ranked = [...source].sort((left, right) => (
      connectionPreviewRank(left.item) - connectionPreviewRank(right.item)
      || String(left.item.id || "").localeCompare(String(right.item.id || ""))
    ));
    return ranked.slice(0, 2);
  }

  function connectionPreviewRank(item) {
    const label = readerEvidenceLabel(item).toLowerCase();
    if (label.startsWith("geography and place identification")) return 0;
    if (label === "manuscript/textual witness") return 0;
    if (label.startsWith("original biblical text")) return 1;
    if (label.startsWith("scholarly interpretation") && label.includes("disputed position")) return 2;
    if (label === "later reception") return 3;
    if (label === "ancient comparative literature") return 4;
    if (label.startsWith("scholarly interpretation")) return 5;
    return isDisputed(item) ? 6 : 7;
  }

  function renderSection(document, definition, section, items, coverageBySource, connectionsByItem, options, renderOptions = {}) {
    const card = element(document, "section", `narrative-explorer-section${renderOptions.focused ? " is-focused" : ""}`);
    card.dataset.sectionId = definition.id;
    const heading = element(document, "div", "narrative-explorer-section-heading");
    appendTextElement(document, heading, "h4", renderOptions.focused ? "Evidence linked to this passage" : definition.title);
    if (!renderOptions.focused) appendTextElement(document, heading, "p", definition.description);
    card.append(heading);
    if (definition.id === "divine_council_cosmic_geography") {
      appendTextElement(
        document,
        card,
        "p",
        "Comparative material describes an ancient cultural or literary context; it does not by itself prove borrowing, quotation, or dependence. Proposed symbolic readings remain interpretations, not archaeological findings.",
        "narrative-explorer-caution",
      );
    }

    const state = normalizeState(section.state);
    const stateLabel = {
      available: "Available",
      partial: "Some results may be missing",
      not_represented: "No linked records found",
      unknown: "Availability could not be checked",
    }[state];
    appendTextElement(document, card, "p", stateLabel, `narrative-explorer-availability is-${state}`);
    const recordCounts = countRecords(items, state);
    appendTextElement(document, card, "p", recordCounts, "narrative-explorer-counts");

    const sourceDomains = Array.isArray(section.source_domains) ? section.source_domains : [];
    if (sourceDomains.length) {
      const coverage = element(document, "ul", "narrative-explorer-coverage");
      sourceDomains.forEach((source) => {
        const item = element(document, "li");
        item.textContent = coverageLine(source, coverageBySource.get(source));
        coverage.append(item);
      });
      card.append(coverage);
    }
    if (state === "not_represented" && definition.id === "archaeology_ancient_history") {
      appendTextElement(document, card, "p", "No linked archaeology records were found; this does not disprove a biblical account.", "narrative-explorer-caution");
    }

    const previewList = element(document, "div", "narrative-explorer-previews");
    const fullList = element(document, "div", "narrative-explorer-record-list");
    fullList.hidden = true;
    const ordered = orderForPreview(items);
    const focusItem = ordered.find((item) => item.id === options.focusItemId);
    const previewItems = focusItem
      ? [focusItem, ...ordered.filter((item) => item.id !== focusItem.id).slice(0, 1)]
      : ordered.slice(0, 2);
    previewItems.forEach((item) => previewList.append(renderItem(document, item, connectionsByItem.get(item.id) || [], options)));
    if (!renderOptions.hidePreviews) card.append(previewList);
    card.append(fullList);

    const inspect = element(document, "button", "secondary narrative-explorer-inspect");
    inspect.type = "button";
    inspect.textContent = items.length ? `Browse all ${items.length} linked records` : "No records available";
    inspect.disabled = items.length === 0;
    inspect.setAttribute("aria-expanded", "false");
    if (items.length) {
      let next = 0;
      let expanded = false;
      let moreButton = null;
      const addNextPage = () => {
        const page = ordered.slice(next, next + PAGE_SIZE);
        page.forEach((item) => fullList.append(renderItem(document, item, connectionsByItem.get(item.id) || [], options)));
        next += page.length;
        if (moreButton) {
          moreButton.hidden = next >= ordered.length;
          moreButton.textContent = `Show ${Math.min(PAGE_SIZE, ordered.length - next)} more records`;
        }
      };
      inspect.addEventListener("click", () => {
        expanded = !expanded;
        inspect.setAttribute("aria-expanded", String(expanded));
        previewList.hidden = expanded;
        fullList.hidden = !expanded;
        inspect.textContent = expanded ? "Hide records" : `Browse all ${items.length} linked records`;
        if (expanded && next === 0) addNextPage();
      });
      moreButton = element(document, "button", "secondary narrative-explorer-more");
      moreButton.type = "button";
      moreButton.textContent = `Show ${Math.min(PAGE_SIZE, ordered.length)} more records`;
      moreButton.hidden = ordered.length <= PAGE_SIZE;
      moreButton.addEventListener("click", addNextPage);
      card.append(inspect, moreButton);
    } else {
      card.append(inspect);
    }
    return card;
  }

  function orderForPreview(items) {
    const preferred = items.filter((item) => item.record_kind !== "object");
    const source = preferred.length ? preferred : items;
    return [...source].sort((left, right) => String(left.id || "").localeCompare(String(right.id || "")));
  }

  function countRecords(items, state) {
    if (state === "unknown") return "No count is available because the source lookup did not finish.";
    if (state === "not_represented") return "No records were found for this passage.";
    const count = items.length;
    const label = `${count} linked ${count === 1 ? "record" : "records"}`;
    return state === "partial" ? `${label} in incomplete results.` : `${label}.`;
  }

  function coverageLine(sourceDomain, entry) {
    const label = SOURCE_LABELS[sourceDomain] || sourceDomain;
    if (!entry) return `${label}: availability could not be checked.`;
    if (entry.state === "available") {
      const count = Number(entry.query_returned_count);
      return `${label}: ${Number.isFinite(count) ? `${count} source record${count === 1 ? "" : "s"} found` : "records are available"}.`;
    }
    if (entry.state === "partial") {
      return `${label}: some results may be missing.`;
    }
    if (entry.state === "not_represented" && entry.query_status === "complete") {
      return `${label}: no records were found for this passage.`;
    }
    return `${label}: results could not be checked.`;
  }

  function renderItem(document, item, connections, options, connectionPreview = null) {
    const card = element(document, "article", "narrative-explorer-item");
    if (connectionPreview) card.dataset.narrativeConnectionPreview = "true";
    const title = readerText(item.title) || readerText(item.claim_text) || readerText(item.description) || readerText(item.id) || "Source record";
    appendTextElement(document, card, "h5", title);
    const evidenceLabel = readerEvidenceLabel(item);
    const cosmicRole = cosmicRoleLabel(item.cosmic_geography_role);
    const redundantCosmicRole = cosmicRole.toLowerCase().includes("interpretation")
      && evidenceLabel.toLowerCase().includes("interpretation");
    const visibleKind = cosmicRole && !redundantCosmicRole
      ? `${evidenceLabel} · ${cosmicRole}`
      : evidenceLabel;
    if (visibleKind) appendTextElement(document, card, "p", visibleKind, "narrative-explorer-item-kind");

    const authoredSentence = previewDescription(item, title);
    if (authoredSentence) appendTextElement(document, card, "p", authoredSentence, "narrative-explorer-item-copy");

    const basis = previewBasis(item, connectionPreview);
    if (basis.text) {
      appendTextElement(document, card, "p", `${basis.label}: ${basis.text}`, "narrative-explorer-preview-basis");
    } else {
      appendTextElement(document, card, "p", "Relevance basis not recorded.", "narrative-explorer-preview-basis");
    }
    if (connectionPreview?.edge?.curation?.uncertainty) {
      appendTextElement(
        document,
        card,
        "p",
        `Interpretive uncertainty: ${readerText(connectionPreview.edge.curation.uncertainty)}`,
        "narrative-explorer-item-qualification narrative-explorer-caution",
      );
    }
    if (connectionPreview?.edge?.curation?.supporting_passages?.length) {
      appendTextElement(
        document,
        card,
        "p",
        `Supporting Scripture passages: ${connectionPreview.edge.curation.supporting_passages.map(readerText).filter(Boolean).join(" · ")}.`,
        "narrative-explorer-curation-support",
      );
      appendCurationPassageNavigation(
        document,
        card,
        connectionPreview.edge.curation.supporting_passages,
        options.trail,
        options,
        connectionPreview.edge,
      );
    }
    if (connectionPreview?.edge?.curation?.supporting_comparative_material?.length) {
      const materials = connectionPreview.edge.curation.supporting_comparative_material
        .map((material) => `${readerText(material.reference)}${material.label ? ` (${readerText(material.label)})` : ""}`)
        .filter(Boolean);
      if (materials.length) appendTextElement(document, card, "p", `Ancient comparative material (not Scripture): ${materials.join(" · ")}.`, "narrative-explorer-curation-comparative");
    }
    const qualification = previewQualification(item, evidenceLabel);
    if (qualification) appendTextElement(document, card, "p", qualification, "narrative-explorer-item-qualification");

    const provenance = element(document, "details", "narrative-explorer-provenance");
    appendTextElement(document, provenance, "summary", "Full evidence and source details");
    appendFullEvidenceDetails(document, provenance, item);
    const metadataConnections = connectionPreview
      ? [connectionPreview.edge, ...connections.filter((edge) => edge !== connectionPreview.edge)]
      : connections;
    const metadata = provenanceLines(item, metadataConnections);
    if (metadata.length) {
      const list = element(document, "ul");
      metadata.forEach((line) => {
        const entry = element(document, "li");
        setFormattedText(document, entry, line);
        list.append(entry);
      });
      provenance.append(list);
    }
    card.append(provenance);

    if (typeof options.onInspect === "function") {
      const inspect = element(document, "button", "secondary narrative-explorer-item-inspect");
      inspect.type = "button";
      inspect.textContent = "Explore this evidence";
      inspect.dataset.narrativeItemId = readerText(item.id);
      inspect.dataset.narrativeFocusId = `item:${readerText(item.id)}`;
      inspect.addEventListener("click", () => options.onInspect(item, inspect));
      card.append(inspect);
    }
    const action = supportedAction(item);
    if (action && item?.navigation?.kind !== "canonical_object" && typeof options.onNavigate === "function") {
      const button = element(document, "button", "secondary narrative-explorer-item-action");
      button.type = "button";
      button.textContent = action.label;
      if (action.ariaLabel) button.setAttribute("aria-label", action.ariaLabel.replace("{title}", title));
      button.addEventListener("click", () => options.onNavigate(item, action, button));
      card.append(button);
    }
    return card;
  }

  function previewDescription(item, title) {
    const candidates = [item?.description, item?.claim_text, item?.rationale?.primary_observation, item?.rationale?.passage_relevance];
    for (const candidate of candidates) {
      const text = readerText(candidate);
      if (!text || text === title) continue;
      return conciseSourceText(text, 220);
    }
    return "";
  }

  function conciseSourceText(value, maxLength = 180) {
    const text = readerText(value);
    if (!text) return "";
    const sentenceEnd = text.search(/[.!?](?=\s|$)/);
    const sentence = sentenceEnd >= 0 ? text.slice(0, sentenceEnd + 1).trim() : text;
    if (sentence.length <= maxLength) return sentence;
    const limit = Math.max(1, maxLength - 1);
    const boundary = sentence.slice(0, limit).lastIndexOf(" ");
    const end = boundary >= Math.floor(limit * 0.6) ? boundary : limit;
    return `${sentence.slice(0, end).trimEnd()}…`;
  }

  function previewBasis(item, connectionPreview) {
    const curatedWhy = readerText(connectionPreview?.edge?.curation?.why);
    if (curatedWhy) return {label: "Why this connects", text: conciseSourceText(curatedWhy)};
    const recorded = readerText(connectionPreview?.edge?.basis?.notes);
    if (recorded) return {label: "Connection context", text: conciseSourceText(recorded)};
    const relevance = readerText(item?.rationale?.passage_relevance);
    if (relevance) return {label: "Why this evidence appears", text: conciseSourceText(relevance)};
    return {label: "", text: ""};
  }

  function previewQualification(item, evidenceLabel) {
    const temporalRelations = [item?.temporal_relation, ...(Array.isArray(item?.temporal_relations) ? item.temporal_relations : [])]
      .map((value) => readerText(value).toLowerCase().replace(/_/g, "-"));
    if (evidenceLabel === "Later reception" && temporalRelations.includes("contemporary")) {
      return "Later reception · This record is later than Genesis, but its time label needs review.";
    }
    if (!isDisputed(item)) return "";
    const dispute = readerText(item?.dispute_status).toLowerCase().replace(/-/g, "_");
    if (dispute === "textual_variant") {
      const subjectText = [item?.title, item?.claim_text, item?.description]
        .map((value) => readerText(value).toLowerCase()).join(" ");
      const rationaleText = Object.values(item?.rationale && typeof item.rationale === "object" ? item.rationale : {})
        .map((value) => readerText(value).toLowerCase()).join(" ");
      if (/deuteronomy 32:8/.test(subjectText) && /manuscript|textual tradition/.test(subjectText)
        && /earliest/.test(rationaleText)) {
        return "The manuscripts preserve different wording at Deuteronomy 32:8; which reading is earliest remains debated.";
      }
      return "Textual variant · wording and implications remain debated.";
    }
    if (dispute === "identification_uncertainty") return "Identification remains uncertain.";
    if (dispute === "major_scholarly_disagreement") return majorDisagreementQualification(item);
    if (dispute === "minor_scholarly_disagreement") return "Some details remain debated.";
    if (dispute === "interpretive_uncertainty") {
      const subjectText = [item?.title, item?.claim_text, item?.description]
        .map((value) => readerText(value).toLowerCase()).join(" ");
      const rationaleText = Object.values(item?.rationale && typeof item.rationale === "object" ? item.rationale : {})
        .map((value) => readerText(value).toLowerCase()).join(" ");
      if (/psalm 82/.test(subjectText) && /identity/.test(rationaleText)) {
        return "The identity of the figures addressed in Psalm 82 remains disputed.";
      }
      return "Interpretation remains disputed.";
    }
    return "Interpretation status is disputed.";
  }

  function majorDisagreementQualification(item) {
    const subjectText = [item?.title, item?.claim_text, item?.description]
      .map((value) => readerText(value).toLowerCase()).join(" ");
    const rationaleText = Object.values(item?.rationale && typeof item.rationale === "object" ? item.rationale : {})
      .map((value) => readerText(value).toLowerCase()).join(" ");
    const recordedText = `${subjectText} ${rationaleText}`;
    const evidenceLabel = readerEvidenceLabel(item);

    if (/sons of god/.test(subjectText) && /identity/.test(recordedText)) {
      return "Who the “sons of God” are and what the episode means remain disputed.";
    }
    if (evidenceLabel === "Ancient comparative literature" && /gilgamesh/.test(subjectText)
      && /transmission|relationship/.test(rationaleText)) {
      return "Scholars compare the flood motifs; how the traditions are related remains debated.";
    }
    if (evidenceLabel === "Ancient comparative literature" && /ugaritic/.test(subjectText)
      && /continuity|relationship/.test(rationaleText)) {
      return "Ugaritic parallels offer context; their relationship to biblical language remains uncertain.";
    }
    return "Some conclusions about this evidence remain unsettled.";
  }

  function appendFullEvidenceDetails(document, parent, item) {
    const original = element(document, "section", "narrative-explorer-original-evidence");
    const claim = readerText(item?.claim_text);
    const description = readerText(item?.description);
    if (claim) {
      appendTextElement(document, original, "h6", "Recorded claim");
      appendTextElement(document, original, "p", claim, "narrative-explorer-original-claim");
    }
    if (description && description !== claim) {
      appendTextElement(document, original, "h6", "Recorded description");
      appendTextElement(document, original, "p", description, "narrative-explorer-original-description");
    }
    if (original.children.length) parent.append(original);
    appendRationaleDetails(document, parent, item?.rationale);
  }

  function provenanceLines(item, connections) {
    const lines = [`Projected source identity: ${readerText(item.id) || "unavailable"}`];
    const subject = readerText(item.parent_object_id || item.object_id);
    if (subject) lines.push(`CKL subject: ${subject}`);
    if (readerText(item.domain) === "maps" && readerText(item.object_id || item.id)) {
      lines.push(`Original map/record ID: ${readerText(item.object_id || item.id)}`);
    }
    if (readerText(item.claim_id)) lines.push(`Claim ID: ${readerText(item.claim_id)}`);
    if (readerText(item.evidence_id)) lines.push(`Evidence ID: ${readerText(item.evidence_id)}`);
    if (readerText(item.evidence_category)) lines.push(`Evidence category: ${readerText(item.evidence_category)}`);
    if (readerText(item.claim_type)) lines.push(`Claim type: ${readerText(item.claim_type)}`);
    if (readerText(item.assertion_type)) lines.push(`Assertion type: ${readerText(item.assertion_type)}`);
    const originalRelationships = Array.isArray(item.original_relationship_types)
      ? item.original_relationship_types.map(readerText).filter(Boolean)
      : [];
    if (originalRelationships.length) {
      lines.push(`Original relationship types: ${[...new Set(originalRelationships)].join(", ")}`);
    }

    const anchors = Array.isArray(item.applicable_passage_anchors) && item.applicable_passage_anchors.length
      ? item.applicable_passage_anchors
      : (Array.isArray(item.passage_anchors) ? item.passage_anchors : []);
    const anchoredReferences = new Set();
    anchors.slice(0, 8).forEach((anchor) => {
      const reference = readerText(anchor.reference);
      if (reference) {
        anchoredReferences.add(reference);
        lines.push(`Passage relationship: ${reference}${anchor.relationship ? ` · ${readerText(anchor.relationship)}` : ""}`);
      }
    });
    (Array.isArray(item.related_passages) ? item.related_passages : []).slice(0, 8).forEach((reference) => {
      const text = readerText(reference);
      if (text && !anchoredReferences.has(text)) lines.push(`Related passage: ${text}`);
    });
    [
      ["Confidence", item.confidence],
      ["Certainty", item.certainty],
      ["Dispute status", item.dispute_status],
      ["Interpretation status", item.interpretation_state],
      ["Review status", item.review_status],
      ["Content status", item.content_status],
      ["Human review required", item.human_review_required],
      ["Temporal relation", item.temporal_relation],
      ["Geography kind", item.geography_kind],
      ["Physical identification status", item.physical_identification_status || item.source_metadata?.physical_identification_status || item.source_metadata?.place_identification_status || item.source_metadata?.identification_status],
      ["Place identification confidence", item.place_identification_confidence],
    ].forEach(([label, value]) => {
      const text = metadataText(value);
      if (text) lines.push(`${label}: ${text}`);
    });
    if (item.coordinates_displayable === false && item.geography_kind && PHYSICAL_GEOGRAPHY.has(item.geography_kind)) {
      if (readerText(item.coordinate_display_reason)) lines.push(`Map point withheld: ${readerText(item.coordinate_display_reason)}`);
      else lines.push("Map point withheld because the source does not establish a precise physical identification.");
    }
    if (item.geometry_displayable === false && item.geometry_display_reason && PHYSICAL_GEOGRAPHY.has(item.geography_kind)) {
      lines.push(`Route geometry withheld: ${readerText(item.geometry_display_reason)}`);
    }
    if (PHYSICAL_GEOGRAPHY.has(item.geography_kind)) {
      const sourceMetadata = item.source_metadata && typeof item.source_metadata === "object" ? item.source_metadata : {};
      [
        ["Ancient name", sourceMetadata.ancient_name || sourceMetadata.ancient_names],
        ["Modern name", sourceMetadata.modern_name || sourceMetadata.modern_names],
        ["Modern location", sourceMetadata.modern_location],
        ["Region", sourceMetadata.region || sourceMetadata.ancient_region],
        ["Territory", sourceMetadata.territory || sourceMetadata.territories],
        ["Historical period", sourceMetadata.historical_period || sourceMetadata.historical_periods || sourceMetadata.period || sourceMetadata.periods],
      ].forEach(([label, value]) => {
        const text = metadataText(value);
        if (text) lines.push(`${label}: ${text}`);
      });
    }
    if (item.rationale && Object.keys(item.rationale).length) {
      lines.push(`Recorded basis: ${compactObject(item.rationale)}`);
    }
    connections.slice(0, 4).forEach((edge) => {
      const relation = readerText(edge.connection_type || edge.original_relationship_type);
      if (relation) lines.push(`Connection: ${relation}${edge.original_relationship_type ? ` · original relationship ${readerText(edge.original_relationship_type)}` : ""}`);
      if (readerText(edge.relationship_mode)) lines.push(`Connection mode: ${readerText(edge.relationship_mode)}`);
      if (readerText(edge.direction)) lines.push(`Connection direction: ${readerText(edge.direction)}`);
      if (readerText(edge.temporal_layer)) lines.push(`Original CKL temporal layer: ${readerText(edge.temporal_layer)}`);
      if (edge.basis && Object.keys(edge.basis).length) lines.push(`Connection basis: ${compactObject(edge.basis)}`);
      const curation = edge.curation && typeof edge.curation === "object" ? edge.curation : null;
      if (curation?.why) lines.push(`Why this connection: ${readerText(curation.why)}`);
      if (curation?.textual_observation) lines.push(`Curated textual observation: ${readerText(curation.textual_observation)}`);
      if (curation?.supporting_passages?.length) lines.push(`Curated supporting passages: ${curation.supporting_passages.map(readerText).filter(Boolean).join(", ")}`);
      if (curation?.uncertainty) lines.push(`Curated interpretive uncertainty: ${readerText(curation.uncertainty)}`);
      if (curation?.classification) lines.push(`Curated classification: ${readerText(curation.classification)}`);
      if (curation?.curation_confidence) lines.push(`Curation confidence: ${readerText(curation.curation_confidence)}`);
      if (curation?.human_scholarly_approval) lines.push(`Human scholarly approval: ${readerText(curation.human_scholarly_approval)}`);
    });
    if (readerText(item.domain) === "maps") {
      const sourceMetadata = item.source_metadata && typeof item.source_metadata === "object" ? item.source_metadata : {};
      const nestedSource = sourceMetadata.source && typeof sourceMetadata.source === "object" ? sourceMetadata.source : {};
      const recordedSource = [
        ["Source", sourceMetadata.source_name || nestedSource.source_name || nestedSource.label || nestedSource.title],
        ["Source URL", sourceMetadata.source_url || nestedSource.source_url || nestedSource.url],
        ["License", sourceMetadata.license || nestedSource.license],
      ].map(([label, value]) => {
        const text = metadataText(value);
        return text ? `${label}: ${text}` : "";
      }).filter(Boolean);
      if (recordedSource.length) lines.push(`Recorded map provenance: ${recordedSource.join(" · ")}`);
    }
    (Array.isArray(item.sources) ? item.sources : []).slice(0, 12).forEach((source) => {
      const id = readerText(source.id);
      const bibliography = source.bibliographic_details || {};
      const title = readerText(bibliography.title);
      if (source.details_available && (id || title)) {
        const details = [title, readerText(bibliography.author), readerText(bibliography.publisher), metadataText(bibliography.year), readerText(bibliography.locator)].filter(Boolean).join(" · ");
        lines.push(`Source: ${details || id}${id && title ? ` · ${id}` : ""}`);
      } else if (id) {
        lines.push(`Source details not available in CKL: ${id}`);
      }
    });
    const sourceIds = Array.isArray(item.source_ids) ? item.source_ids.map(readerText).filter(Boolean) : [];
    const listedSources = new Set((Array.isArray(item.sources) ? item.sources : []).map((source) => readerText(source.id)).filter(Boolean));
    sourceIds.filter((id) => !listedSources.has(id)).slice(0, 12).forEach((id) => lines.push(`Source ID: ${id}`));
    return lines;
  }

  function cosmicRoleLabel(role) {
    return ({
      sacred_space_interpretation: "Sacred-space interpretation",
      sacred_space_guarding_context: "Sacred-space guarding context",
      divine_assembly_text: "Heavenly assembly language",
      divine_assembly_comparison: "Divine assembly comparison",
      ancient_cosmology_comparison: "Ancient cosmology comparison",
      disputed_divine_beings_interpretation: "Divine beings with disputed interpretation",
    })[readerText(role)] || "";
  }

  function supportedAction(item) {
    const navigation = item.navigation;
    const targetId = readerText(navigation?.target_id);
    if (!navigation || !targetId) return null;
    if (navigation.kind === "canonical_object") return {label: "Open CKL record"};
    if (navigation.kind === "archaeology_item") return {label: "Open archaeology record"};
    if (
      navigation.selection_required === true
      && ["map_place", "map_route", "map_record", "map_manuscript"].includes(navigation.kind)
      && PHYSICAL_GEOGRAPHY.has(item.geography_kind)
    ) {
      const canFocusPlace = item.coordinates_displayable === true;
      const canFocusRoute = item.geometry_displayable === true;
      const mapFocusAllowed = navigation.kind === "map_route" ? canFocusRoute : canFocusPlace;
      return {
        label: mapFocusAllowed
          ? "Open Maps Explorer and try to focus this item"
          : "Open general Maps Explorer",
        ariaLabel: mapFocusAllowed
          ? "Open Maps Explorer and try to select {title}"
          : "Open the general Maps Explorer for this passage",
        mapFocusAllowed,
      };
    }
    return null;
  }

  function groupConnections(connections) {
    const grouped = new Map();
    (Array.isArray(connections) ? connections : []).forEach((edge) => {
      for (const id of [edge.source_id, edge.target_id]) {
        if (!id) continue;
        const current = grouped.get(id) || [];
        current.push(edge);
        grouped.set(id, current);
      }
    });
    return grouped;
  }

  function renderTrailHeader(trail, options = {}) {
    const document = options.document || root.document;
    const header = element(document, "section", "narrative-explorer-trail-header");
    header.setAttribute("aria-label", "Evidence trail navigation");
    const nodes = trailNodes(trail);
    const currentIndex = nodes.length - 1;
    const navigation = element(document, "nav", "narrative-explorer-breadcrumbs");
    navigation.setAttribute("aria-label", "Evidence trail");
    const list = element(document, "ol", "narrative-explorer-breadcrumb-steps");
    nodes.forEach((node, index) => {
      if (index > 0 && node.relationship) list.append(renderTrailConnectionStep(document, node.relationship));
      const entry = element(document, "li", `narrative-explorer-trail-step is-${node.kind || "record"}`);
      const role = index === 0
        ? "Origin passage"
        : node.kind === "passage"
          ? "Related passage"
          : node.kind === "evidence"
            ? "Evidence record"
            : "Connected CKL subject";
      appendTextElement(document, entry, "span", role, "narrative-explorer-trail-step-kind");
      const label = appendTextElement(document, entry, "span", readerText(node.label || node.reference || node.id), "narrative-explorer-trail-step-label");
      if (index === currentIndex) label.setAttribute("aria-current", "page");
      list.append(entry);
    });
    navigation.append(list);
    header.append(navigation);

    const controls = element(document, "div", "narrative-explorer-trail-controls");
    if (currentIndex > 0 && typeof options.onBack === "function") {
      const back = element(document, "button", "secondary narrative-explorer-trail-back");
      back.type = "button";
      back.textContent = "Back to previous trail step";
      back.addEventListener("click", options.onBack);
      controls.append(back);
    }
    if (currentIndex > 0 && typeof options.onReturnToOrigin === "function") {
      const returnButton = element(document, "button", "secondary narrative-explorer-return-origin");
      returnButton.type = "button";
      returnButton.textContent = `Return to ${readerText(trail?.originSelection?.reference) || "original passage"}`;
      returnButton.addEventListener("click", options.onReturnToOrigin);
      controls.append(returnButton);
    }
    if (controls.children.length) header.append(controls);
    appendTextElement(
      document,
      header,
      "p",
      `Connection trail: ${currentRelationshipHops(trail)} of ${MAX_RELATIONSHIP_HOPS} links followed.`,
      "narrative-explorer-trail-depth",
    );
    const activeRelationship = activeTrailStep(trail)?.relationship;
    if (activeRelationship?.provenance) {
      const provenance = element(document, "section", "narrative-explorer-trail-relationship");
      appendTextElement(document, provenance, "h4", "Connection used to open this passage");
      const label = activeRelationship.provenance === "authored_ckl_relationship"
        ? "authored CKL relationship"
        : String(activeRelationship.provenance).replace(/^ckl_documented_/, "CKL-documented ").replace(/_/g, " ");
      appendTextElement(document, provenance, "p", `${label} · ${connectionCategoryLabel(activeRelationship.relationshipCategory) || activeRelationship.relationshipCategory || "relationship category not recorded"}.`);
      if (activeRelationship.sourcePassage || activeRelationship.destinationPassage) {
        appendTextElement(document, provenance, "p", `${activeRelationship.sourcePassage || "Source passage unavailable"} → ${activeRelationship.destinationPassage || "Destination passage unavailable"}.`);
      }
      if (activeRelationship.originalRelationshipType) {
        appendTextElement(document, provenance, "p", `Original relationship type: ${activeRelationship.originalRelationshipType}.`);
      }
      if (activeRelationship.direction) {
        appendTextElement(document, provenance, "p", `Recorded direction: ${activeRelationship.direction.replace(/_/g, " ")}.`);
      }
      if (activeRelationship.explanation) appendTextElement(document, provenance, "p", activeRelationship.explanation);
      if (activeRelationship.uncertainty) appendTextElement(document, provenance, "p", `Uncertainty: ${activeRelationship.uncertainty}`, "narrative-explorer-caution");
      if (activeRelationship.supportingRecordIds?.length) {
        appendTextElement(document, provenance, "p", `Supporting CKL records: ${activeRelationship.supportingRecordIds.join("; ")}.`, "narrative-explorer-source-id");
      }
      if (activeRelationship.supportingSourceIds?.length) {
        appendTextElement(document, provenance, "p", `Supporting CKL sources: ${activeRelationship.supportingSourceIds.join("; ")}.`, "narrative-explorer-source-id");
      }
      if (activeRelationship.humanScholarlyApproval) {
        appendTextElement(document, provenance, "p", `Human scholarly approval: ${activeRelationship.humanScholarlyApproval.replace(/_/g, " ")}.`);
      }
      header.append(provenance);
    }
    return header;
  }

  function renderTrailConnectionStep(document, relationship) {
    const step = element(document, "li", "narrative-explorer-trail-step is-connection");
    const provenance = readerText(relationship?.provenance);
    const provenanceLabel = provenance === "authored_ckl_relationship"
      ? "Authored CKL relationship"
      : provenance.startsWith("ckl_documented_")
        ? `CKL-documented ${provenance.slice("ckl_documented_".length).replace(/_/g, " ")}`
        : "Recorded connection";
    appendTextElement(document, step, "span", "Recorded connection", "narrative-explorer-trail-step-kind");
    appendTextElement(document, step, "span", provenanceLabel, "narrative-explorer-trail-step-label");
    const source = readerText(relationship?.sourcePassage);
    const destination = readerText(relationship?.destinationPassage);
    if (source || destination) appendTextElement(document, step, "span", `${source || "Source passage unavailable"} → ${destination || "Related passage unavailable"}`, "narrative-explorer-trail-step-direction");
    if (relationship?.originalRelationshipType) {
      appendTextElement(document, step, "span", `Original relationship type: ${readerText(relationship.originalRelationshipType)}`, "narrative-explorer-trail-step-direction");
    }
    if (relationship?.direction) {
      appendTextElement(document, step, "span", `Direction: ${readerText(relationship.direction).replace(/_/g, " ")}`, "narrative-explorer-trail-step-direction");
    }
    return step;
  }

  function renderEvidenceDetail(item, connections = [], trail = null, options = {}) {
    const document = options.document || root.document;
    if (!document) throw new Error("A document is required to render evidence details.");
    const view = element(document, "section", "narrative-explorer-evidence-detail");
    view.setAttribute("aria-label", "Evidence detail");
    if (trail) view.append(renderTrailHeader(trail, {...options, document}));
    const title = readerText(item?.title || item?.claim_text || item?.description || item?.id) || "Evidence detail";
    appendTextElement(document, view, "h3", title, "narrative-explorer-detail-title");
    view.children[view.children.length - 1].setAttribute("tabindex", "-1");
    view.children[view.children.length - 1].dataset.narrativePrimary = "true";

    const activeStep = activeTrailStep(trail);
    const followedRelationship = activeStep?.kind === "evidence" ? activeStep.relationship : null;
    if (followedRelationship?.basisKind === "ckl_related_evidence") {
      const label = readerText(followedRelationship.originalRelationshipType) || "(original CKL label unavailable)";
      appendTextElement(document, view, "p", `Opened through recorded CKL evidence relationship: ${label}.`, "narrative-explorer-connection-label");
      appendTextElement(document, view, "p", "This recorded relationship is not a Scripture anchor.", "narrative-explorer-connection-direction");
      if (followedRelationship.sourceId || followedRelationship.targetId) {
        appendTextElement(document, view, "p", `Recorded evidence IDs: ${readerText(followedRelationship.sourceId) || "(source ID unavailable)"} → ${readerText(followedRelationship.targetId) || "(target ID unavailable)"}. Destination resolution: ${readerText(followedRelationship.targetResolutionStatus) || "not established"}.`, "narrative-explorer-connection-status");
      }
      const basis = [
        readerText(followedRelationship.notes),
        followedRelationship.weight ? `recorded weight: ${readerText(followedRelationship.weight)}` : "",
      ].filter(Boolean).join(" · ");
      appendTextElement(document, view, `p`, `Recorded relationship basis: ${basis || "no explanatory basis was recorded"}.`, "narrative-explorer-provenance-note");
      appendCurationSummary(document, view, followedRelationship.curation, {trail, options, relationship: followedRelationship});
      if (label.toLowerCase() === "compared-with") {
        appendTextElement(document, view, "p", "A recorded compared-with relationship does not establish literary borrowing or dependence.", "narrative-explorer-caution");
      }
    }

    const category = evidenceCategoryLabel(item);
    appendTextElement(document, view, "p", category, "narrative-explorer-evidence-distinction");
    if (readerText(item?.claim_text)) appendTextElement(document, view, "p", readerText(item.claim_text), "narrative-explorer-item-copy");
    if (readerText(item?.description) && readerText(item.description) !== readerText(item.claim_text)) {
      appendTextElement(document, view, "p", readerText(item.description), "narrative-explorer-item-description");
    }
    if (isDisputed(item)) {
      appendTextElement(document, view, "p", "This item records a disputed hypothesis or interpretation; it is not presented as settled evidence.", "narrative-explorer-caution");
    }
    const temporalRelations = [item?.temporal_relation, ...(Array.isArray(item?.temporal_relations) ? item.temporal_relations : [])]
      .map((value) => readerText(value).toLowerCase().replace(/_/g, "-"));
    if (explicitlyDescribesLaterReception(item) && temporalRelations.includes("contemporary")) {
      appendTextElement(
        document,
        view,
        "p",
        "This record documents later reception. It does not establish that reception as the earlier passage's original meaning. The CKL Scripture link is marked contemporary, so its temporal metadata needs review.",
        "narrative-explorer-caution",
      );
    }
    if (category === "Ancient comparative literature") {
      appendTextElement(document, view, "p", "Comparative material is not, by itself, evidence of borrowing, quotation, fulfillment, or dependence.", "narrative-explorer-caution");
    }
    const contentStatus = readerText(item?.content_status).toLowerCase();
    if (contentStatus === "draft" || item?.human_review_required === true) {
      const notice = contentStatus === "draft" && item?.human_review_required === true
        ? "Draft evidence — awaiting human review."
        : contentStatus === "draft"
          ? "Draft evidence — review information is available below."
          : "Human review is required; see the review details below.";
      const governance = appendTextElement(document, view, "p", notice, "narrative-explorer-governance");
      governance.setAttribute("role", "status");
    }

    const identity = element(document, "dl", "narrative-explorer-detail-identity");
    appendDefinition(document, identity, "Projected item ID", item?.id);
    appendDefinition(document, identity, "CKL parent object", item?.parent_object_id || item?.object_id);
    appendDefinition(document, identity, "Record kind", item?.record_kind);
    appendDefinition(document, identity, "Original claim ID", item?.claim_id);
    appendDefinition(document, identity, "Original evidence ID", item?.evidence_id);
    appendDefinition(document, identity, "CKL local ID", item?.local_id);
    appendDefinition(document, identity, "Evidence category", item?.evidence_category);
    appendDefinition(document, identity, "Claim type", item?.claim_type);
    appendDefinition(document, identity, "Assertion type", item?.assertion_type);
    const action = supportedAction(item);
    if (action && typeof options.onNavigate === "function") {
      const button = element(document, "button", "secondary narrative-explorer-item-action");
      button.type = "button";
      button.textContent = action.label;
      if (action.ariaLabel) button.setAttribute("aria-label", action.ariaLabel.replace("{title}", title));
      button.dataset.narrativeFocusId = `source:${readerText(item?.id)}`;
      button.addEventListener("click", () => options.onNavigate(item, action, button));
      view.append(button);
    }

    const status = element(document, "ul", "narrative-explorer-evidence-status");
    [
      ["Confidence", item?.confidence],
      ["Certainty", item?.certainty],
      ["Dispute state", item?.dispute_status],
      ["Interpretation state", item?.interpretation_state],
      ["Review state", item?.review_status],
      ["Content state", item?.content_status],
      ["Human review required", item?.human_review_required],
      ["Human scholarly approval", item?.human_scholarly_approval],
      ["Temporal relation", item?.temporal_relation],
      ["Temporal scope", item?.temporal_scope],
    ].forEach(([label, value]) => {
      const entry = element(document, "li");
      entry.textContent = `${label}: ${metadataText(value) || "not recorded in CKL"}`;
      status.append(entry);
    });
    if (readerText(item?.temporal_scope?.notes)) {
      appendTextElement(document, view, "p", `Recorded historical qualification: ${readerText(item.temporal_scope.notes)}`, "narrative-explorer-caution");
    }

    const reviewDetails = element(document, "details", "narrative-explorer-detail-review");
    appendTextElement(document, reviewDetails, "summary", "Review, provenance and source details");
    reviewDetails.append(identity);
    appendRationaleDefinitionList(document, reviewDetails, item?.rationale);
    reviewDetails.append(status);
    view.append(reviewDetails);

    const originalAnchors = Array.isArray(item?.passage_anchors) ? item.passage_anchors : [];
    const applicable = Array.isArray(item?.applicable_passage_anchors) ? item.applicable_passage_anchors : [];
    const sourceDetails = element(document, "details", "narrative-explorer-detail-sources");
    appendTextElement(document, sourceDetails, "summary", "Scripture anchors and sources");
    appendAnchorGroup(document, sourceDetails, "Original Scripture anchors", originalAnchors, trail, options, {navigable: true});
    if (applicable.length) {
      appendAnchorGroup(document, sourceDetails, "Anchors applicable to this passage", applicable, trail, options, {navigable: false});
    } else {
      appendTextElement(document, sourceDetails, "p", "No passage anchors were returned for this item.", "narrative-explorer-missing-provenance");
    }
    appendBibliography(document, sourceDetails, item?.sources, item?.source_ids, {disclosure: false});
    view.append(sourceDetails);

    const connectionDetails = element(document, "details", "narrative-explorer-detail-connections");
    appendTextElement(document, connectionDetails, "summary", "Recorded relationships and further connections");
    appendConnectionList(document, connectionDetails, item, connections, trail, options);
    view.append(connectionDetails);
    return view;
  }

  function renderSubjectDetail(subject, trail = null, options = {}) {
    const document = options.document || root.document;
    if (!document) throw new Error("A document is required to render CKL subject details.");
    const view = element(document, "section", "narrative-explorer-subject-detail");
    view.setAttribute("aria-label", "Connected CKL subject");
    if (trail) view.append(renderTrailHeader(trail, {...options, document}));
    const title = readerText(subject?.title || subject?.name || subject?.id) || "Connected CKL subject";
    appendTextElement(document, view, "h3", title, "narrative-explorer-detail-title");
    view.children[view.children.length - 1].setAttribute("tabindex", "-1");
    view.children[view.children.length - 1].dataset.narrativePrimary = "true";
    appendTextElement(document, view, "p", `CKL subject · ${readerText(subject?.type) || "type not recorded"} · ${readerText(subject?.id) || "identity unavailable"}`, "narrative-explorer-item-kind");
    if (readerText(subject?.summary)) {
      appendTextElement(document, view, "p", readerText(subject.summary), "narrative-explorer-subject-summary");
    }
    appendTextElement(
      document,
      view,
      "p",
      "This CKL subject was opened through a recorded relationship. Other claims in this subject are not evidence for the originating passage unless their own passage anchors support that use.",
      "narrative-explorer-caution",
    );
    const activeRelationship = activeTrailStep(trail)?.relationship;
    appendCurationSummary(document, view, activeRelationship?.curation, {trail, options, relationship: activeRelationship});
    const status = element(document, "ul", "narrative-explorer-evidence-status");
    [
      ["Confidence", subject?.confidence],
      ["Review state", subject?.review_status],
      ["Content state", subject?.content_status],
      ["Human review required", subject?.human_review_required],
    ].forEach(([label, value]) => {
      const entry = element(document, "li");
      entry.textContent = `${label}: ${metadataText(value) || "not recorded in CKL"}`;
      status.append(entry);
    });
    view.append(status);
    appendBibliography(document, view, subject?.sources, subject?.source_ids);
    appendSubjectScripture(document, view, subject, trail, options);
    appendSubjectRelations(document, view, subject, trail, options);
    return view;
  }

  function renderSubjectFailure(message, targetId, trail = null, options = {}) {
    const document = options.document || root.document;
    const view = element(document, "section", "narrative-explorer-subject-failure");
    view.setAttribute("role", "alert");
    if (trail) view.append(renderTrailHeader(trail, {...options, document}));
    appendTextElement(document, view, "h3", "Connected subject unavailable");
    appendTextElement(document, view, "p", `CKL target ${readerText(targetId) || "unknown"} could not be resolved: ${readerText(message) || "the detail request did not complete"}. The recorded relationship remains unchanged.`, "narrative-explorer-caution");
    return view;
  }

  function renderEvidenceUnavailable(message, targetId, trail = null, options = {}) {
    const document = options.document || root.document;
    const view = element(document, "section", "narrative-explorer-evidence-unavailable");
    view.setAttribute("role", "status");
    if (trail) view.append(renderTrailHeader(trail, {...options, document}));
    appendTextElement(document, view, "h3", "Linked evidence unavailable");
    appendTextElement(document, view, "p", `The exact evidence item ${readerText(targetId) || "(ID unavailable)"} is not available as an eligible item in the current passage projection. ${readerText(message) || "No further availability reason is established."} The recorded relationship remains visible in its source detail.`, "narrative-explorer-missing-provenance");
    return view;
  }

  function appendDefinition(document, list, label, value) {
    const text = metadataText(value);
    const term = element(document, "dt");
    const description = element(document, "dd");
    setFormattedText(document, term, label);
    setFormattedText(document, description, text || "not recorded in CKL");
    list.append(term, description);
  }

  function evidenceCategoryLabel(item) {
    const category = readerText(item?.evidence_category).toLowerCase().replace(/_/g, "-");
    const claimType = readerText(item?.claim_type).toLowerCase().replace(/_/g, "-");
    const temporal = [item?.temporal_relation, ...(Array.isArray(item?.temporal_relations) ? item.temporal_relations : [])]
      .map((value) => readerText(value).toLowerCase().replace(/_/g, "-"));
    const anchors = [...(Array.isArray(item?.passage_anchors) ? item.passage_anchors : []), ...(Array.isArray(item?.applicable_passage_anchors) ? item.applicable_passage_anchors : [])];
    const comparative = anchors.some((anchor) => readerText(anchor?.relationship).toLowerCase() === "comparative")
      || temporal.includes("earlier-comparative") || temporal.includes("later-comparative");
    if (category.includes("manuscript") || category.includes("textual-witness") || item?.dispute_status === "textual_variant") return "Manuscript/textual witness";
    if (temporal.some((value) => value.includes("later")) || category.includes("reception") || claimType.includes("reception") || explicitlyDescribesLaterReception(item)) return "Later reception";
    if (["biblical-text", "biblical-textual", "textual-observation"].includes(category) || ["biblical-text", "textual-observation"].includes(claimType)) return "Original biblical text";
    if (category === "worldview-concept") {
      if (item?.assertion_type === "primary-evidence" && anchors.some((anchor) => readerText(anchor?.relationship).toLowerCase() === "direct")) return "Original biblical text · worldview language";
      return isDisputed(item) ? "Scholarly interpretation · disputed position" : "Scholarly interpretation · worldview context";
    }
    if (category === "geography-environment") return "Geography and place identification";
    if (category === "ancient-text" || category === "ancient-literature" || claimType === "historical-cultural") {
      return comparative ? "Ancient comparative literature" : "Historical or cultural background";
    }
    if (category.includes("artifact") || category.includes("historical") || category.includes("cultural") || category.includes("inscription") || category.includes("material-culture") || category.includes("archaeological")) return "Historical or cultural background";
    if (category.includes("literary") || category.includes("thematic") || ["literary", "composition", "rhetorical"].includes(claimType)) {
      if (item?.assertion_type === "secondary-evidence" || isDisputed(item)) return "Scholarly interpretation · literary reading";
      if (item?.assertion_type === "primary-evidence" && anchors.some((anchor) => readerText(anchor?.relationship).toLowerCase() === "direct")) return "Original biblical text · literary observation";
      return "Literary or thematic connection";
    }
    if (category.includes("scholarly") || category.includes("interpretive") || category.includes("theological") || claimType.includes("theolog") || item?.record_kind === "interpretive_note") return "Scholarly interpretation";
    return "Evidence type not recorded";
  }

  function explicitlyDescribesLaterReception(item) {
    const rationale = item?.rationale && typeof item.rationale === "object" ? Object.values(item.rationale) : [];
    const authoredText = [item?.title, item?.claim_text, item?.description, ...rationale]
      .filter((value) => typeof value === "string")
      .join(" ")
      .toLowerCase();
    return /later reception|later interpretation|reception source|reception witness|later interpretive/.test(authoredText);
  }

  function readerEvidenceLabel(item) {
    const domain = readerText(item?.domain).toLowerCase();
    if (domain === "maps") return item?.record_kind === "route" ? "Map route record" : "Map place record";
    if (domain === "archaeology") return "Archaeology record";
    if (domain && domain !== "ckl") return "Related source record";
    return evidenceCategoryLabel(item);
  }

  function isDisputed(item) {
    const dispute = readerText(item?.dispute_status).toLowerCase().replace(/-/g, "_");
    return dispute !== "" && !["none", "not_disputed", "not_applicable", "unknown"].includes(dispute)
      || ["disputed", "unknown"].includes(readerText(item?.interpretation_state).toLowerCase().replace(/-/g, "_"));
  }

  function appendRationaleDetails(document, parent, rationale) {
    if (!rationale || typeof rationale !== "object" || !Object.keys(rationale).length) return;
    const details = element(document, "details", "narrative-explorer-recorded-rationale");
    appendTextElement(document, details, "summary", "Recorded observations and interpretation");
    appendRationaleDefinitionList(document, details, rationale);
    parent.append(details);
  }

  function appendRationaleDefinitionList(document, parent, rationale) {
    if (!rationale || typeof rationale !== "object" || !Object.keys(rationale).length) return;
    const list = element(document, "dl", "narrative-explorer-detail-identity");
    Object.entries(rationale).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") return;
      const term = element(document, "dt");
      setFormattedText(document, term, key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()));
      const description = element(document, "dd");
      setFormattedText(document, description, metadataText(value));
      list.append(term, description);
    });
    parent.append(list);
  }

  function appendAnchorGroup(document, parent, title, anchors, trail, options, config = {}) {
    if (!anchors.length) return;
    const section = element(document, "section", "narrative-explorer-scripture-anchors");
    appendTextElement(document, section, "h4", title);
    const list = element(document, "ul");
    const seen = new Set();
    anchors.slice(0, 16).forEach((anchor, index) => {
      const data = typeof anchor === "string" ? {reference: anchor} : anchor || {};
      const reference = readerText(data.reference);
      if (!reference || seen.has(reference)) return;
      seen.add(reference);
      const entry = element(document, "li");
      const relationship = readerText(data.relationship);
      const rationale = readerText(data.relevance_rationale || data.notes);
      appendTextElement(document, entry, "p", `${reference}${relationship ? ` · ${relationship}` : ""}`);
      if (rationale) appendTextElement(document, entry, "p", rationale, "narrative-explorer-provenance-note");
      const currentReference = normalizeReference(trailCurrentSelection(trail)?.reference);
      const resolved = validateScriptureReference(reference, options.knownBooks || []);
      const normalizedReference = normalizeReference(resolved.reference || reference);
      const alreadyVisited = passageIsInTrail(trail, normalizedReference);
      if (!config.navigable || currentReference === normalizedReference) {
        if (currentReference === normalizedReference) appendTextElement(document, entry, "span", "Current passage", "narrative-explorer-current-passage");
      } else if (alreadyVisited) {
        appendTextElement(document, entry, "span", "This passage already appears in the trail; the cycle was stopped.", "narrative-explorer-trail-cycle");
      } else if (!resolved.valid) {
        appendTextElement(document, entry, "span", `Passage navigation unavailable: ${resolved.reason}`, "narrative-explorer-missing-provenance");
      } else if (typeof options.onOpenPassage === "function") {
        const button = element(document, "button", "secondary narrative-explorer-passage-link");
        button.type = "button";
        button.textContent = `Open ${resolved.reference}`;
        button.dataset.narrativeFocusId = `scripture:${resolved.reference}`;
        button.addEventListener("click", () => options.onOpenPassage(resolved, relationshipSnapshot(data), button));
        entry.append(button);
      }
      list.append(entry);
    });
    section.append(list);
    parent.append(section);
  }

  function appendBibliography(document, parent, sources, sourceIds, config = {}) {
    const sourceList = Array.isArray(sources) ? sources : [];
    const ids = Array.isArray(sourceIds) ? sourceIds.map(readerText).filter(Boolean) : [];
    const disclosure = config.disclosure !== false;
    const details = element(document, disclosure ? "details" : "section", "narrative-explorer-bibliography");
    const title = `Bibliography (${Math.max(sourceList.length, ids.length)} source${Math.max(sourceList.length, ids.length) === 1 ? "" : "s"})`;
    appendTextElement(document, details, disclosure ? "summary" : "h4", title);
    const list = element(document, "ul");
    const covered = new Set();
    sourceList.slice(0, 12).forEach((source) => {
      const id = readerText(source?.id);
      const data = source?.bibliographic_details && typeof source.bibliographic_details === "object"
        ? source.bibliographic_details
        : source || {};
      if (id) covered.add(id);
      const entry = element(document, "li", "narrative-explorer-bibliography-entry");
      const title = readerText(data.title);
      const fields = [
        ["Title", title], ["Author", data.author], ["Publisher", data.publisher],
        ["Publication year", data.year], ["Locator", data.locator], ["Source type", data.source_type],
      ].filter(([, value]) => value !== null && value !== undefined && value !== "");
      appendTextElement(document, entry, "p", fields.map(([label, value]) => `${label}: ${metadataText(value)}`).join(" · ") || `Bibliographic details are not available in CKL for source ${id || "(ID missing)"}.`);
      if (id) appendTextElement(document, entry, "p", `Source identifier: ${id}`, "narrative-explorer-source-id");
      const missing = ["title", "author", "publisher", "year", "locator"].filter((key) => data[key] === null || data[key] === undefined || data[key] === "");
      if (missing.length && source?.details_available !== false) {
        appendTextElement(document, entry, "p", `Missing in CKL: ${missing.map((key) => ({title: "title", author: "author", publisher: "publisher", year: "publication year", locator: "locator"}[key])).join(", ")}.`, "narrative-explorer-missing-provenance");
      }
      if (readerText(data.notes)) appendTextElement(document, entry, "p", readerText(data.notes), "narrative-explorer-provenance-note");
      const url = safeHttpUrl(data.url);
      if (url) {
        const link = element(document, "a");
        link.setAttribute("href", url);
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener noreferrer");
        link.textContent = "Open recorded source URL";
        entry.append(link);
      }
      list.append(entry);
    });
    ids.filter((id) => !covered.has(id)).slice(0, 12).forEach((id) => {
      const entry = element(document, "li");
      entry.textContent = `Source details not available in CKL: ${id}`;
      list.append(entry);
    });
    if (sourceList.length === 0 && ids.length === 0) {
      const missing = element(document, "li");
      missing.textContent = "No source identifiers or bibliographic details were returned for this item.";
      list.append(missing);
    }
    details.append(list);
    parent.append(details);
  }

  function safeHttpUrl(value) {
    const text = readerText(value);
    if (!text) return "";
    try {
      const url = new URL(text, root.location?.origin || "https://example.invalid");
      return ["http:", "https:"].includes(url.protocol) && /^https?:\/\//i.test(text) ? url.href : "";
    } catch (_error) {
      return "";
    }
  }

  function appendConnectionList(document, parent, item, connections, trail, options) {
    const itemId = readerText(item?.id);
    const allEdges = (Array.isArray(connections) ? connections : [])
      .filter((edge) => edge?.source_id === itemId || edge?.target_id === itemId)
      .map((edge) => {
        if (edge?.direction !== "reciprocal") return edge;
        const hasReverse = readerText(edge.reverse_edge_id)
          && (Array.isArray(connections) ? connections : []).some((candidate) => (
            candidate?.id === edge.reverse_edge_id
            && candidate.source_id === edge.target_id
            && candidate.target_id === edge.source_id
            && candidate.direction === "reciprocal"
            && candidate.reverse_edge_id === edge.id
          ));
        return hasReverse ? edge : {...edge, direction: "one_way", reverse_edge_id: null};
      });
    const edges = allEdges
      .filter((edge) => !(edge?.direction === "reciprocal" && edge?.target_id === itemId && edge?.source_id !== itemId))
      .sort((left, right) => readerText(left?.id).localeCompare(readerText(right?.id)));
    const section = element(document, "section", "narrative-explorer-connections");
    const anchors = edges.filter((edge) => readerText(edge?.basis?.kind).endsWith("_scripture_anchor"));
    const relationships = edges.filter((edge) => !readerText(edge?.basis?.kind).endsWith("_scripture_anchor"));
    appendConnectionGroup(
      document,
      section,
      `Recorded CKL relationships (${relationships.length})`,
      relationships,
      item,
      trail,
      options,
      "No separate CKL relationship was returned for this item in the current passage projection.",
    );
    appendConnectionGroup(
      document,
      section,
      `Passage anchors (${anchors.length})`,
      anchors,
      item,
      trail,
      options,
      "No Scripture passage anchors were returned for this item.",
    );
    parent.append(section);
  }

  function appendConnectionGroup(document, parent, title, edges, item, trail, options, emptyMessage) {
    const group = element(document, "section", "narrative-explorer-connection-group");
    appendTextElement(document, group, "h4", title);
    if (!edges.length) {
      appendTextElement(document, group, "p", emptyMessage);
      parent.append(group);
      return;
    }
    const list = element(document, "ol", "narrative-explorer-connection-list");
    let next = 0;
    let moreButton = null;
    const addPage = () => {
      const page = edges.slice(next, next + CONNECTION_PAGE_SIZE);
      page.forEach((edge) => list.append(renderConnection(document, item, edge, trail, options)));
      next += page.length;
      if (moreButton) {
        moreButton.hidden = next >= edges.length;
        moreButton.textContent = `Show ${Math.min(CONNECTION_PAGE_SIZE, edges.length - next)} more ${title.startsWith("Passage anchors") ? "anchors" : "relationships"}`;
      }
    };
    addPage();
    group.append(list);
    if (edges.length > CONNECTION_PAGE_SIZE) {
      moreButton = element(document, "button", "secondary narrative-explorer-more-connections");
      moreButton.type = "button";
      moreButton.textContent = `Show ${Math.min(CONNECTION_PAGE_SIZE, edges.length - next)} more ${title.startsWith("Passage anchors") ? "anchors" : "relationships"}`;
      moreButton.addEventListener("click", addPage);
      group.append(moreButton);
    }
    parent.append(group);
  }

  function renderConnection(document, selectedItem, edge, trail, options) {
    const entry = element(document, "li", "narrative-explorer-connection");
    const outgoing = edge.source_id === selectedItem.id;
    const source = readerText(edge.source_id);
    const target = readerText(edge.target_id);
    const sourceSubject = readerText(edge?.basis?.parent_object_id) || endpointSubjectId(source);
    const targetSubject = endpointSubjectId(target);
    const direction = edge.direction === "reciprocal" ? "reciprocal" : "one-way";
    const isScriptureAnchor = edge?.basis?.kind === "ckl_scripture_anchor";
    const isRelatedEvidence = edge?.basis?.kind === "ckl_related_evidence";
    const anchorRelationship = readerText(edge?.basis?.anchor_metadata?.relationship).toLowerCase();
    const category = isScriptureAnchor
      ? (anchorRelationship === "comparative" ? "Comparative passage anchor" : "Scripture passage anchor")
      : connectionCategoryLabel(edge.connection_type);
    const relationshipHeading = isScriptureAnchor
      ? `Evidence scope: ${category}`
      : isRelatedEvidence ? "Recorded CKL evidence relationship" : `Recorded relationship: ${category}`;
    appendTextElement(document, entry, "p", `${relationshipHeading}${edge.original_relationship_type ? ` · original CKL label: ${readerText(edge.original_relationship_type)}` : " · original CKL label unavailable"}`, "narrative-explorer-connection-label");
    appendTextElement(document, entry, "p", `Source subject: ${sourceSubject} · Target subject: ${targetSubject} · Direction: ${sourceSubject} → ${targetSubject} (${direction}).`);
    if (edge.direction === "reciprocal" && readerText(edge.reverse_edge_id)) {
      appendTextElement(document, entry, "p", `A reciprocal CKL edge is recorded; reverse CKL edge ID: ${readerText(edge.reverse_edge_id)}.`, "narrative-explorer-connection-direction");
    }
    if (readerText(edge.relationship_mode)) appendTextElement(document, entry, "p", `Interpretive status: ${readerText(edge.relationship_mode)}.`, "narrative-explorer-connection-status");
    if (readerText(edge.temporal_layer)) appendTextElement(document, entry, "p", `Original CKL temporal layer: ${readerText(edge.temporal_layer)}.`, "narrative-explorer-connection-status");
    if (edge.basis && Object.keys(edge.basis).length) {
      appendTextElement(document, entry, "p", `Recorded support: ${readerText(edge.basis.notes || edge.basis.reference || edge.basis.kind) || "basis present; no explanatory note recorded"}.`, "narrative-explorer-provenance-note");
      if (readerText(edge.basis.reference)) appendTextElement(document, entry, "p", `Evidence or Scripture anchor: ${readerText(edge.basis.reference)}.`);
    }
    appendCurationSummary(document, entry, edge.curation, {trail, options, relationship: edge});
    if (edge.curation?.classification === "later_canonical_reception" && edge.temporal_layer === "unknown") {
      appendTextElement(document, entry, "p", "Later canonical reception is a separate curated relationship classification; the original CKL temporal layer is unknown.", "narrative-explorer-connection-status");
    }
    if (isScriptureAnchor) {
      appendTextElement(document, entry, "p", "This anchor shows the evidence's passage scope; by itself it does not establish a literary or theological relationship between passages.", "narrative-explorer-connection-direction");
    } else if (isRelatedEvidence) {
      appendTextElement(document, entry, "p", "This is an authored evidence-to-evidence relationship, not a Scripture anchor.", "narrative-explorer-connection-direction");
      appendTextElement(document, entry, "p", `Recorded evidence IDs: ${source} → ${target}.`, "narrative-explorer-connection-status");
      if (readerText(edge.original_relationship_type).toLowerCase() === "compared-with") {
        appendTextElement(document, entry, "p", "A recorded compared-with relationship does not establish literary borrowing or dependence.", "narrative-explorer-caution");
      }
    } else if (edge.connection_type === "uncategorized" || !connectionCategoryLabel(edge.connection_type)) {
      appendTextElement(document, entry, "p", "This authored label is a descriptive association; its relationship category is not established by the projection.", "narrative-explorer-caution");
    }
    if (outgoing) {
      if (isRelatedEvidence) {
        const parentId = readerText(edge?.basis?.parent_object_id);
        const localRecordId = readerText(edge?.basis?.local_record_id);
        const targetEvidenceId = readerText(edge?.basis?.target_evidence_id);
        const expectedSourceId = parentId && localRecordId ? `ckl:${parentId}#evidence:${localRecordId}` : "";
        const expectedTargetId = parentId && targetEvidenceId ? `ckl:${parentId}#evidence:${targetEvidenceId}` : "";
        const sourceMatches = selectedItem?.record_kind === "evidence"
          && selectedItem?.id === expectedSourceId
          && readerText(selectedItem?.parent_object_id) === parentId
          && readerText(selectedItem?.local_id) === localRecordId
          && readerText(selectedItem?.evidence_id) === localRecordId
          && Array.isArray(selectedItem?.applicable_passage_anchors)
          && selectedItem.applicable_passage_anchors.length > 0;
        const status = readerText(edge?.basis?.target_resolution_status);
        if (status === "filtered") {
          appendTextElement(document, entry, "p", "The linked evidence is filtered from this passage projection and cannot be opened here.", "narrative-explorer-missing-provenance");
        } else if (status === "unavailable") {
          appendTextElement(document, entry, "p", "The target could not be resolved in the current lookup; its availability reason is not established.", "narrative-explorer-missing-provenance");
        } else if (status === "invalid") {
          appendTextElement(document, entry, "p", "The recorded target ID is invalid within the recorded CKL parent.", "narrative-explorer-missing-provenance");
        } else if (status !== "eligible") {
          appendTextElement(document, entry, "p", "The target cannot be verified from the current projection.", "narrative-explorer-missing-provenance");
        } else if (!sourceMatches || !expectedTargetId || target !== expectedTargetId) {
          appendTextElement(document, entry, "p", "The exact parent-qualified target could not be verified from the current projection.", "narrative-explorer-missing-provenance");
        } else if (typeof options.resolveEvidenceTarget !== "function") {
          appendTextElement(document, entry, "p", "The exact parent-qualified target could not be verified from the current projection.", "narrative-explorer-missing-provenance");
        } else {
          const targetItem = options.resolveEvidenceTarget(expectedTargetId);
          if (!exactEvidenceTarget(targetItem, expectedTargetId, parentId, targetEvidenceId)) {
            appendTextElement(document, entry, "p", "The exact parent-qualified target could not be verified from the current projection.", "narrative-explorer-missing-provenance");
          } else if (trailNodes(trail).some((node) => node.kind === "evidence" && node.id === expectedTargetId)) {
            appendTextElement(document, entry, "p", "This evidence already appears in the trail; the cycle was stopped.", "narrative-explorer-trail-cycle");
          } else if (currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) {
            appendTextElement(document, entry, "p", `This connection trail has reached its ${MAX_RELATIONSHIP_HOPS}-link limit.`, "narrative-explorer-trail-limit");
          } else if (typeof options.onFollowEvidence === "function") {
            const title = readerText(targetItem.title || targetItem.claim_text || targetItem.description) || expectedTargetId;
            appendTextElement(document, entry, "p", "The destination is an independently eligible evidence item in this passage projection.", "narrative-explorer-connection-status");
            appendActionButton(document, entry, `Open linked evidence: ${title}`, `connection:${readerText(edge.id)}`, (button) => options.onFollowEvidence(
              targetItem,
              relationshipSnapshot(edge),
              button,
            ));
          } else {
            appendTextElement(document, entry, "p", "This target has no supported destination in the current projection.", "narrative-explorer-missing-provenance");
          }
        }
      } else {
        const targetObjectId = canonicalTargetObjectId(edge.target_id);
        if (targetObjectId && typeof options.onFollowConnection === "function") {
          if (currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) {
            appendTextElement(document, entry, "p", `This connection trail has reached its ${MAX_RELATIONSHIP_HOPS}-link limit.`, "narrative-explorer-trail-limit");
          } else {
            appendActionButton(document, entry, `Open connected CKL subject: ${targetSubject}`, `connection:${readerText(edge.id)}`, (button) => options.onFollowConnection(
              {targetId: targetObjectId, title: targetSubject},
              relationshipSnapshot(edge),
              button,
            ));
          }
        } else if (String(edge.target_id || "").startsWith("passage:") && typeof options.onOpenPassage === "function") {
          const reference = String(edge.target_id).slice("passage:".length);
          const resolved = validateScriptureReference(reference, options.knownBooks || []);
          if (passageIsInTrail(trail, normalizeReference(resolved.reference || reference))) appendTextElement(document, entry, "p", "This passage already appears in the trail; the cycle was stopped.", "narrative-explorer-trail-cycle");
          else if (resolved.valid && currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) appendTextElement(document, entry, "p", `This connection trail has reached its ${MAX_RELATIONSHIP_HOPS}-link limit.`, "narrative-explorer-trail-limit");
          else if (resolved.valid) appendActionButton(document, entry, `Open linked passage: ${resolved.reference}`, `connection:${readerText(edge.id)}`, (button) => options.onOpenPassage(resolved, relationshipSnapshot(edge), button));
          else appendTextElement(document, entry, "p", `Passage navigation unavailable: ${resolved.reason}`, "narrative-explorer-missing-provenance");
        } else {
          appendTextElement(document, entry, "p", "This target has no supported destination in the current projection.", "narrative-explorer-missing-provenance");
        }
      }
    } else {
      appendTextElement(document, entry, "p", "This edge points toward the selected item; the UI does not create a reverse navigation edge.", "narrative-explorer-connection-direction");
    }
    return entry;
  }

  function connectionCategoryLabel(value) {
    const labels = {
      direct_quotation: "Direct quotation",
      explicit_textual_reference: "Explicit textual reference",
      shared_literary_motif: "Shared literary motif",
      narrative_parallel: "Narrative parallel",
      thematic_relationship: "Thematic relationship",
      later_canonical_reception: "Later canonical reception",
      proposed_intertextual_echo: "Proposed intertextual echo",
      interpretive_association: "Interpretive association",
      uncategorized: "Descriptive association",
    };
    return labels[readerText(value)] || "";
  }

  function canonicalTargetObjectId(value) {
    const target = readerText(value);
    if (!target.startsWith("ckl:")) return "";
    const id = target.slice(4);
    return id && !id.includes("#") ? id : "";
  }

  function exactEvidenceTarget(item, expectedId, parentId, localId) {
    return Boolean(item)
      && item.record_kind === "evidence"
      && item.id === expectedId
      && expectedId === `ckl:${parentId}#evidence:${localId}`
      && readerText(item.parent_object_id) === parentId
      && readerText(item.local_id) === localId
      && readerText(item.evidence_id) === localId
      && Array.isArray(item.applicable_passage_anchors)
      && item.applicable_passage_anchors.length > 0;
  }

  function endpointLabel(value, item) {
    if (value === item.id) return readerText(item.title || item.claim_text || item.description) || value;
    if (value.startsWith("ckl:")) return value.slice(4);
    if (value.startsWith("passage:")) return value.slice("passage:".length);
    return value;
  }

  function endpointSubjectId(value) {
    const endpoint = readerText(value);
    if (!endpoint.startsWith("ckl:")) return endpoint;
    return endpoint.slice(4).split("#", 1)[0] || endpoint;
  }

  function appendSubjectScripture(document, parent, subject, trail, options) {
    const anchors = Array.isArray(subject?.scripture_references) ? subject.scripture_references : [];
    const section = element(document, "section", "narrative-explorer-subject-scripture");
    appendTextElement(document, section, "h4", `Scripture anchors (${anchors.length})`);
    if (!anchors.length) appendTextElement(document, section, "p", "No Scripture anchors are recorded on this CKL subject.");
    const list = element(document, "ol");
    let next = 0;
    let moreButton = null;
    const addPage = () => {
      anchors.slice(next, next + PAGE_SIZE).forEach((raw) => {
        const anchor = typeof raw === "string" ? {reference: raw} : raw || {};
        const reference = readerText(anchor.reference);
        if (!reference) return;
        const entry = element(document, "li");
        appendTextElement(document, entry, "p", `${reference}${anchor.relationship ? ` · ${readerText(anchor.relationship)}` : ""}`);
        if (readerText(anchor.notes)) appendTextElement(document, entry, "p", readerText(anchor.notes), "narrative-explorer-provenance-note");
        const resolved = validateScriptureReference(reference, options.knownBooks || []);
        if (!resolved.valid) appendTextElement(document, entry, "p", `Passage navigation unavailable: ${resolved.reason}`, "narrative-explorer-missing-provenance");
        else if (normalizeReference(resolved.reference) === normalizeReference(trailCurrentSelection(trail)?.reference)) {
          appendTextElement(document, entry, "span", "Current passage", "narrative-explorer-current-passage");
        } else if (passageIsInTrail(trail, normalizeReference(resolved.reference))) {
          appendTextElement(document, entry, "span", "This passage already appears in the trail; the cycle was stopped.", "narrative-explorer-trail-cycle");
        } else if (currentRelationshipHops(trail) >= MAX_RELATIONSHIP_HOPS) {
          appendTextElement(document, entry, "p", `This connection trail has reached its ${MAX_RELATIONSHIP_HOPS}-link limit.`, "narrative-explorer-trail-limit");
        } else if (typeof options.onOpenPassage === "function") {
          appendActionButton(document, entry, `Open linked passage: ${resolved.reference}`, `scripture:${resolved.reference}`, (button) => options.onOpenPassage(resolved, relationshipSnapshot(anchor), button));
        }
        list.append(entry);
      });
      next += Math.min(PAGE_SIZE, anchors.length - next);
      if (moreButton) {
        moreButton.hidden = next >= anchors.length;
        moreButton.textContent = `Show ${Math.min(PAGE_SIZE, anchors.length - next)} more Scripture anchors`;
      }
    };
    addPage();
    section.append(list);
    if (anchors.length > PAGE_SIZE) {
      moreButton = element(document, "button", "secondary narrative-explorer-more-scripture");
      moreButton.type = "button";
      moreButton.textContent = `Show ${Math.min(PAGE_SIZE, anchors.length - next)} more Scripture anchors`;
      moreButton.addEventListener("click", addPage);
      section.append(moreButton);
    }
    parent.append(section);
  }

  function appendSubjectRelations(document, parent, subject, trail, options) {
    const links = Array.isArray(subject?.related_object_links) ? [...subject.related_object_links] : [];
    links.sort((left, right) => readerText(left?.id).localeCompare(readerText(right?.id)) || readerText(left?.relationship).localeCompare(readerText(right?.relationship)));
    const section = element(document, "section", "narrative-explorer-subject-relations");
    appendTextElement(document, section, "h4", `Authored CKL relationships (${links.length})`);
    if (!links.length) appendTextElement(document, section, "p", "No further authored CKL relationships are available on this subject.");
    const list = element(document, "ol");
    let next = 0;
    let moreButton = null;
    const addPage = () => {
      links.slice(next, next + CONNECTION_PAGE_SIZE).forEach((link) => {
        const entry = element(document, "li", "narrative-explorer-subject-relationship");
        const label = readerText(link.relationship) || "(original relationship label unavailable)";
        const targetId = readerText(link.id);
        const title = readerText(link.title || targetId) || "CKL target unavailable";
        appendTextElement(document, entry, "p", `${link.curation ? "Original CKL relationship" : "Relationship: descriptive association"} · original CKL label: ${label}`, "narrative-explorer-connection-label");
        appendTextElement(document, entry, "p", `Source subject: ${readerText(subject.id)} · Target subject: ${title} (${targetId})${readerText(link.type) ? ` · type: ${readerText(link.type)}` : ""} · Direction: ${readerText(subject.id)} → ${targetId}.`);
        if (link.curation) {
          appendCurationSummary(document, entry, link.curation, {trail, options, relationship: link});
          if (readerText(link.temporal_layer)) appendTextElement(document, entry, "p", `Original CKL temporal layer: ${readerText(link.temporal_layer)}.`, "narrative-explorer-connection-status");
          if (link.curation.classification === "later_canonical_reception" && link.temporal_layer === "unknown") {
            appendTextElement(document, entry, "p", "Later canonical reception is a separate curated relationship classification; the original CKL temporal layer is unknown.", "narrative-explorer-connection-status");
          }
        } else {
          appendTextElement(document, entry, "p", "Validated relationship category and reciprocal status are not included in this subject detail response; the original label is retained without upgrading it.", "narrative-explorer-caution");
          appendTextElement(document, entry, "p", "Interpretive status: not recorded for this relationship in the subject detail response.", "narrative-explorer-connection-status");
        }
        if (Number.isFinite(Number(link.weight))) appendTextElement(document, entry, "p", `CKL relationship weight: ${Number(link.weight)} (recorded metadata; not an interpretation category).`, "narrative-explorer-connection-status");
        if (readerText(link.notes)) appendTextElement(document, entry, "p", `Recorded rationale: ${readerText(link.notes)}`, "narrative-explorer-provenance-note");
        if (!link.curation) appendTextElement(document, entry, "p", "Evidence or Scripture anchor: not included in this subject detail response.", "narrative-explorer-missing-provenance");
        const currentHops = currentRelationshipHops(trail);
        if (!targetId) appendTextElement(document, entry, "p", "No target CKL ID was returned; this relationship cannot be followed.", "narrative-explorer-missing-provenance");
        else if (currentHops >= MAX_RELATIONSHIP_HOPS) appendTextElement(document, entry, "p", `This connection trail has reached its ${MAX_RELATIONSHIP_HOPS}-link limit.`, "narrative-explorer-trail-limit");
        else if (trailNodes(trail).some((node) => node.subjectId === targetId || node.parentObjectId === targetId)) appendTextElement(document, entry, "p", "This relationship returns to a subject already in the trail; the cycle is stopped.", "narrative-explorer-trail-cycle");
        else if (typeof options.onFollowSubject === "function") {
          appendActionButton(document, entry, `Open connected CKL subject: ${title}`, `subject-relationship:${targetId}`, (button) => options.onFollowSubject(
            {targetId, title},
            {
              connection_type: link.connection_type,
              originalRelationshipType: link.original_relationship_type || label,
              original_relationship_type: link.original_relationship_type || label,
              relationship_mode: link.relationship_mode,
              temporal_layer: link.temporal_layer,
              direction: link.direction,
              reverse_edge_id: link.reverse_edge_id,
              basis: link.basis || {notes: readerText(link.notes), weight: link.weight},
              curation: link.curation,
              notes: readerText(link.notes),
              weight: link.weight,
            },
            button,
          ));
        }
        list.append(entry);
      });
      next += Math.min(CONNECTION_PAGE_SIZE, links.length - next);
      if (moreButton) {
        moreButton.hidden = next >= links.length;
        moreButton.textContent = `Show ${Math.min(CONNECTION_PAGE_SIZE, links.length - next)} more relationships`;
      }
    };
    addPage();
    section.append(list);
    if (links.length > CONNECTION_PAGE_SIZE) {
      moreButton = element(document, "button", "secondary narrative-explorer-more-subject-relations");
      moreButton.type = "button";
      moreButton.textContent = `Show ${Math.min(CONNECTION_PAGE_SIZE, links.length - next)} more relationships`;
      moreButton.addEventListener("click", addPage);
      section.append(moreButton);
    }
    parent.append(section);
  }

  function appendActionButton(document, parent, label, focusId, callback) {
    const button = element(document, "button", "secondary narrative-explorer-trail-action");
    button.type = "button";
    button.textContent = label;
    button.dataset.narrativeFocusId = focusId;
    button.addEventListener("click", () => callback(button));
    parent.append(button);
    return button;
  }

  function renderFailure(state, selection, options = {}) {
    const document = options.document || root.document;
    if (!document) throw new Error("A document is required to render Narrative Explorer status.");
    const container = element(document, "section", "narrative-explorer-state");
    container.setAttribute("role", "alert");
    if (options.trail) container.append(renderTrailHeader(options.trail, {...options, document}));
    const offline = state === "offline";
    appendTextElement(document, container, "h3", offline ? "Not available offline" : "Narrative Explorer unavailable");
    const reference = readerText(selection?.reference) || "this passage";
    appendTextElement(
      document,
      container,
      "p",
      offline
        ? `No saved Narrative Explorer projection is available for ${reference}. Reconnect and try again to check current evidence.`
        : `Narrative Explorer could not check ${reference} right now. Availability is unknown; this is not an empty evidence result.`,
    );
    if (typeof options.onRetry === "function") {
      const retry = element(document, "button", "secondary narrative-explorer-retry");
      retry.type = "button";
      retry.textContent = "Check again";
      retry.addEventListener("click", options.onRetry);
      container.append(retry);
    }
    return container;
  }

  function normalizeState(value) {
    return ["available", "partial", "not_represented", "unknown"].includes(value) ? value : "unknown";
  }

  function element(document, tagName, className = "") {
    const value = document.createElement(tagName);
    if (className) value.className = className;
    return value;
  }

  function appendTextElement(document, parent, tagName, text, className = "") {
    const value = element(document, tagName, className);
    setFormattedText(document, value, text);
    parent.append(value);
    return value;
  }

  function setFormattedText(document, parent, value) {
    const source = String(value ?? "");
    const emphasisPattern = /(\*\*|__)(\S[^*_\n]*?\S)\1|(?<![\w])([*_])(\S[^*_\n]*?\S)\3(?![\w])/g;
    const matches = [...source.matchAll(emphasisPattern)];
    if (!matches.length) {
      parent.textContent = source;
      return;
    }
    parent.textContent = "";
    let cursor = 0;
    matches.forEach((match) => {
      const start = match.index ?? cursor;
      if (start > cursor) appendInlineText(document, parent, source.slice(cursor, start));
      const marker = match[1] || match[3];
      const emphasized = element(document, marker.length === 2 ? "strong" : "em");
      emphasized.textContent = match[2] || match[4];
      parent.append(emphasized);
      cursor = start + match[0].length;
    });
    if (cursor < source.length) appendInlineText(document, parent, source.slice(cursor));
  }

  function appendInlineText(document, parent, text) {
    if (!text) return;
    const value = element(document, "span");
    value.textContent = text;
    parent.append(value);
  }

  function readerText(value) {
    return typeof value === "string" || typeof value === "number" ? String(value).trim() : "";
  }

  function metadataText(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (Array.isArray(value)) return value.map(metadataText).filter(Boolean).join(", ");
    if (typeof value === "object") return compactObject(value);
    return String(value);
  }

  function compactObject(value) {
    if (!value || typeof value !== "object") return readerText(value);
    return Object.entries(value)
      .filter(([, entry]) => entry !== null && entry !== undefined && entry !== "")
      .slice(0, 6)
      .map(([key, entry]) => `${key}: ${typeof entry === "object" ? JSON.stringify(entry) : String(entry)}`)
      .join("; ");
  }

  function dispatchMetric(detail) {
    if (typeof root.document?.dispatchEvent !== "function" || typeof root.CustomEvent !== "function") return;
    root.document.dispatchEvent(new root.CustomEvent("bhf:narrative-explorer-metrics", {detail}));
  }

  function now() {
    return root.performance?.now?.() ?? Date.now();
  }

  function elapsed(start) {
    return Math.max(0, now() - start);
  }

  function byteLength(value) {
    if (typeof root.TextEncoder === "function") return new root.TextEncoder().encode(value).length;
    return unescape(encodeURIComponent(value)).length;
  }

  return Object.freeze({
    SECTIONS,
    MAX_RELATIONSHIP_HOPS,
    MAX_TRAIL_NODES,
    urlFor,
    load,
    findVerifiedPassageRoute,
    createSubjectLoader,
    createSession,
    createTrail,
    addEvidenceStep,
    followSubject,
    followEvidence,
    followPassage,
    returnToOrigin,
    applyProjectionCurationsToSubject,
    activeTrailStep,
    trailNodes,
    trailCurrentSelection,
    trailReturnFocusId,
    currentRelationshipHops,
    validateScriptureReference,
    subjectMatchesId,
    renderOverview,
    renderTrailHeader,
    renderEvidenceDetail,
    renderSubjectDetail,
    renderSubjectFailure,
    renderEvidenceUnavailable,
    renderFailure,
    classifyError,
  });
});
