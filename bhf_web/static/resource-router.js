/* Native companion summaries and resource-first collection browsers. */
(function () {
  "use strict";

  const NATIVE_RESOURCES = new Set([
    "commentary", "canonical", "maps", "archaeology", "people", "places",
    "themes", "timeline", "cross_references",
  ]);
  const CANONICAL_TYPES = {
    people: "person",
    places: "place",
    themes: "theme",
    timeline: "event",
  };

  function create(options) {
    const panel = options?.panel;
    const shell = options?.shell;
    const host = panel?.querySelector("[data-companion-resource-host]");
    if (!panel || !shell || !host) return null;
    let sequence = 0;
    let controller = null;
    let nativeBackView = null;

    host.addEventListener("click", handleClick);
    host.addEventListener("keydown", handleKeydown);

    async function open(resourceId, routeOptions = {}) {
      if (!NATIVE_RESOURCES.has(resourceId)) return false;
      sequence += 1;
      const requestSequence = sequence;
      controller?.abort();
      controller = new AbortController();
      nativeBackView = null;
      shell.classList.add("is-native-resource");
      host.hidden = false;
      renderLoading(host);
      try {
        if (routeOptions.mode === "explore") {
          await renderExplore(resourceId, requestSequence, controller.signal);
        } else {
          await renderPassage(resourceId, requestSequence, controller.signal);
        }
      } catch (error) {
        if (error?.name !== "AbortError" && requestSequence === sequence) {
          renderError(host, error?.message || "This resource could not be loaded.");
        }
      }
      return true;
    }

    function close() {
      sequence += 1;
      controller?.abort();
      controller = null;
      host.hidden = true;
      host.replaceChildren();
      host.removeAttribute("aria-busy");
      shell.classList.remove("is-native-resource");
      nativeBackView = null;
    }

    function showLegacy(resourceId) {
      host.hidden = true;
      shell.classList.remove("is-native-resource");
      options.openLegacy?.(resourceId);
    }

    async function renderPassage(resourceId, requestSequence, signal) {
      const selection = options.getSelection?.() || {};
      const selectionKey = window.BHFCompanionContext?.requestKey?.(selection) || "";
      const contextRecord = options.getContextRecord?.() || {
        key: selectionKey,
        status: "ready",
        context: options.getContext?.() || null,
      };
      if (resourceId === "commentary") {
        const parameters = new URLSearchParams();
        if (selection.startVerse) parameters.set("start_verse", String(selection.startVerse));
        if (selection.endVerse) parameters.set("end_verse", String(selection.endVerse));
        const suffix = parameters.toString() ? `?${parameters}` : "";
        const data = await requestJson(
          `/api/commentary/${encodeURIComponent(selection.book)}/${selection.chapter}${suffix}`,
          signal,
        );
        if (requestSequence !== sequence) return;
        renderCommentary(data);
        return;
      }
      if (contextRecord.status === "error" && contextRecord.key === selectionKey) {
        renderError(host, contextRecord.error || "Passage resources could not be loaded.");
        return;
      }
      if (!contextRecord.context || contextRecord.status !== "ready" || contextRecord.key !== selectionKey) {
        renderLoading(host, `Loading ${selection.reference || "passage"} resources…`);
        return;
      }
      const context = contextRecord.context;
      if (resourceId === "maps") {
        renderMaps(context.summaries?.maps || {places: [], routes: []});
      } else if (resourceId === "archaeology") {
        renderArchaeology(context.summaries?.archaeology || [], true);
      } else if (["people", "places", "themes"].includes(resourceId)) {
        renderCanonicalCards(context.entities?.[resourceId] || [], resourceId, true);
      } else if (resourceId === "canonical") {
        renderCanonicalCards(context.summaries?.canonical || [], "canonical knowledge", true);
      } else if (resourceId === "timeline") {
        renderCanonicalCards(context.summaries?.timeline || [], "timeline", true);
      } else if (resourceId === "cross_references") {
        renderCrossReferences(context.summaries?.cross_references || []);
      }
    }

    async function renderExplore(resourceId, requestSequence, signal) {
      if (resourceId === "maps") {
        const data = await requestJson("/api/maps/catalog", signal);
        if (requestSequence !== sequence) return;
        renderMaps({places: data.places || [], routes: data.routes || []}, {collection: true});
        return;
      }
      if (resourceId === "archaeology") {
        const data = await requestJson("/api/archaeology?limit=12&include_media=false", signal);
        if (requestSequence !== sequence) return;
        renderArchaeology(data.results || [], false);
        return;
      }
      if (resourceId === "commentary") {
        const data = await requestJson("/api/commentary/diagnostics", signal);
        if (requestSequence !== sequence) return;
        renderCommentaryCollection(data);
        return;
      }
      const type = CANONICAL_TYPES[resourceId];
      const parameters = new URLSearchParams({limit: "12", include_placeholders: "false"});
      if (type) parameters.set("type", type);
      const data = await requestJson(`/api/canonical/search?${parameters}`, signal);
      if (requestSequence !== sequence) return;
      renderCanonicalCards(data.results || [], resourceId === "canonical" ? "canonical knowledge" : resourceId, false);
    }

    function renderCommentary(data) {
      const entries = Array.isArray(data.entries) ? data.entries : [];
      const body = resourceBody("Tyndale Study Notes", entries.length
        ? `${entries.length} passage note${entries.length === 1 ? "" : "s"}`
        : "No notes cover this passage.");
      entries.forEach((entry) => {
        const card = summaryCard(entry.title || "Study note", entry.body || "");
        card.classList.add("companion-commentary-entry");
        body.append(card);
      });
      body.append(actionButton("Open full commentary →", "commentary"));
      commit(body);
    }

    function renderCommentaryCollection(data) {
      const available = Boolean(data.available);
      const body = resourceBody(
        "Tyndale Study Notes",
        available
          ? "The local commentary collection is installed. Select a chapter in the Bible to read its notes."
          : "The commentary collection is not installed on this device.",
      );
      (data.sources || []).forEach((source) => body.append(summaryCard(source.name || source.id, source.attribution || source.copyright || "")));
      commit(body);
    }

    function renderMaps(data, options = {}) {
      const places = Array.isArray(data.places) ? data.places : [];
      const routes = Array.isArray(data.routes) ? data.routes : [];
      const body = resourceBody(
        options.collection ? "Map Collections" : "Maps for this passage",
        `${places.length} place${places.length === 1 ? "" : "s"} and ${routes.length} route${routes.length === 1 ? "" : "s"}`,
      );
      appendGroup(body, "Places", places.slice(0, 8));
      appendGroup(body, "Journeys & routes", routes.slice(0, 8));
      body.append(actionButton("Open Full Map →", "maps"));
      commit(body);
    }

    function renderArchaeology(items, contextual) {
      const body = resourceBody(
        contextual ? "Archaeology for this passage" : "Archaeology Collection",
        `${items.length} record${items.length === 1 ? "" : "s"}${contextual ? " related to this passage" : " available to browse"}`,
      );
      items.slice(0, 12).forEach((item) => {
        const subtitle = [item.item_type, item.period, item.confidence].filter(Boolean).join(" · ");
        body.append(summaryCard(item.title || item.name || item.id, item.summary || item.why_it_matters || subtitle, subtitle));
      });
      const link = document.createElement("a");
      link.className = "companion-detail-action";
      link.href = "/archaeology";
      link.textContent = "Open Archaeology Library →";
      body.append(link);
      commit(body);
    }

    function renderCanonicalCards(items, label, contextual) {
      const body = resourceBody(
        titleCase(label),
        items.length
          ? `${items.length} ${contextual ? "passage-related" : "browsable"} result${items.length === 1 ? "" : "s"}`
          : `No ${label} records are available${contextual ? " for this passage" : ""}.`,
      );
      items.slice(0, 12).forEach((item) => {
        const card = summaryCard(item.title || item.name || item.id, item.summary || "", item.type || item.relationship || "");
        if (item.id || item.title) {
          card.dataset.canonicalId = item.id || item.title;
          card.tabIndex = 0;
          card.setAttribute("role", "button");
          card.setAttribute("aria-label", `View ${item.title || item.name || item.id} details`);
        }
        body.append(card);
      });
      body.append(actionButton("Open Canonical Knowledge →", "canonical"));
      commit(body);
    }

    function renderCrossReferences(items) {
      const body = resourceBody("Cross References", `${items.length} related Scripture reference${items.length === 1 ? "" : "s"}`);
      const list = document.createElement("ul");
      list.className = "companion-reference-list";
      items.forEach((item) => {
        const entry = document.createElement("li");
        entry.textContent = String(item);
        list.append(entry);
      });
      body.append(list);
      commit(body);
    }

    function appendGroup(body, label, items) {
      if (!items.length) return;
      const heading = document.createElement("h3");
      heading.textContent = label;
      body.append(heading);
      items.forEach((item) => body.append(summaryCard(
        item.title || item.name || item.id,
        item.summary || item.description || "",
        item.confidence || item.period || "",
      )));
    }

    function resourceBody(title, description) {
      const body = document.createElement("div");
      body.className = "companion-detail-body";
      const heading = document.createElement("h3");
      heading.textContent = title;
      const intro = document.createElement("p");
      intro.className = "companion-detail-intro";
      intro.textContent = description;
      body.append(heading, intro);
      return body;
    }

    function summaryCard(title, summary, meta = "") {
      const card = document.createElement("article");
      card.className = "companion-summary-card";
      const heading = document.createElement("h4");
      heading.textContent = title || "Resource";
      card.append(heading);
      if (meta) {
        const metadata = document.createElement("p");
        metadata.className = "companion-summary-meta";
        metadata.textContent = meta;
        card.append(metadata);
      }
      if (summary) {
        const text = document.createElement("p");
        text.textContent = summary;
        card.append(text);
      }
      return card;
    }

    function actionButton(label, resourceId) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "companion-detail-action";
      button.dataset.openLegacyResource = resourceId;
      button.textContent = label;
      return button;
    }

    function handleClick(event) {
      const legacy = event.target.closest("[data-open-legacy-resource]");
      if (legacy) {
        showLegacy(legacy.dataset.openLegacyResource);
        return;
      }
      const canonical = event.target.closest("[data-canonical-query]");
      const canonicalCard = event.target.closest("[data-canonical-id]");
      if (canonicalCard) {
        void openCanonicalDetail(canonicalCard.dataset.canonicalId);
        return;
      }
      const nativeBack = event.target.closest("[data-native-resource-back]");
      if (nativeBack) {
        restoreNativeBackView();
        return;
      }
      if (canonical) {
        showLegacy("canonical");
        window.BHFStudyActions?.openCanonicalQuery?.(canonical.dataset.canonicalQuery);
      }
    }

    function handleKeydown(event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      const canonical = event.target.closest("[data-canonical-id], [data-canonical-query]");
      if (!canonical) return;
      event.preventDefault();
      canonical.click();
    }

    async function openCanonicalDetail(objectId) {
      const normalized = String(objectId || "").trim();
      if (!normalized) return;
      if (!nativeBackView) {
        const fragment = document.createDocumentFragment();
        while (host.firstChild) fragment.append(host.firstChild);
        nativeBackView = fragment;
      }
      sequence += 1;
      const requestSequence = sequence;
      controller?.abort();
      controller = new AbortController();
      renderLoading(host, "Loading entity details…");
      try {
        const detail = await requestJson(`/api/canonical/objects/${encodeURIComponent(normalized)}`, controller.signal);
        if (requestSequence !== sequence) return;
        renderCanonicalDetail(detail);
      } catch (error) {
        if (error?.name !== "AbortError" && requestSequence === sequence) {
          renderError(host, error?.message || "This entity could not be loaded.");
        }
      }
    }

    function renderCanonicalDetail(detail) {
      const body = resourceBody(detail.title || detail.name || detail.id, detail.summary || "Canonical knowledge detail");
      const sections = [
        ["Historical context", detail.historical_context],
        ["Canonical context", detail.canonical_context || detail.canonical_role],
        ["Literary context", detail.literary_context],
        ["Covenantal significance", detail.covenantal_significance],
      ];
      sections.filter(([, value]) => value).slice(0, 3).forEach(([label, value]) => {
        const section = document.createElement("section");
        const heading = document.createElement("h4");
        heading.textContent = label;
        const text = document.createElement("p");
        text.textContent = value;
        section.append(heading, text);
        body.append(section);
      });
      const references = (detail.scripture_references || []).slice(0, 6)
        .map((item) => typeof item === "string" ? item : item.reference)
        .filter(Boolean);
      if (references.length) appendGroup(body, "Scripture", references.map((reference) => ({title: reference})));
      const back = actionButton("← Back to results", "");
      delete back.dataset.openLegacyResource;
      back.dataset.nativeResourceBack = "";
      body.append(back, actionButton("Open Canonical Knowledge →", "canonical"));
      commit(body);
    }

    function restoreNativeBackView() {
      if (!nativeBackView) return;
      sequence += 1;
      controller?.abort();
      host.replaceChildren(nativeBackView);
      host.setAttribute("aria-busy", "false");
      nativeBackView = null;
      host.querySelector("[data-canonical-id]")?.focus({preventScroll: true});
    }

    function commit(content) {
      host.replaceChildren(content);
      host.setAttribute("aria-busy", "false");
    }

    return Object.freeze({open, close, showLegacy, openCanonicalDetail});
  }

  async function requestJson(url, signal) {
    if (window.BHFApi?.requestJson) {
      return window.BHFApi.requestJson(url, {signal, headers: {Accept: "application/json"}}, "Resource could not be loaded.");
    }
    const response = await fetch(url, {signal, headers: {Accept: "application/json"}});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  function renderLoading(host, message = "Loading resource…") {
    const status = document.createElement("p");
    status.className = "companion-detail-status";
    status.setAttribute("role", "status");
    status.textContent = message;
    host.replaceChildren(status);
    host.setAttribute("aria-busy", "true");
  }

  function renderError(host, message) {
    const status = document.createElement("div");
    status.className = "companion-detail-error";
    status.setAttribute("role", "alert");
    const title = document.createElement("h3");
    title.textContent = "Resource unavailable";
    const text = document.createElement("p");
    text.textContent = message;
    status.append(title, text);
    host.replaceChildren(status);
    host.setAttribute("aria-busy", "false");
  }

  function titleCase(value) {
    return String(value || "Resource")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  window.BHFResourceRouter = Object.freeze({create});
})();
