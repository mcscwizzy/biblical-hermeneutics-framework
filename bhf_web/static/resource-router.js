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

    host.addEventListener("click", handleClick);
    host.addEventListener("keydown", handleKeydown);

    async function open(resourceId, routeOptions = {}) {
      if (!NATIVE_RESOURCES.has(resourceId)) return false;
      sequence += 1;
      const requestSequence = sequence;
      controller?.abort();
      controller = new AbortController();
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
      shell.classList.remove("is-native-resource");
    }

    function showLegacy(resourceId) {
      host.hidden = true;
      shell.classList.remove("is-native-resource");
      options.openLegacy?.(resourceId);
    }

    async function renderPassage(resourceId, requestSequence, signal) {
      const selection = options.getSelection?.() || {};
      const context = options.getContext?.() || {};
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
      host.replaceChildren(body);
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
      host.replaceChildren(body);
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
      host.replaceChildren(body);
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
      host.replaceChildren(body);
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
          card.dataset.canonicalQuery = item.id || item.title;
          card.tabIndex = 0;
          card.setAttribute("role", "button");
        }
        body.append(card);
      });
      body.append(actionButton("Open Canonical Knowledge →", "canonical"));
      host.replaceChildren(body);
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
      host.replaceChildren(body);
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
      if (canonical) {
        showLegacy("canonical");
        window.BHFStudyActions?.openCanonicalQuery?.(canonical.dataset.canonicalQuery);
      }
    }

    function handleKeydown(event) {
      if (event.key !== "Enter" && event.key !== " ") return;
      const canonical = event.target.closest("[data-canonical-query]");
      if (!canonical) return;
      event.preventDefault();
      canonical.click();
    }

    return Object.freeze({open, close, showLegacy});
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

  function renderLoading(host) {
    const status = document.createElement("p");
    status.className = "companion-detail-status";
    status.setAttribute("role", "status");
    status.textContent = "Loading resource…";
    host.replaceChildren(status);
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
  }

  function titleCase(value) {
    return String(value || "Resource")
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  window.BHFResourceRouter = Object.freeze({create});
})();
