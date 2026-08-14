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
  let contextController = null;
  let sheetController = null;
  let resourceRouter = null;
  let saveStateController = null;
  let historyController = null;
  let viewportController = null;
  let lastTrigger = null;
  let lastResourceTrigger = null;
  let lastCompact = null;
  let resizeFrame = null;

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
        const requestedState = button.dataset.companionStateControl;
        const nextState = requestedState === "full" && currentState === "full"
          ? "study"
          : requestedState;
        setState(nextState, {source: "control"});
      });
    });
    panel.querySelector("[data-companion-back]")?.addEventListener("click", navigateBackFromResource);
    panel.querySelectorAll("[data-companion-action]").forEach((button) => {
      button.addEventListener("click", () => performPersonalAction(button.dataset.companionAction));
    });
    panel.addEventListener("click", handleCompanionClick);
    panel.querySelector("[data-companion-quick-ask]")?.addEventListener("submit", handleQuickAsk);
    actionStrip?.addEventListener("click", handlePassageAction);
    document.querySelector("[data-app-dock]")?.addEventListener("click", handlePrimaryNavigation);
    document.addEventListener("bhf:workspace-tab-changed", handleWorkspaceTabChanged);
    document.addEventListener("bhf:companion-context-invalidated", handleContextInvalidated);
    window.addEventListener("resize", handleViewportChange);
    document.addEventListener("keydown", handleEscape);

    sheetController = window.BHFCompanionSheet?.create?.({
      panel,
      compactViewport,
      getState: () => currentState,
      setState,
    });
    resourceRouter = window.BHFResourceRouter?.create?.({
      panel,
      shell,
      getSelection: () => selection,
      getContext: () => contextController?.getRecord?.().context || null,
      getContextRecord: () => contextController?.getRecord?.(),
      openLegacy: openLegacyResource,
    });

    contextController = window.BHFCompanionContextController?.create?.({
      onLoading: () => {
        if (currentMode !== "passage") return;
        renderLoadingState();
        renderEntities([]);
      },
      onReady: (context) => {
        if (currentMode !== "passage") return;
        renderRecommendations(context);
        renderEntities([
          ...(context.entities?.people || []),
          ...(context.entities?.places || []),
          ...(context.entities?.themes || []),
        ]);
        if (currentResource && currentMode === "passage") {
          void resourceRouter?.open?.(currentResource, {mode: currentMode});
        }
      },
      onError: (message) => {
        if (currentMode !== "passage") return;
        renderAvailabilityError(message);
        if (currentResource && currentMode === "passage") {
          void resourceRouter?.open?.(currentResource, {mode: currentMode});
        }
      },
    });

    saveStateController = window.BHFSavedPassageState?.create?.({
      loadStudies: (currentSelection, options) => {
        const loadStudies = window.BHFStudyActions?.getSavedStudies;
        if (typeof loadStudies !== "function") {
          return Promise.reject(new Error("Saved studies are unavailable."));
        }
        return loadStudies(currentSelection, options);
      },
      onChange: renderSaveState,
    });
    historyController = window.BHFCompanionHistory?.create?.({apply: applyHistoryState});
    viewportController = window.BHFCompanionViewport?.create?.({
      panel,
      compactViewport,
      ensureVisible: () => {
        if (currentState === "closed" || currentState === "peek") {
          setState("study", {focus: false, history: false, source: "keyboard"});
          historyController?.replace(historySnapshot());
        }
      },
    });

    lastCompact = compactViewport();
    setState(lastCompact ? currentState : "study", {focus: false, history: false});
    historyController?.initialize(historySnapshot());
    if (window.BHFStudySelection?.subscribe) {
      window.BHFStudySelection.subscribe(handleSelectionChange);
    }

    window.BHFStudyCompanion = Object.freeze({
      setState,
      showOverview,
      openResource,
      ensureResourceVisible,
      showPersonalResource,
      getState: () => ({state: currentState, mode: currentMode, resource: currentResource}),
      getContext: () => contextController?.getRecord?.().context || null,
      getContextRecord: () => contextController?.getRecord?.(),
    });
  }

  function setState(nextState, options = {}) {
    const previousState = currentState;
    let normalized = STATES.has(nextState) ? nextState : "study";
    if (!compactViewport() && normalized === "closed") normalized = "study";
    currentState = normalized;
    panel.dataset.companionState = normalized;
    panel.setAttribute("aria-expanded", String(normalized !== "closed"));
    document.body.classList.toggle("companion-sheet-open", compactViewport() && normalized !== "closed" && normalized !== "peek");
    document.body.classList.toggle("companion-sheet-peek", compactViewport() && normalized === "peek");
    document.body.classList.toggle("companion-sheet-full", normalized === "full");
    const peek = panel.querySelector("[data-companion-state-control='study'].companion-peek");
    if (peek) peek.hidden = normalized !== "peek";
    panel.querySelectorAll("[data-companion-state-control]").forEach((control) => {
      control.removeAttribute("aria-pressed");
      control.setAttribute("aria-controls", panel.id);
      if (control.dataset.companionStateControl === "full") {
        const expanded = normalized === "full";
        const label = expanded
          ? "Collapse Study Companion"
          : "Expand Study Companion";
        control.setAttribute("aria-expanded", String(expanded));
        control.setAttribute("aria-label", label);
        control.setAttribute("title", label);
      } else if (control.dataset.companionStateControl === "study") {
        control.setAttribute("aria-expanded", String(normalized === "study" || normalized === "full"));
      } else {
        control.removeAttribute("aria-expanded");
      }
    });
    panel.inert = normalized === "closed";
    updateReaderAccessibility(normalized);
    if (options.focus !== false && (normalized === "study" || normalized === "full")) {
      window.requestAnimationFrame(() => {
        const target = currentResource
          ? panel.querySelector("[data-companion-back]")
          : panel.querySelector("[data-companion-reference]");
        if (target) {
          if (target.matches("button, a[href], input, select, textarea, [tabindex]:not([tabindex='-1'])")) {
            target.removeAttribute("tabindex");
          } else {
            target.setAttribute("tabindex", "-1");
          }
          target.focus({preventScroll: true});
        }
      });
    }
    if (normalized === "closed" && lastTrigger?.isConnected) lastTrigger.focus({preventScroll: true});
    const transientSource = ["drag", "drag-cancel", "selection", "breakpoint", "keyboard"].includes(options.source);
    if (historyController && options.history !== false && !transientSource && !currentResource && previousState !== normalized) {
      const expanding = stateIndex(normalized) > stateIndex(previousState);
      if (expanding) historyController.push(historySnapshot());
      else historyController.replace(historySnapshot());
    } else if (historyController && options.source === "drag" && previousState !== normalized) {
      historyController.replace(historySnapshot());
    } else if (historyController && currentResource && options.source === "control" && previousState !== normalized) {
      historyController.replace(historySnapshot());
    }
  }

  function handleSelectionChange(nextSelection) {
    selection = nextSelection;
    saveStateController?.setSelection(selection);
    const contextChange = contextController?.setSelection?.(selection, {load: currentMode !== "explore"}) || {changed: false};
    if (currentMode === "explore") return;
    currentMode = "passage";
    if (currentResource) renderResourceHeader(currentResource);
    else renderSelectionContext();
    if (selection?.hasPassageSelection && compactViewport() && currentState === "closed") {
      setState("peek", {focus: false, history: false, source: "selection"});
      historyController?.replace(historySnapshot());
    }
    if (selection?.book && selection?.chapter) {
      if (currentResource && contextChange.changed) {
        void resourceRouter?.open?.(currentResource, {mode: currentMode});
      }
    } else {
      renderRecommendations({resources: {}});
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

  function renderLoadingState() {
    const recommended = panel.querySelector("[data-companion-recommended]");
    if (recommended) {
      const status = document.createElement("p");
      status.className = "visually-hidden";
      status.setAttribute("role", "status");
      status.textContent = `Loading study resources for ${selection?.reference || "this passage"}…`;
      recommended.replaceChildren(status, skeleton(), skeleton(), skeleton(), skeleton());
    }
    const deeper = panel.querySelector("[data-companion-deeper]");
    if (deeper) deeper.replaceChildren(skeleton("row"), skeleton("row"));
  }

  function renderRecommendations(availability = {}) {
    const engine = window.BHFStudyRecommendations;
    const ranking = engine.rank(selection, availability);
    const recommended = panel.querySelector("[data-companion-recommended]");
    const deeper = panel.querySelector("[data-companion-deeper]");
    const reason = panel.querySelector("[data-companion-recommendation-reason]");
    if (reason) reason.textContent = ranking.reason;
    if (recommended) {
      recommended.replaceChildren(...ranking.recommended.map((resource) => resourceCard(resource)));
      if (!ranking.recommended.length) recommended.append(emptyAvailability("No verified resources are available for this selection."));
    }
    if (deeper) deeper.replaceChildren(...ranking.deeper.map((resource) => resourceRow(resource)));
    setText("[data-companion-resource-count]", `${ranking.all.length} study resources available`);
  }

  function renderAvailabilityError(message) {
    const recommended = panel.querySelector("[data-companion-recommended]");
    const deeper = panel.querySelector("[data-companion-deeper]");
    recommended?.replaceChildren(emptyAvailability(message, true));
    deeper?.replaceChildren();
    setText("[data-companion-recommendation-reason]", "Local resources remain usable even when availability cannot be refreshed.");
    setText("[data-companion-resource-count]", "Resource availability unknown");
    renderEntities([]);
  }

  function emptyAvailability(message, error = false) {
    const item = document.createElement("p");
    item.className = error ? "companion-availability-error" : "companion-availability-empty";
    if (error) item.setAttribute("role", "alert");
    item.textContent = message;
    return item;
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
      button.dataset.companionEntity = entity.id || entity.title || entity.name;
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
    description.textContent = resource.count > 0
      ? `${resource.description || "Open this resource"} · ${resource.count}`
      : resource.description || "Open this resource";
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
    if (currentResource && options.history !== false) {
      historyController?.backFromResource(() => showOverview({...options, history: false}));
      return;
    }
    const previousResourceTrigger = lastResourceTrigger;
    resourceRouter?.close?.();
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
      if (options.reload !== false || !contextController?.matchesSelection?.()) contextController?.schedule?.();
    }
    setState(options.state || "study", {
      focus: options.focus,
      history: options.history,
      source: options.source || "navigation",
    });
    if (options.focus !== false && previousResourceTrigger?.isConnected) {
      window.requestAnimationFrame(() => previousResourceTrigger.focus({preventScroll: true}));
    }
  }

  async function openResource(resourceId, options = {}) {
    if (options.trigger) lastResourceTrigger = options.trigger;
    if (options.mode) currentMode = options.mode;
    if (resourceId === "maps") {
      await openLegacyResource(resourceId);
      if (options.history !== false && historyController?.current()?.resource !== resourceId) {
        historyController?.push(historySnapshot());
      }
      return;
    }
    const engine = window.BHFStudyRecommendations;
    const resource = engine?.resources?.[resourceId] || {label: options.label || "Study Resource"};
    ensureResourceVisible(resourceId, resource, {state: options.state});
    if (options.history !== false && historyController?.current()?.resource !== resourceId) {
      historyController?.push(historySnapshot());
    }

    if (await resourceRouter?.open?.(resourceId, {mode: currentMode})) return;
    openLegacyResource(resourceId);
  }

  async function openLegacyResource(resourceId) {
    const actions = window.BHFStudyActions;
    if (resourceId === "commentary") {
      actions?.openWorkspaceTab?.("commentary");
    } else if (resourceId === "canonical") {
      actions?.openWorkspaceTab?.("context");
    } else if (resourceId === "maps") {
      // Maps is one of the legacy workspace panes nested inside the companion.
      // Mark it as the active resource and keep the companion visible so the
      // pane is not hidden (or left inside an inert, closed mobile sheet).
      ensureResourceVisible(
        resourceId,
        window.BHFStudyRecommendations?.resources?.maps,
        {focus: false},
      );
      const selectedContext = window.BHFStudySelection?.getState?.();
      const mapContext = currentMode === "explore"
        ? {mode: "browse"}
        : selectedContext;
      if (typeof window.BHFMaps?.openMapPanel === "function") {
        await window.BHFMaps.openMapPanel(
          mapContext?.book && mapContext?.chapter ? mapContext : {mode: "browse"},
        );
      } else {
        // The MapPanel module can still be loading on a fresh page. The shared
        // action bridge queues the context until it becomes available.
        await actions?.perform?.("open_map_panel", mapContext);
      }
    } else if (resourceId === "ask") {
      actions?.openWorkspaceTab?.("ask");
      window.BHFWorkspace?.focusAskPanel?.();
    } else if (RESOURCE_ACTIONS.has(resourceId)) {
      await actions?.perform?.(resourceId);
    }
  }

  function ensureResourceVisible(resourceId, resource = null, options = {}) {
    const engine = window.BHFStudyRecommendations;
    const resolved = resource || engine?.resources?.[resourceId] || {label: "Study Resource"};
    currentResource = resourceId;
    resourceRouter?.close?.();
    shell.dataset.companionResource = resourceId;
    shell.classList.add("is-resource-detail");
    overview.hidden = true;
    const back = panel.querySelector("[data-companion-back]");
    if (back) {
      back.hidden = false;
      back.setAttribute("aria-label", `Back to ${selection?.reference || "passage"} overview`);
    }
    renderResourceHeader(resourceId, resolved);
    setState(options.state || (compactViewport() ? "full" : "study"), {
      focus: options.focus,
      history: false,
    });
  }

  function showPersonalResource(resourceId, label) {
    const shouldPush = historyController?.current?.()?.resource !== resourceId;
    ensureResourceVisible(resourceId, {label: label || "My Study"});
    if (shouldPush) historyController?.push(historySnapshot());
  }

  function handleCompanionClick(event) {
    const resource = event.target.closest("[data-companion-resource]");
    if (resource && resource !== shell) {
      openResource(resource.dataset.companionResource, {trigger: resource});
      return;
    }
    const route = event.target.closest("[data-companion-route]");
    if (route) {
      openResource(route.dataset.companionRoute, {trigger: route});
      return;
    }
    const question = event.target.closest("[data-companion-question]");
    if (question) {
      openAsk(question.dataset.companionQuestion);
      return;
    }
    const entity = event.target.closest("[data-companion-entity]");
    if (entity) {
      openResource("canonical", {trigger: entity})
        .then(() => resourceRouter?.openCanonicalDetail?.(entity.dataset.companionEntity));
    }
  }

  function handleQuickAsk(event) {
    event.preventDefault();
    const input = event.currentTarget.elements.question;
    const question = String(input?.value || "").trim();
    openAsk(question);
  }

  function openAsk(question) {
    window.BHFStudyActions?.syncAskSelection?.();
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
      showPersonalResource("note", "Note");
    } else if (action === "save") {
      const button = panel.querySelector('[data-companion-action="save"]');
      if (
        button?.dataset.saved === "true"
        || button?.disabled
        || selection?.hasPassageSelection !== true
      ) return;
      const requestedPassageKey = window.BHFSavedPassageState?.passageKey?.(selection);
      renderSaveState({status: "saving", saving: true, selection});
      try {
        await window.BHFStudyActions?.savePassage?.();
      } catch (_error) {
        if (window.BHFSavedPassageState?.passageKey?.(selection) === requestedPassageKey) {
          renderSaveState({status: "unavailable", unavailable: true, selection});
        }
      }
    }
  }

  function handlePassageAction(event) {
    const button = event.target.closest("[data-passage-action]");
    if (!button) return;
    lastTrigger = button;
    const action = button.dataset.passageAction;
    if (action === "explore") showOverview({mode: "passage", source: "navigation"});
    else if (action === "ask") openAsk("");
    else if (action === "note") performPersonalAction("note");
    else if (action === "highlight") window.BHFStudyActions?.perform?.("highlight");
  }

  function handlePrimaryNavigation(event) {
    const button = event.target.closest("[data-app-section]");
    if (!button) return;
    lastTrigger = button;
    const section = button.dataset.appSection;
    if (section === "bible") {
      currentMode = "passage";
      showOverview({focus: false, reload: false, state: compactViewport() ? "closed" : "study", history: false});
      historyController?.replace(historySnapshot());
    } else if (section === "explore") {
      showOverview({mode: "explore", history: false});
      historyController?.replace(historySnapshot());
    } else if (section === "notes") {
      currentResource = "my-study";
      shell.dataset.companionResource = "my-study";
      shell.classList.add("is-resource-detail");
      overview.hidden = true;
      panel.querySelector("[data-companion-back]").hidden = false;
      setText("[data-companion-reference]", "My Study");
      setText("[data-companion-selected-text]", "Notes, highlights, and saved studies on this device");
      setState(compactViewport() ? "full" : "study", {history: false});
      if (historyController?.current?.()?.resource !== "my-study") {
        historyController?.push(historySnapshot());
      }
    }
  }

  function handleWorkspaceTabChanged(event) {
    if (!shell || !event.detail?.tabId || !["ask", "lexicon", "context", "commentary", "notes", "highlights", "saved", "maps"].includes(event.detail.tabId)) return;
    if (!currentResource) return;
    panel.querySelector("[data-companion-resource-host]")?.setAttribute("hidden", "");
    shell.classList.remove("is-native-resource");
    shell.classList.add("is-resource-detail");
    overview.hidden = true;
  }

  function handleViewportChange() {
    window.cancelAnimationFrame(resizeFrame);
    resizeFrame = window.requestAnimationFrame(applyViewportTransition);
  }

  function handleEscape(event) {
    if (event.key !== "Escape") return;
    if (currentResource) navigateBackFromResource();
    else if (!compactViewport()) return;
    else if (currentState === "full") setState("study");
    else if (currentState === "study") setState(selection?.hasPassageSelection ? "peek" : "closed");
  }

  function applyViewportTransition() {
    sheetController?.cancel?.();
    viewportController?.update?.();
    const isCompact = compactViewport();
    if (lastCompact === null) {
      lastCompact = isCompact;
      return;
    }
    if (isCompact === lastCompact) return;
    lastCompact = isCompact;
    if (!isCompact) {
      setState("study", {focus: false, history: false, source: "breakpoint"});
    } else if (currentResource) {
      setState("full", {focus: false, history: false, source: "breakpoint"});
    } else if (currentMode === "explore") {
      setState("study", {focus: false, history: false, source: "breakpoint"});
    } else {
      setState(selection?.hasPassageSelection ? "peek" : "closed", {
        focus: false,
        history: false,
        source: "breakpoint",
      });
    }
    historyController?.replace(historySnapshot());
  }

  function navigateBackFromResource() {
    historyController?.backFromResource(() => showOverview({history: false}));
  }

  async function applyHistoryState(snapshot) {
    currentMode = snapshot.mode;
    if (snapshot.resource) {
      await openResource(snapshot.resource, {
        history: false,
        mode: snapshot.mode,
        state: snapshot.state,
      });
      return;
    }
    showOverview({
      history: false,
      mode: snapshot.mode,
      state: snapshot.state,
      reload: false,
    });
  }

  function historySnapshot() {
    return {state: currentState, mode: currentMode, resource: currentResource};
  }

  function handleContextInvalidated(event) {
    const invalidated = contextController?.invalidate?.(event.detail?.key, {load: currentMode === "passage"});
    if (invalidated && currentMode === "passage" && currentResource) {
      void resourceRouter?.open?.(currentResource, {mode: currentMode});
    }
  }

  function renderResourceHeader(resourceId, resource = null) {
    const resolved = resource || window.BHFStudyRecommendations?.resources?.[resourceId] || {label: "Study Resource"};
    setText("[data-companion-reference]", resolved.label || "Study Resource");
    setText("[data-companion-selected-text]", currentMode === "explore"
      ? "Explore BHF collections"
      : selection?.reference || "Study Companion");
  }

  function renderSaveState(state = {}) {
    const button = panel?.querySelector('[data-companion-action="save"]');
    if (!button) return;
    const reference = state.selection?.reference || selection?.reference || "this passage";
    const hasPassageSelection = state.selection?.hasPassageSelection === true;
    const status = state.status || (state.saved
      ? "saved"
      : state.loading
        ? "loading"
        : state.unavailable
          ? "unavailable"
          : "not-saved");
    const saved = status === "saved";
    const loading = status === "loading";
    const saving = status === "saving" || state.saving === true;
    const unavailable = status === "unavailable";
    button.dataset.saved = saved ? "true" : status === "not-saved" ? "false" : "unknown";
    button.dataset.saveState = status;
    button.disabled = !hasPassageSelection || loading || saving || saved || unavailable;
    button.setAttribute("aria-disabled", String(button.disabled));
    button.setAttribute("aria-busy", String(loading || saving));
    button.setAttribute("aria-label", !hasPassageSelection
      ? "Save Passage unavailable; select a verse or passage"
      : saved
        ? `${reference} is saved`
        : loading
          ? `Checking whether ${reference} is saved`
          : saving
            ? `Saving ${reference}`
            : unavailable
              ? `Save Passage unavailable for ${reference}; saved status could not be confirmed`
              : `Save ${reference}`);
    button.textContent = saved
      ? "✓ Passage Saved"
      : saving
        ? "Saving…"
        : "☆ Save Passage";
  }

  function updateReaderAccessibility(state) {
    const reader = document.querySelector(".reader-column");
    if (!reader) return;
    const inaccessible = compactViewport() && state === "full";
    reader.inert = inaccessible;
    if (inaccessible) {
      reader.dataset.companionInert = "true";
      reader.setAttribute("aria-hidden", "true");
    } else if (reader.dataset.companionInert === "true") {
      delete reader.dataset.companionInert;
      reader.removeAttribute("aria-hidden");
    }
  }

  function stateIndex(state) {
    return ["closed", "peek", "study", "full"].indexOf(state);
  }

  function setText(selector, value) {
    const target = panel?.querySelector(selector) || document.querySelector(selector);
    if (target) target.textContent = String(value || "");
  }

  document.addEventListener("DOMContentLoaded", init);
})();
