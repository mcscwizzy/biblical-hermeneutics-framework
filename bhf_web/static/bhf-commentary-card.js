/* Read-only BHF Commentary v1.0 projection for the Study Companion. */
(function () {
  "use strict";

  const AVAILABILITY_LABELS = Object.freeze({
    AVAILABLE: "Context available",
    THIN: "Limited contextual evidence",
    DATA_GAP: "Contextual evidence not currently available",
  });
  const cache = new Map();
  const evidenceCache = new Map();

  function availabilityLabel(availability) {
    return AVAILABILITY_LABELS[availability] || "Context status not recorded";
  }

  function normalizePayload(payload) {
    const source = payload && typeof payload === "object" ? payload : {};
    const availability = Object.prototype.hasOwnProperty.call(source, "availability")
      ? source.availability
      : null;
    const verseReferences = Array.isArray(source.verse_references)
      ? source.verse_references.filter((value) => typeof value === "string" && value.trim())
      : [];
    const evidenceCount = Number(source.evidence_count);
    return Object.freeze({
      available: source.available === true,
      release: String(source.release || ""),
      book: String(source.book || ""),
      chapter: Number.isInteger(Number(source.chapter)) ? Number(source.chapter) : null,
      availability: typeof availability === "string" && availability ? availability : null,
      availabilityLabel: availabilityLabel(availability),
      commentary: typeof source.commentary === "string" ? source.commentary : "",
      verseReferences: Object.freeze(verseReferences),
      evidenceCount: Number.isFinite(evidenceCount) && evidenceCount >= 0 ? evidenceCount : null,
      reason: String(source.reason || ""),
    });
  }

  function chapterKey(selection) {
    return selection?.book && selection?.chapter
      ? `${selection.book} ${selection.chapter}`
      : "";
  }

  async function requestChapter(selection, signal) {
    const path = `/api/bhf-commentary/${encodeURIComponent(selection.book)}/${encodeURIComponent(selection.chapter)}`;
    if (typeof window.BHFApi?.requestJson === "function") {
      return normalizePayload(await window.BHFApi.requestJson(path, {signal}, "BHF Context could not be loaded."));
    }
    const response = await fetch(path, {signal, headers: {Accept: "application/json"}});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "BHF Context could not be loaded.");
    return normalizePayload(payload);
  }

  function normalizeEvidencePayload(payload) {
    const source = payload && typeof payload === "object" ? payload : {};
    const items = Array.isArray(source.evidence_items)
      ? source.evidence_items.filter((item) => item && typeof item === "object" && typeof item.id === "string")
      : [];
    const unavailableIds = Array.isArray(source.unavailable_ids)
      ? source.unavailable_ids.filter((value) => typeof value === "string" && value.trim())
      : [];
    const evidenceCount = Number(source.evidence_count);
    return Object.freeze({
      available: source.available === true,
      evidenceItems: Object.freeze(items),
      unavailableIds: Object.freeze(unavailableIds),
      evidenceCount: Number.isFinite(evidenceCount) && evidenceCount >= 0 ? evidenceCount : 0,
    });
  }

  async function requestEvidence(selection, signal) {
    const path = `/api/bhf-commentary/${encodeURIComponent(selection.book)}/${encodeURIComponent(selection.chapter)}/evidence`;
    if (typeof window.BHFApi?.requestJson === "function") {
      return normalizeEvidencePayload(await window.BHFApi.requestJson(path, {signal}, "BHF evidence could not be loaded."));
    }
    const response = await fetch(path, {signal, headers: {Accept: "application/json"}});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "BHF evidence could not be loaded.");
    return normalizeEvidencePayload(payload);
  }

  function elements(root) {
    return {
      card: root,
      availability: root.querySelector("[data-bhf-commentary-availability]"),
      reference: root.querySelector("[data-bhf-commentary-reference]"),
      status: root.querySelector("[data-bhf-commentary-status]"),
      body: root.querySelector("[data-bhf-commentary-body]"),
      meta: root.querySelector("[data-bhf-commentary-meta]"),
      verseRefs: root.querySelector("[data-bhf-commentary-verse-refs]"),
      evidenceCount: root.querySelector("[data-bhf-commentary-evidence-count]"),
      evidenceToggle: root.querySelector("[data-bhf-commentary-evidence-toggle]"),
      evidencePanel: root.querySelector("[data-bhf-commentary-evidence-panel]"),
      evidenceStatus: root.querySelector("[data-bhf-commentary-evidence-status]"),
      evidenceList: root.querySelector("[data-bhf-commentary-evidence-list]"),
    };
  }

  function clearChildren(element) {
    if (element) element.replaceChildren();
  }

  function setText(element, value) {
    if (element) element.textContent = value || "";
  }

  function resetEvidence(parts) {
    if (parts.evidenceToggle) {
      parts.evidenceToggle.hidden = true;
      parts.evidenceToggle.setAttribute("aria-expanded", "false");
    }
    if (parts.evidencePanel) parts.evidencePanel.hidden = true;
    setText(parts.evidenceStatus, "");
    clearChildren(parts.evidenceList);
  }

  function renderLoading(parts, selection) {
    parts.card.hidden = false;
    parts.card.dataset.state = "loading";
    parts.card.removeAttribute("data-availability");
    setText(parts.availability, "");
    setText(parts.reference, `${selection.book} ${selection.chapter}`);
    setText(parts.status, "Loading BHF context…");
    clearChildren(parts.body);
    parts.meta.hidden = true;
    resetEvidence(parts);
  }

  function renderUnavailable(parts, model) {
    parts.card.hidden = false;
    parts.card.dataset.state = "unavailable";
    parts.card.removeAttribute("data-availability");
    setText(parts.availability, "");
    setText(parts.reference, model.book && model.chapter ? `${model.book} ${model.chapter}` : "");
    setText(parts.status, model.available
      ? ""
      : "BHF Commentary is not available for this chapter.");
    clearChildren(parts.body);
    parts.meta.hidden = true;
    resetEvidence(parts);
  }

  function renderError(parts, selection) {
    parts.card.hidden = false;
    parts.card.dataset.state = "error";
    parts.card.removeAttribute("data-availability");
    setText(parts.availability, "");
    setText(parts.reference, `${selection.book} ${selection.chapter}`);
    setText(parts.status, "BHF Context is unavailable right now.");
    clearChildren(parts.body);
    parts.meta.hidden = true;
    resetEvidence(parts);
  }

  function renderReady(parts, model) {
    parts.card.hidden = false;
    parts.card.dataset.state = "ready";
    if (model.availability) parts.card.dataset.availability = model.availability;
    else parts.card.removeAttribute("data-availability");
    setText(parts.availability, model.availabilityLabel);
    setText(parts.reference, `${model.book} ${model.chapter}`);
    setText(parts.status, model.availability === "DATA_GAP"
      ? "BHF does not currently have anchored contextual evidence for this chapter."
      : model.availability === null
        ? "Context availability was not recorded for this release artifact."
        : "");
    setText(parts.body, model.commentary || "No commentary text is available.");
    clearChildren(parts.verseRefs);
    model.verseReferences.forEach((reference) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "bhf-commentary-verse-ref";
      button.dataset.bhfCommentaryVerseRef = reference;
      button.textContent = reference;
      button.setAttribute("aria-label", `Read ${reference}`);
      parts.verseRefs.appendChild(button);
    });
    if (model.verseReferences.length) {
      parts.verseRefs.setAttribute("aria-label", "Commentary verse references");
    } else {
      parts.verseRefs.removeAttribute("aria-label");
    }
    setText(parts.evidenceCount, model.evidenceCount === null
      ? ""
      : model.evidenceCount === 0
        ? "No anchored evidence cited"
        : `${model.evidenceCount} evidence item${model.evidenceCount === 1 ? "" : "s"}`);
    parts.meta.hidden = model.verseReferences.length === 0 && model.evidenceCount === null;
    resetEvidence(parts);
    if (parts.evidenceToggle && model.evidenceCount > 0) {
      parts.evidenceToggle.hidden = false;
    }
  }

  function readableCategory(category) {
    return String(category || "Context").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function confidenceLabel(confidence) {
    const labels = {high: "High confidence", medium: "Moderate confidence", low: "Limited confidence"};
    return labels[String(confidence || "").toLowerCase()] || "Confidence not recorded";
  }

  function renderEvidenceItem(item) {
    const article = document.createElement("article");
    article.className = "bhf-commentary-evidence-item";
    const heading = document.createElement("div");
    heading.className = "bhf-commentary-evidence-heading";
    const category = document.createElement("span");
    category.className = "bhf-commentary-evidence-category";
    category.textContent = readableCategory(item.category);
    heading.appendChild(category);
    const confidence = document.createElement("span");
    confidence.className = "bhf-commentary-evidence-confidence";
    confidence.textContent = confidenceLabel(item.confidence);
    heading.appendChild(confidence);
    article.appendChild(heading);

    const claim = document.createElement("p");
    claim.className = "bhf-commentary-evidence-claim";
    claim.textContent = item.claim || "Evidence claim unavailable.";
    article.appendChild(claim);

    if (item.dispute_status) {
      const dispute = document.createElement("p");
      dispute.className = "bhf-commentary-evidence-dispute";
      dispute.textContent = `Interpretation note: ${item.dispute_status}`;
      article.appendChild(dispute);
    }
    const anchors = Array.isArray(item.scripture_anchors) ? item.scripture_anchors : [];
    if (anchors.length) {
      const anchor = document.createElement("p");
      anchor.className = "bhf-commentary-evidence-anchor";
      anchor.textContent = `Scripture anchor: ${anchors.join(", ")}`;
      article.appendChild(anchor);
    }

    const details = document.createElement("details");
    details.className = "bhf-commentary-evidence-details";
    const summary = document.createElement("summary");
    summary.textContent = "Advanced details";
    details.appendChild(summary);
    const detailText = document.createElement("p");
    const sources = Array.isArray(item.sources) ? item.sources : [];
    const entities = Array.isArray(item.related_entities) ? item.related_entities : [];
    const levels = Array.isArray(item.interpretation_levels) ? item.interpretation_levels : [];
    detailText.textContent = [
      `Evidence ID: ${item.id}`,
      item.assertion_type ? `Assertion: ${item.assertion_type}` : "",
      levels.length ? `Allowed interpretation: ${levels.join(", ")}` : "",
      sources.length ? `Sources: ${sources.map((source) => source.title || source.id).join(", ")}` : "",
      entities.length ? `Related entities: ${entities.map((entity) => entity.title || entity.id).join(", ")}` : "",
    ].filter(Boolean).join("\n");
    details.appendChild(detailText);
    article.appendChild(details);
    const actions = renderToolActions(item);
    if (actions) article.appendChild(actions);
    return article;
  }

  function renderToolActions(item) {
    const actions = toolActions(item);
    if (!actions.length) return null;
    const container = document.createElement("div");
    container.className = "bhf-commentary-evidence-actions";
    actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary bhf-commentary-tool-action";
      button.dataset.bhfCommentaryTool = action.tool;
      if (action.target) button.dataset.bhfCommentaryTarget = action.target;
      if (action.query) button.dataset.bhfCommentaryQuery = action.query;
      button.textContent = action.label;
      button.setAttribute("aria-label", `${action.label} for supplied evidence`);
      container.appendChild(button);
    });
    return container;
  }

  function toolActions(item) {
    const actions = [];
    const seen = new Set();
    const add = (action) => {
      const key = `${action.tool}:${action.target || action.query || ""}`;
      if (seen.has(key)) return;
      seen.add(key);
      actions.push(action);
    };
    (Array.isArray(item.related_entities) ? item.related_entities : []).forEach((entity) => {
      const type = String(entity.type || "").toLowerCase();
      if (type === "place") add({tool: "maps", target: entity.id, label: "Open in Maps"});
      else if (["person", "people_group", "group", "institution"].includes(type)) {
        add({tool: "canonical", query: entity.title || entity.id, label: "Open in Context"});
      } else if (["event", "timeline"].includes(type)) {
        add({tool: "timeline", label: "Open Timeline"});
      }
    });
    const category = String(item.category || "").toLowerCase();
    const categoryActions = {
      archaeology: {tool: "archaeology", label: "Open Archaeology"},
      language: {tool: "word_study", label: "Open Lexicon"},
      chronology: {tool: "timeline", label: "Open Timeline"},
      history: {tool: "historical_context", label: "Open History"},
      culture: {tool: "cultural_context", label: "Open Culture"},
    };
    if (categoryActions[category]) add(categoryActions[category]);
    return actions;
  }

  function renderEvidence(parts, evidence) {
    if (!parts.evidencePanel) return;
    parts.evidencePanel.hidden = false;
    setText(parts.evidenceStatus, evidence.available ? "Evidence cited by this context" : "Cited evidence is unavailable in this release.");
    clearChildren(parts.evidenceList);
    evidence.evidenceItems.forEach((item) => parts.evidenceList.appendChild(renderEvidenceItem(item)));
    if (evidence.unavailableIds.length) {
      const unavailable = document.createElement("p");
      unavailable.className = "bhf-commentary-evidence-unavailable";
      unavailable.textContent = "Some referenced evidence is unavailable in this release.";
      parts.evidenceList.appendChild(unavailable);
    }
  }

  function parseVerseReference(reference, selection) {
    const match = String(reference || "").match(/^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$/);
    if (!match || match[1].trim() !== selection.book || Number(match[2]) !== Number(selection.chapter)) {
      return null;
    }
    const startVerse = Number(match[3]);
    const endVerse = Number(match[4] || startVerse);
    if (!Number.isInteger(startVerse) || !Number.isInteger(endVerse) || endVerse < startVerse) return null;
    return {
      startVerse,
      endVerse,
      selectedVerses: Array.from({length: endVerse - startVerse + 1}, (_value, index) => startVerse + index),
    };
  }

  function handleVerseReference(event, selection) {
    const button = event.target.closest?.("[data-bhf-commentary-verse-ref]");
    if (!button) return;
    const parsed = parseVerseReference(button.dataset.bhfCommentaryVerseRef, selection);
    if (!parsed) return;
    window.BHFStudySelection?.setSelection?.(parsed, "bhf-commentary");
    document.querySelector(`#chapter-reader [data-verse="${parsed.startVerse}"]`)
      ?.scrollIntoView?.({behavior: "smooth", block: "center"});
  }

  function handleEvidenceToggle(event, parts, selection, model, state) {
    const toggle = event.target.closest?.("[data-bhf-commentary-evidence-toggle]");
    if (!toggle || !model || model.evidenceCount <= 0) return;
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
    if (expanded) {
      parts.evidencePanel.hidden = true;
      return;
    }
    parts.evidencePanel.hidden = false;
    setText(parts.evidenceStatus, "Loading evidence…");
    const key = chapterKey(selection);
    const cached = evidenceCache.get(key);
    if (cached) {
      renderEvidence(parts, cached);
      return;
    }
    state.evidenceController?.abort();
    state.evidenceController = new AbortController();
    void requestEvidence(selection, state.evidenceController.signal)
      .then((evidence) => {
        evidenceCache.set(key, evidence);
        renderEvidence(parts, evidence);
      })
      .catch((error) => {
        if (error?.name === "AbortError") return;
        setText(parts.evidenceStatus, "Evidence is unavailable right now.");
        clearChildren(parts.evidenceList);
      });
  }

  function handleToolAction(event) {
    const button = event.target.closest?.("[data-bhf-commentary-tool]");
    if (!button) return;
    const tool = button.dataset.bhfCommentaryTool;
    const target = button.dataset.bhfCommentaryTarget;
    const query = button.dataset.bhfCommentaryQuery;
    const companion = window.BHFStudyCompanion;
    if (tool === "maps") {
      void companion?.openResource?.("maps", {trigger: button, mapFocus: {kind: "place", targetId: target}});
    } else if (tool === "canonical") {
      window.BHFWorkspace?.openCanonicalQuery?.(query || target);
    } else {
      void companion?.openResource?.(tool, {trigger: button});
    }
  }

  function handlePersonalAction(event) {
    const button = event.target.closest?.("[data-bhf-commentary-personal-action]");
    if (!button) return;
    const action = button.dataset.bhfCommentaryPersonalAction;
    if (action === "note" || action === "highlight" || action === "compare_translations") {
      void window.BHFStudyActions?.perform?.(action);
    }
  }

  function init(root) {
    const parts = elements(root);
    let sequence = 0;
    let controller = null;
    let currentModel = null;
    const state = {evidenceController: null};

    async function load(selection) {
      const key = chapterKey(selection);
      controller?.abort();
      if (!key) {
        root.hidden = true;
        return;
      }
      const requestSequence = ++sequence;
      renderLoading(parts, selection);
      try {
        let model = cache.get(key);
        if (!model) {
          controller = new AbortController();
          model = await requestChapter(selection, controller.signal);
          cache.set(key, model);
        }
        if (requestSequence !== sequence) return;
        currentModel = model;
        if (!model.available) renderUnavailable(parts, {...model, book: selection.book, chapter: selection.chapter});
        else renderReady(parts, model);
      } catch (error) {
        if (error?.name === "AbortError" || requestSequence !== sequence) return;
        renderError(parts, selection);
      }
    }

    root.addEventListener("click", (event) => {
      const selection = window.BHFStudySelection?.getState?.() || {};
      handleVerseReference(event, selection);
      handleEvidenceToggle(event, parts, selection, currentModel, state);
      handleToolAction(event);
      handlePersonalAction(event);
    });
    window.BHFStudySelection?.subscribe?.((selection) => { void load(selection); });
    return {
      load,
      render: (payload) => {
        currentModel = normalizePayload(payload);
        renderReady(parts, currentModel);
      },
    };
  }

  window.BHFCommentaryCard = Object.freeze({
    init,
    normalizePayload,
    normalizeEvidencePayload,
    availabilityLabel,
  });

  function boot() {
    const root = document.querySelector("[data-bhf-commentary-card]");
    if (root) init(root);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
