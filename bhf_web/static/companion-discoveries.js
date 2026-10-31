/* Render validated discovery cards and route their grounded exploration actions. */
(function (root, factory) {
  "use strict";

  const discoveries = factory();
  if (typeof module === "object" && module.exports) module.exports = discoveries;
  root.BHFCompanionDiscoveries = discoveries;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function render(panel, context = {}, options = {}) {
    const cards = options.visible !== false && Array.isArray(context.presentation_packet?.cards)
      ? context.presentation_packet.cards
      : [];
    const walkCards = cards.filter((card) => card?.type === "walk_the_land");
    renderSection(panel, "[data-companion-land-section]", "[data-companion-land]", walkCards, "walk_the_land", 1, context, options);
  }

  function renderSection(panel, sectionSelector, listSelector, cards, type, maximum, context, options) {
    const section = panel?.querySelector(sectionSelector);
    const list = panel?.querySelector(listSelector);
    if (!section || !list) return;
    const visibleCards = cards.filter((card) => card?.type === type).slice(0, maximum);
    section.hidden = visibleCards.length === 0 && options?.showEmpty !== true;
    const document = list.ownerDocument || globalThis.document;
    if (visibleCards.length) {
      list.replaceChildren(...visibleCards.map((card) => discoveryCard(card, context, document, options)));
    } else if (options?.showEmpty === true && type === "walk_the_land") {
      const empty = document.createElement("p");
      empty.className = "companion-geography-empty";
      empty.dataset.geographyEmpty = "";
      empty.textContent = `No source-grounded journeys are available for ${context.reference || "this passage"}.`;
      list.replaceChildren(empty);
    } else {
      list.replaceChildren();
    }
  }

  function discoveryCard(card, context, document, options) {
    const article = document.createElement("article");
    article.className = "companion-discovery-card";
    if (card.type === "walk_the_land") article.classList.add("companion-land-card");
    const headline = document.createElement("h4");
    headline.textContent = card.headline || "A detail worth noticing";
    const body = document.createElement("p");
    body.textContent = card.body || "";
    const meta = document.createElement("p");
    meta.className = "companion-discovery-meta";
    meta.textContent = `${titleCase(card.confidence || "low")} confidence · ${titleCase(card.interpretation_level || "fact")}`;
    const details = document.createElement("details");
    details.className = "companion-discovery-details";
    const summary = document.createElement("summary");
    summary.textContent = "Dig In";
    const evidence = evidenceForCard(card, context);
    const explanation = shouldShowExplanation(card.dig_in_summary, [
      card.headline,
      card.body,
      ...evidence.map((item) => item.claim),
    ])
      ? textParagraph(card.dig_in_summary, "companion-discovery-explanation", document)
      : null;
    const evidenceList = document.createElement("div");
    evidenceList.className = "companion-discovery-evidence";
    const evidenceHeading = document.createElement("h5");
    evidenceHeading.textContent = "Evidence";
    evidenceList.append(evidenceHeading);
    evidenceList.append(
      ...evidence
        .map((item) => evidenceDetail(item, document)),
    );
    const actions = document.createElement("div");
    actions.className = "companion-discovery-actions";
    const usefulActions = Array.isArray(card.dig_deeper_actions)
      ? card.dig_deeper_actions.filter((action) => action?.type !== "show_evidence")
      : [];
    const connectionChoices = findVerifiedConnections(
      card,
      context,
      options?.verifiedProjection,
      {narrativeExplorerEnabled: options?.narrativeExplorerEnabled === true},
    );
    usefulActions.push(...connectionChoices.map((route) => ({
      type: "explore_connection",
      target_id: route.id,
      route_identity: route.handoff_record_identity,
      passage_reference: context.reference,
      label: connectionChoices.length === 1
        ? "Explore this connection"
        : `Explore this connection: ${route.destination_passage} · ${titleCase(route.relationship_category)}`,
    })));
    if (usefulActions.length) {
      const actionsHeading = document.createElement("h5");
      actionsHeading.textContent = "Actions";
      actions.append(actionsHeading, ...usefulActions.map((action) => actionButton(action, document)));
    }
    details.append(summary);
    if (explanation) details.append(explanation);
    details.append(evidenceList);
    if (usefulActions.length) details.append(actions);
    article.append(headline, body, meta, details);
    return article;
  }

  function textParagraph(text, className, document) {
    const body = document.createElement("p");
    body.className = className;
    body.textContent = text;
    return body;
  }

  function shouldShowExplanation(summary, visibleText) {
    const normalized = normalizeText(summary);
    if (!normalized || isBoilerplate(normalized)) return false;
    const summaryWords = normalized.split(" ");
    for (const candidate of visibleText) {
      const candidateNormalized = normalizeText(candidate);
      if (!candidateNormalized) continue;
      if (normalized === candidateNormalized) return false;
      const candidateWords = candidateNormalized.split(" ");
      const shorter = Math.min(summaryWords.length, candidateWords.length);
      const longer = Math.max(summaryWords.length, candidateWords.length);
      const shared = new Set(summaryWords.filter((word) => candidateWords.includes(word))).size;
      const addedWords = Math.abs(summaryWords.length - candidateWords.length);
      if (addedWords <= 3 && shorter / longer >= 0.62 && shared / shorter >= 0.84) return false;
    }
    return true;
  }

  function normalizeText(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
  }

  function isBoilerplate(value) {
    return /^(this|these) (detail|details|fact|facts|context|evidence) (matters|is important|is significant)( here)?$/.test(value)
      || /^(it is|this is) (important|significant) (because|for) (the passage|the text|the reader)$/.test(value);
  }

  function evidenceForCard(card, context) {
    const wanted = new Set(Array.isArray(card.evidence_ids) ? card.evidence_ids : []);
    if (Array.isArray(context?.presentation_evidence)) {
      return context.presentation_evidence
        .filter((item) => wanted.has(item.id))
        .map((item) => ({
          ...item,
          sourceLabels: (item.sources || []).map((source) => source?.title || source?.id),
        }));
    }
    const bundle = context?.evidence_bundle;
    const sources = new Map(
      (Array.isArray(bundle?.provenance?.sources) ? bundle.provenance.sources : [])
        .map((source) => [source.id, source]),
    );
    return (Array.isArray(bundle?.evidence_items) ? bundle.evidence_items : [])
      .filter((item) => wanted.has(item.id))
      .map((item) => ({
        ...item,
        sourceLabels: (item.source_ids || []).map((id) => sources.get(id)?.title || id),
      }));
  }

  function evidenceDetail(item, document) {
    const detail = document.createElement("div");
    detail.className = "companion-evidence-detail";
    const claim = document.createElement("p");
    claim.textContent = item.claim || "";
    const provenance = document.createElement("small");
    const labels = Array.isArray(item.sourceLabels)
      ? [...new Set(item.sourceLabels.filter(Boolean))]
      : [];
    provenance.textContent = `${titleCase(item.category || "context")} · ${titleCase(item.confidence || "low")} confidence${labels.length ? ` · Sources: ${labels.join(", ")}` : ""}`;
    detail.append(claim, provenance);
    return detail;
  }

  function actionButton(action, document) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary companion-discovery-action";
    button.setAttribute("aria-label", action.label || "Explore");
    button.dataset.presentationAction = action.type || "";
    if (action.target_id) button.dataset.presentationTarget = action.target_id;
    if (action.reference) button.dataset.presentationReference = action.reference;
    if (action.type === "explore_connection") {
      button.dataset.presentationRouteId = action.target_id || "";
      button.dataset.presentationPassageReference = action.passage_reference || "";
      button.dataset.presentationObjectId = action.route_identity?.object_id || "";
      button.dataset.presentationRecordKind = action.route_identity?.record_kind || "";
      button.dataset.presentationRecordId = action.route_identity?.record_id || "";
    }
    button.textContent = action.label || "Explore";
    return button;
  }

  function titleCase(value) {
    return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  async function dispatchAction(button, options = {}) {
    const action = button?.dataset?.presentationAction || "";
    const target = button?.dataset?.presentationTarget || "";
    const openResource = options.openResource;
    if (typeof openResource !== "function") return false;

    if (action === "open_map" && target) {
      await openResource("maps", {
        trigger: button,
        mapFocus: {kind: "place", targetId: target, acknowledgeFocus: true},
      });
    } else if (action === "show_route" && target) {
      await openResource("maps", {
        trigger: button,
        mapFocus: {kind: "route", targetId: target, acknowledgeFocus: true},
      });
    } else if (action === "archaeology") {
      await openResource("archaeology", {trigger: button});
      if (target) await options.openArchaeologyDetail?.(target);
    } else if (action === "explore_language") {
      await openResource("word_study", {trigger: button});
    } else if (action === "explore_history") {
      await openResource("historical_context", {trigger: button});
    } else if (action === "related_passages") {
      await openResource("cross_references", {trigger: button});
    } else if (action === "explore_connection") {
      const identity = {
        object_id: button.dataset.presentationObjectId || "",
        record_kind: button.dataset.presentationRecordKind || "",
        record_id: button.dataset.presentationRecordId || "",
      };
      if (!options.narrativeExplorerEnabled || !isCompleteRecordIdentity(identity) || !button.dataset.presentationRouteId) {
        await openResource("cross_references", {trigger: button});
        return true;
      }
      let opened = false;
      try {
        opened = await openResource("narrative_explorer", {
          trigger: button,
          routeHandoff: {
            routeId: button.dataset.presentationRouteId,
            identity,
            passageReference: button.dataset.presentationPassageReference || "",
          },
        });
      } catch (_error) {
        opened = false;
      }
      if (opened !== true) await openResource("cross_references", {trigger: button});
    } else if (
      action === "explore_place"
      && target
      && options.mapPlaceIds?.has?.(target)
    ) {
      await openResource("maps", {
        trigger: button,
        mapFocus: {kind: "place", targetId: target, acknowledgeFocus: true},
      });
    } else if (
      ["explore_person", "explore_place", "explore_event", "explore_custom"].includes(action)
      && target
    ) {
      await openResource("canonical", {trigger: button});
      await options.openCanonicalDetail?.(target);
    } else {
      return false;
    }
    return true;
  }

  function findVerifiedConnections(card, context, projection, options = {}) {
    if (options.narrativeExplorerEnabled !== true) return [];
    const related = projection?.related_passages;
    const contextReference = normalizeReference(context?.reference);
    const projectionReference = normalizeReference(projection?.passage?.reference);
    if (
      !related
      || related.state !== "available"
      || related.query_status !== "complete"
      || !contextReference
      || !projectionReference
      || contextReference !== projectionReference
    ) return [];

    const citedIds = new Set(Array.isArray(card?.evidence_ids) ? card.evidence_ids : []);
    const identitiesByEvidence = new Map();
    (Array.isArray(context?.presentation_evidence) ? context.presentation_evidence : []).forEach((item) => {
      if (!citedIds.has(item?.id)) return;
      const identity = normalizeRecordIdentity(item?.ckl_record_identity);
      if (!identity) return;
      const key = recordIdentityKey(identity);
      const keys = identitiesByEvidence.get(item.id) || new Set();
      keys.add(key);
      identitiesByEvidence.set(item.id, keys);
    });
    const identities = new Map();
    identitiesByEvidence.forEach((keys, evidenceId) => {
      if (keys.size !== 1) return;
      const key = [...keys][0];
      const identity = (context.presentation_evidence || []).find((item) => {
        if (item?.id !== evidenceId) return false;
        const normalized = normalizeRecordIdentity(item?.ckl_record_identity);
        return normalized && recordIdentityKey(normalized) === key;
      })?.ckl_record_identity;
      const normalized = normalizeRecordIdentity(identity);
      if (normalized) identities.set(key, normalized);
    });
    if (!identities.size) return [];

    const matches = new Map();
    const ambiguousIds = new Set();
    const routeGroups = [
      [related.authored_relationships, "authored_ckl_relationship"],
      [related.evidence_backed_bridges, null],
    ];
    routeGroups.forEach(([routes, expectedProvenance]) => {
      (Array.isArray(routes) ? routes : []).forEach((route) => {
        if (!isConfirmedRoute(route, expectedProvenance)) return;
        const provenance = expectedProvenance || String(route.provenance || "");
        const routeIdentities = provenance === "authored_ckl_relationship"
          ? (Array.isArray(route.supporting_record_ids) ? route.supporting_record_ids : [])
            .map(parseStableRecordIdentity)
            .filter(Boolean)
          : (Array.isArray(route.supporting_records) ? route.supporting_records : [])
            .map((record) => normalizeRecordIdentity(record))
            .filter(Boolean);
        const identity = routeIdentities.find((candidate) => identities.has(recordIdentityKey(candidate)));
        if (!identity) return;
        if (matches.has(route.id)) {
          ambiguousIds.add(route.id);
          return;
        }
        matches.set(route.id, {...route, handoff_record_identity: identity});
      });
    });
    ambiguousIds.forEach((id) => matches.delete(id));
    return [...matches.values()].sort((left, right) => left.id.localeCompare(right.id));
  }

  function isConfirmedRoute(route, expectedProvenance) {
    if (!route || typeof route !== "object"
      || [route.id, route.source_passage, route.destination_passage, route.relationship_category, route.explanation]
        .some((value) => typeof value !== "string" || !value)
      || typeof route.uncertainty !== "string"
      || !route.uncertainty) return false;
    if (expectedProvenance) return route.provenance === expectedProvenance;
    return ["ckl_documented_claim", "ckl_documented_evidence", "ckl_documented_interpretive_note"]
      .includes(route.provenance);
  }

  function normalizeRecordIdentity(identity) {
    if (!identity || typeof identity !== "object") return null;
    const {object_id: objectId, record_kind: recordKind, record_id: recordId} = identity;
    if ([objectId, recordKind, recordId].some((value) => typeof value !== "string" || !value || value.trim() !== value)) return null;
    if (!["claim", "evidence"].includes(recordKind)) return null;
    return {object_id: objectId, record_kind: recordKind, record_id: recordId};
  }

  function isCompleteRecordIdentity(identity) {
    return normalizeRecordIdentity(identity) !== null;
  }

  function parseStableRecordIdentity(value) {
    if (typeof value !== "string" || !value.startsWith("ckl:")) return null;
    const hashIndex = value.indexOf("#", 4);
    if (hashIndex <= 4) return null;
    const objectId = value.slice(4, hashIndex);
    const remainder = value.slice(hashIndex + 1);
    const colonIndex = remainder.indexOf(":");
    if (colonIndex <= 0) return null;
    return normalizeRecordIdentity({
      object_id: objectId,
      record_kind: remainder.slice(0, colonIndex),
      record_id: remainder.slice(colonIndex + 1),
    });
  }

  function recordIdentityKey(identity) {
    return JSON.stringify([identity.object_id, identity.record_kind, identity.record_id]);
  }

  function normalizeReference(value) {
    return String(value || "").trim().toLowerCase()
      .replace(/[\u2010-\u2015\u2212]/g, "-")
      .replace(/\s+/g, " ");
  }

  return Object.freeze({dispatchAction, findVerifiedConnections, render});
});
