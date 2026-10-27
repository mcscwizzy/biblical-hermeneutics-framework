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
    const supportedCards = cards.filter((card) =>
      card && ["did_you_know", "walk_the_land"].includes(card.type));
    const visibleMapIds = new Set(
      (Array.isArray(context.locations?.items) ? context.locations.items : [])
        .filter((item) => item?.origin === "maps" && (item.map_focus_id || item.id))
        .map((item) => String(item.map_focus_id || item.id)),
    );
    const visibleCards = supportedCards.filter((card) => !isConsolidatedWalkCard(card, visibleMapIds));
    renderSection(panel, "[data-companion-land-section]", "[data-companion-land]", visibleCards, "walk_the_land", 1, context);
    renderSection(panel, "[data-companion-discoveries-section]", "[data-companion-discoveries]", visibleCards, "did_you_know", 3, context);
  }

  function isConsolidatedWalkCard(card, visibleMapIds) {
    if (card?.type !== "walk_the_land" || !visibleMapIds.size) return false;
    return (Array.isArray(card.dig_deeper_actions) ? card.dig_deeper_actions : [])
      .some((action) => action?.type === "open_map"
        && visibleMapIds.has(String(action.target_id || "")));
  }

  function renderSection(panel, sectionSelector, listSelector, cards, type, maximum, context) {
    const section = panel?.querySelector(sectionSelector);
    const list = panel?.querySelector(listSelector);
    if (!section || !list) return;
    const visibleCards = cards.filter((card) => card?.type === type).slice(0, maximum);
    section.hidden = visibleCards.length === 0;
    const document = list.ownerDocument || globalThis.document;
    list.replaceChildren(...visibleCards.map((card) => discoveryCard(card, context, document)));
  }

  function discoveryCard(card, context, document) {
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
    button.dataset.presentationAction = action.type || "";
    if (action.target_id) button.dataset.presentationTarget = action.target_id;
    if (action.reference) button.dataset.presentationReference = action.reference;
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

  return Object.freeze({dispatchAction, render});
});
