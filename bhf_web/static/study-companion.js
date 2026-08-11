/* One passage-first companion presented as a mobile sheet or desktop dock. */
(function () {
  "use strict";

  const STATES = new Set(["closed", "peek", "study", "full"]);
  const RESOURCE_ACTIONS = new Set([
    "historical_context", "cultural_context", "literary_context", "original_audience",
    "covenant_context", "word_study", "cross_references", "people", "places",
    "themes", "archaeology", "timeline", "compare_translations",
  ]);
  const runtime = window.BHFRuntimeConfig || {};
  const breakpoint = Number(runtime.breakpoints?.tablet || 900);
  let panel;
  let shell;
  let overview;
  let actionStrip;
  let currentState = "closed";
  let currentMode = "passage";
  let currentResource = null;
  let selection = null;
  let availabilitySequence = 0;
  let availabilityTimer = null;
  let lastTrigger = null;

  function compactViewport() {
    return window.matchMedia(`(max-width: ${breakpoint}px)`).matches;
  }

  function init() {
    panel = document.querySelector("[data-study-companion]");
    shell = panel?.querySelector(".study-companion");
    overview = panel?.querySelector("[data-companion-overview]");
    actionStrip = document.querySelector("[data-passage-action-strip]");
    if (!panel || !shell || !overview) return;

    panel.querySelectorAll("[data-companion-state-control]").forEach((button) => {
      button.addEventListener("click", () => {
        lastTrigger = button;
        setState(button.dataset.companionStateControl);
      });
    });
    panel.querySelector("[data-companion-back]")?.addEventListener("click", () => showOverview());
    panel.querySelectorAll("[data-companion-action]").forEach((button) => {
      button.addEventListener("click", () => performPersonalAction(button.dataset.companionAction));
    });
    panel.addEventListener("click", handleCompanionClick);
    panel.querySelector("[data-companion-quick-ask]")?.addEventListener("submit", handleQuickAsk);
    actionStrip?.addEventListener("click", handlePassageAction);
    document.querySelector("[data-app-dock]")?.addEventListener("click", handlePrimaryNavigation);
    document.addEventListener("bhf:workspace-tab-changed", handleWorkspaceTabChanged);
    window.addEventListener("resize", handleViewportChange);
    document.addEventListener("keydown", handleEscape);

    if (window.BHFStudySelection?.subscribe) {
      window.BHFStudySelection.subscribe(handleSelectionChange);
    }
    if (!compactViewport()) setState("study", {focus: false});

    window.BHFStudyCompanion = Object.freeze({
      setState,
      showOverview,
      openResource,
      ensureResourceVisible,
      getState: () => ({state: currentState, mode: currentMode, resource: currentResource}),
    });
  }

  function setState(nextState, options = {}) {
    let normalized = STATES.has(nextState) ? nextState : "study";
    if (!compactViewport() && normalized === "closed") normalized = "study";
    currentState = normalized;
    panel.dataset.companionState = normalized;
    document.body.classList.toggle("companion-sheet-open", compactViewport() && normalized !== "closed" && normalized !== "peek");
    document.body.classList.toggle("companion-sheet-full", compactViewport() && normalized === "full");
    const peek = panel.querySelector("[data-companion-state-control='study'].companion-peek");
    if (peek) peek.hidden = normalized !== "peek";
    const close = panel.querySelector("[data-companion-state-control='closed']");
    if (close) close.setAttribute("aria-expanded", String(normalized !== "closed"));
    if (options.focus !== false && (normalized === "study" || normalized === "full")) {
      window.requestAnimationFrame(() => {
        const target = currentResource
          ? panel.querySelector("[data-companion-back]")
          : panel.querySelector("[data-companion-reference]");
        if (target) {
          target.setAttribute("tabindex", "-1");
          target.focus({preventScroll: true});
        }
      });
    }
    if (normalized === "closed" && lastTrigger?.isConnected) lastTrigger.focus({preventScroll: true});
  }

  function handleSelectionChange(nextSelection) {
    selection = nextSelection;
    currentMode = "passage";
    renderSelectionContext();
    if (selection?.hasPassageSelection && compactViewport() && currentState === "closed") {
      setState("peek", {focus: false});
    }
    if (!compactViewport()) showOverview({focus: false, reload: false});
    if (selection?.hasPassageSelection) {
      scheduleAvailabilityLoad();
    } else if (selection?.book && selection?.chapter && window.BHFStudyRecommendations) {
      renderRecommendations({});
      renderEntities([]);
    }
  }

  function renderSelectionContext() {
    if (!selection) return;
    const reference = selection.reference || "Chapter Companion";
    setText("[data-companion-reference]", reference);
    setText("[data-companion-peek-reference]", reference);
    setText("[data-passage-action-reference]", reference);
    const selectedText = selection.selectedText || (selection.chapter ? `Resources for ${reference}` : "");
    setText("[data-companion-selected-text]", selectedText);
    if (actionStrip) actionStrip.hidden = !selection.hasPassageSelection;
    renderSuggestions();
  }

  function scheduleAvailabilityLoad() {
    window.clearTimeout(availabilityTimer);
    const sequence = ++availabilitySequence;
    renderLoadingState();
    availabilityTimer = window.setTimeout(() => loadAvailability(sequence), 180);
    window.setTimeout(() => {
      if (sequence === availabilitySequence && panel.querySelector(".companion-skeleton")) {
        renderRecommendations({});
      }
    }, 420);
  }

  function renderLoadingState() {
    const recommended = panel.querySelector("[data-companion-recommended]");
    if (recommended) {
      recommended.replaceChildren(skeleton(), skeleton(), skeleton(), skeleton());
    }
    const deeper = panel.querySelector("[data-companion-deeper]");
    if (deeper) deeper.replaceChildren(skeleton("row"), skeleton("row"));
  }

  async function loadAvailability(sequence) {
    if (!selection?.book || !selection?.chapter || !window.BHFStudyRecommendations) return;
    const parameters = new URLSearchParams({
      book: selection.book,
      chapter: String(selection.chapter),
    });
    if (selection.startVerse) parameters.set("verse_start", String(selection.startVerse));
    if (selection.endVerse) parameters.set("verse_end", String(selection.endVerse));
    if (selection.selectedText) parameters.set("passage_text", selection.selectedText);
    const requests = await Promise.allSettled([
      requestJson(`/api/commentary/${encodeURIComponent(selection.book)}/${selection.chapter}`),
      requestJson("/api/lexicon/diagnostics"),
      requestJson(`/api/maps/places-for-passage?${parameters}`),
      requestJson(`/api/maps/routes-for-passage?${parameters}`),
      requestJson(`/api/archaeology/for-passage?${parameters}&limit=6`),
      requestJson(`/api/canonical/entities-for-passage?${parameters}&limit=12`),
    ]);
    if (sequence !== availabilitySequence) return;

    const value = (index) => requests[index].status === "fulfilled" ? requests[index].value : null;
    const commentary = value(0);
    const lexicon = value(1);
    const places = value(2);
    const routes = value(3);
    const archaeology = value(4);
    const canonical = value(5);
    const entities = Array.isArray(canonical?.results)
      ? canonical.results.filter((item) => ["person", "place", "theme"].includes(String(item.type || "").toLowerCase()))
      : [];
    const archaeologyItems = archaeology?.items || archaeology?.results || archaeology?.evidence || [];
    const availability = {
      commentary: commentary ? Boolean(commentary.available && commentary.entries?.length) : false,
      word_study: lexicon ? Boolean(lexicon.lexical_database_found && lexicon.verse_word_count > 0) : false,
      maps: Boolean(Number(places?.match_count || 0) + Number(routes?.match_count || 0)),
      archaeology: Array.isArray(archaeologyItems)
        ? archaeologyItems.length > 0
        : Number(archaeology?.match_count || archaeology?.result_count || 0) > 0,
      people: entities.some((item) => String(item.type).toLowerCase() === "person"),
      places: entities.some((item) => String(item.type).toLowerCase() === "place") || Number(places?.match_count || 0) > 0,
      mapCount: Number(places?.match_count || 0) + Number(routes?.match_count || 0),
      archaeologyCount: Array.isArray(archaeologyItems) ? archaeologyItems.length : Number(archaeology?.match_count || 0),
      peopleCount: entities.filter((item) => String(item.type).toLowerCase() === "person").length,
      placeCount: entities.filter((item) => String(item.type).toLowerCase() === "place").length,
      themeCount: entities.filter((item) => String(item.type).toLowerCase() === "theme").length,
      canonicalCount: Number(canonical?.results?.length || 0),
    };
    renderRecommendations(availability);
    renderEntities(entities);
  }

  function renderRecommendations(availability = {}) {
    const engine = window.BHFStudyRecommendations;
    const ranking = engine.rank(selection, availability);
    const recommended = panel.querySelector("[data-companion-recommended]");
    const deeper = panel.querySelector("[data-companion-deeper]");
    const reason = panel.querySelector("[data-companion-recommendation-reason]");
    if (reason) reason.textContent = ranking.reason;
    if (recommended) recommended.replaceChildren(...ranking.recommended.map((resource) => resourceCard(resource)));
    if (deeper) deeper.replaceChildren(...ranking.deeper.map((resource) => resourceRow(resource)));
    setText("[data-companion-resource-count]", `${ranking.all.length} study resources available`);
  }

  function renderExploreOverview() {
    const engine = window.BHFStudyRecommendations;
    const ids = ["maps", "archaeology", "people", "places", "themes", "timeline", "commentary", "canonical"];
    const resources = ids.map((id) => ({id, ...engine.resources[id]})).filter((item) => item.label);
    panel.querySelector("[data-companion-recommended]")?.replaceChildren(...resources.slice(0, 4).map(resourceCard));
    panel.querySelector("[data-companion-deeper]")?.replaceChildren(...resources.slice(4).map(resourceRow));
    setText("[data-companion-recommendation-reason]", "Browse BHF’s local research collections independently of a selected passage.");
    setText("[data-companion-resource-count]", `${resources.length} research collections`);
    panel.querySelector("[data-companion-entities-section]")?.setAttribute("hidden", "");
  }

  function renderEntities(entities) {
    const section = panel.querySelector("[data-companion-entities-section]");
    const list = panel.querySelector("[data-companion-entities]");
    if (!section || !list || currentMode !== "passage") return;
    const useful = entities.slice(0, 6);
    section.hidden = useful.length === 0;
    list.replaceChildren(...useful.map((entity) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "companion-entity-chip";
      button.dataset.companionEntity = entity.title || entity.name || entity.id;
      const label = document.createElement("strong");
      label.textContent = entity.title || entity.name || entity.id;
      const type = document.createElement("span");
      type.textContent = String(entity.type || "Context").replaceAll("_", " ");
      button.append(label, type);
      return button;
    }));
  }

  function renderSuggestions() {
    const target = panel.querySelector("[data-companion-suggestions]");
    const engine = window.BHFStudyRecommendations;
    if (!target || !engine) return;
    target.replaceChildren(...engine.suggestedQuestions(selection).map((question) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "companion-suggestion";
      button.dataset.companionQuestion = question;
      button.textContent = question;
      return button;
    }));
  }

  function resourceCard(resource) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "companion-resource-card";
    button.dataset.companionResource = resource.id;
    const icon = document.createElement("span");
    icon.className = "companion-resource-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = resource.icon || "◇";
    const content = document.createElement("span");
    const label = document.createElement("strong");
    label.textContent = resource.label;
    const description = document.createElement("small");
    description.textContent = resource.description || "Open this resource";
    content.append(label, description);
    const arrow = document.createElement("span");
    arrow.setAttribute("aria-hidden", "true");
    arrow.textContent = "→";
    button.append(icon, content, arrow);
    return button;
  }

  function resourceRow(resource) {
    const row = resourceCard(resource);
    row.classList.replace("companion-resource-card", "companion-resource-row");
    return row;
  }

  function skeleton(kind = "card") {
    const item = document.createElement("div");
    item.className = `companion-skeleton companion-skeleton-${kind}`;
    item.setAttribute("aria-hidden", "true");
    return item;
  }

  function showOverview(options = {}) {
    currentResource = null;
    delete shell.dataset.companionResource;
    currentMode = options.mode || currentMode || "passage";
    shell.classList.remove("is-resource-detail");
    overview.hidden = false;
    panel.querySelector("[data-companion-back]").hidden = true;
    if (currentMode === "explore") {
      setText("[data-companion-reference]", "Explore BHF");
      setText("[data-companion-selected-text]", "Browse people, places, themes, maps, archaeology, commentary, and canonical knowledge.");
      renderExploreOverview();
    } else {
      renderSelectionContext();
      if (options.reload !== false) scheduleAvailabilityLoad();
    }
    setState(options.state || "study", {focus: options.focus});
  }

  async function openResource(resourceId, options = {}) {
    const engine = window.BHFStudyRecommendations;
    const resource = engine?.resources?.[resourceId] || {label: options.label || "Study Resource"};
    ensureResourceVisible(resourceId, resource);

    const actions = window.BHFStudyActions;
    if (resourceId === "commentary") {
      actions?.openWorkspaceTab?.("commentary");
    } else if (resourceId === "canonical") {
      actions?.openWorkspaceTab?.("context");
    } else if (resourceId === "maps") {
      await actions?.perform?.("open_map_panel");
    } else if (resourceId === "ask") {
      actions?.openWorkspaceTab?.("ask");
      window.BHFWorkspace?.focusAskPanel?.();
    } else if (RESOURCE_ACTIONS.has(resourceId)) {
      await actions?.perform?.(resourceId);
    }
  }

  function ensureResourceVisible(resourceId, resource = null) {
    const engine = window.BHFStudyRecommendations;
    const resolved = resource || engine?.resources?.[resourceId] || {label: "Study Resource"};
    currentResource = resourceId;
    shell.dataset.companionResource = resourceId;
    shell.classList.add("is-resource-detail");
    overview.hidden = true;
    const back = panel.querySelector("[data-companion-back]");
    if (back) {
      back.hidden = false;
      back.setAttribute("aria-label", `Back to ${selection?.reference || "passage"} overview`);
    }
    setText("[data-companion-reference]", resolved.label);
    setText("[data-companion-selected-text]", selection?.reference || "Study Companion");
    setState(compactViewport() ? "full" : "study");
  }

  function handleCompanionClick(event) {
    const resource = event.target.closest("[data-companion-resource]");
    if (resource) {
      openResource(resource.dataset.companionResource);
      return;
    }
    const route = event.target.closest("[data-companion-route]");
    if (route) {
      openResource(route.dataset.companionRoute);
      return;
    }
    const question = event.target.closest("[data-companion-question]");
    if (question) {
      openAsk(question.dataset.companionQuestion);
      return;
    }
    const entity = event.target.closest("[data-companion-entity]");
    if (entity) {
      openResource("canonical").then(() => window.BHFStudyActions?.openCanonicalQuery?.(entity.dataset.companionEntity));
    }
  }

  function handleQuickAsk(event) {
    event.preventDefault();
    const input = event.currentTarget.elements.question;
    const question = String(input?.value || "").trim();
    openAsk(question);
  }

  function openAsk(question) {
    const field = document.querySelector('.ask-form [name="question"]');
    if (field && question) {
      field.value = question;
      field.dispatchEvent(new Event("input", {bubbles: true}));
    }
    openResource("ask").then(() => field?.focus({preventScroll: true}));
  }

  async function performPersonalAction(action) {
    if (action === "note") {
      await window.BHFStudyActions?.perform?.("note");
      currentResource = "note";
      shell.dataset.companionResource = "note";
      shell.classList.add("is-resource-detail");
      overview.hidden = true;
      panel.querySelector("[data-companion-back]").hidden = false;
      setText("[data-companion-reference]", "Note");
      setState(compactViewport() ? "full" : "study");
    } else if (action === "save") {
      await window.BHFStudyActions?.savePassage?.();
      const button = panel.querySelector('[data-companion-action="save"]');
      if (button) button.textContent = "✓ Saved";
    }
  }

  function handlePassageAction(event) {
    const button = event.target.closest("[data-passage-action]");
    if (!button) return;
    lastTrigger = button;
    const action = button.dataset.passageAction;
    if (action === "explore") showOverview({mode: "passage"});
    else if (action === "ask") openAsk("");
    else if (action === "note") performPersonalAction("note");
    else if (action === "highlight") window.BHFStudyActions?.perform?.("highlight");
    else if (action === "more") window.BHFStudyActions?.openAdvancedMenu?.(button);
  }

  function handlePrimaryNavigation(event) {
    const button = event.target.closest("[data-app-section]");
    if (!button) return;
    const section = button.dataset.appSection;
    if (section === "bible") {
      currentMode = "passage";
      showOverview({focus: false, reload: false, state: compactViewport() ? "closed" : "study"});
    } else if (section === "explore") {
      showOverview({mode: "explore"});
    } else if (section === "notes") {
      currentResource = "my-study";
      shell.dataset.companionResource = "my-study";
      shell.classList.add("is-resource-detail");
      overview.hidden = true;
      panel.querySelector("[data-companion-back]").hidden = false;
      setText("[data-companion-reference]", "My Study");
      setText("[data-companion-selected-text]", "Notes, highlights, and saved studies on this device");
      window.BHFStudyActions?.openWorkspaceTab?.("notes");
      setState(compactViewport() ? "full" : "study");
    }
  }

  function handleWorkspaceTabChanged(event) {
    if (!shell || !event.detail?.tabId || !["ask", "lexicon", "context", "commentary", "notes", "highlights", "saved", "maps"].includes(event.detail.tabId)) return;
    if (!currentResource) return;
    shell.classList.add("is-resource-detail");
    overview.hidden = true;
  }

  function handleViewportChange() {
    if (!compactViewport()) setState("study", {focus: false});
    else if (currentState === "study" && !currentResource) setState("study", {focus: false});
  }

  function handleEscape(event) {
    if (event.key !== "Escape" || !compactViewport()) return;
    if (currentResource) showOverview();
    else if (currentState === "full") setState("study");
    else if (currentState === "study") setState(selection?.hasPassageSelection ? "peek" : "closed");
  }

  function setText(selector, value) {
    const target = panel?.querySelector(selector) || document.querySelector(selector);
    if (target) target.textContent = String(value || "");
  }

  async function requestJson(url) {
    if (window.BHFApi?.requestJson) {
      return window.BHFApi.requestJson(url, {}, "Resource availability check failed.");
    }
    const response = await fetch(url, {headers: {Accept: "application/json"}});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
