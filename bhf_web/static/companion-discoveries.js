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
    renderSection(panel, "[data-companion-land-section]", "[data-companion-land]", cards, "walk_the_land", 1, context);
    renderSection(panel, "[data-companion-discoveries-section]", "[data-companion-discoveries]", cards, "did_you_know", 3, context);
    renderSection(panel, "[data-companion-significance-section]", "[data-companion-significance]", cards, "why_it_matters", 1, context);
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
    if (card.type === "why_it_matters") article.classList.add("companion-significance-card");
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
    const evidenceList = document.createElement("div");
    evidenceList.className = "companion-discovery-evidence";
    evidenceList.replaceChildren(
      ...evidenceForCard(card, context)
        .map((item) => evidenceDetail(item, document)),
    );
    const actions = document.createElement("div");
    actions.className = "companion-discovery-actions";
    const usefulActions = Array.isArray(card.dig_deeper_actions)
      ? card.dig_deeper_actions.filter((action) => action?.type !== "show_evidence")
      : [];
    actions.replaceChildren(...usefulActions.map((action) => actionButton(action, document)));
    details.append(summary, evidenceList);
    if (usefulActions.length) details.append(actions);
    article.append(headline, body, meta, details);
    return article;
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
    const labels = Array.isArray(item.sourceLabels) ? item.sourceLabels.filter(Boolean) : [];
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
        mapFocus: {kind: "place", targetId: target},
      });
    } else if (action === "show_route" && target) {
      await openResource("maps", {
        trigger: button,
        mapFocus: {kind: "route", targetId: target},
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
        mapFocus: {kind: "place", targetId: target},
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
