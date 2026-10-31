/* Source-grounded, paged Locations for the Study Companion. */
(function (root, factory) {
  "use strict";

  const locations = factory();
  if (typeof module === "object" && module.exports) module.exports = locations;
  root.BHFCompanionLocations = locations;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const PAGE_SIZE = 25;
  const states = new WeakMap();

  function render(panel, payload, options = {}) {
    const section = panel?.querySelector("[data-companion-locations-section]");
    const list = panel?.querySelector("[data-companion-locations-list]");
    const status = panel?.querySelector("[data-companion-locations-status]");
    const more = panel?.querySelector("[data-companion-locations-more]");
    if (!section || !list || !status || !more) return null;

    const previous = states.get(panel);
    if (previous) {
      previous.active = false;
      previous.controller.abort();
    }

    const document = list.ownerDocument || rootDocument();
    const items = Array.isArray(payload?.items) ? payload.items.filter(isLocation) : [];
    if (!items.length) {
      section.hidden = options.showEmpty !== true;
      list.replaceChildren();
      status.textContent = "";
      status.setAttribute("role", "status");
      more.hidden = true;
      more.disabled = false;
      states.delete(panel);
      if (options.showEmpty === true) {
        const emptyItem = document.createElement("li");
        emptyItem.className = "companion-location-empty-item";
        const empty = textBlock(
          document,
          "companion-geography-empty",
          `No source-grounded locations for ${payload?.reference || options.selection?.reference || "this passage"}.`,
        );
        empty.dataset.geographyEmpty = "";
        emptyItem.append(empty);
        list.append(emptyItem);
      }
      return null;
    }

    const state = {
      panel,
      section,
      list,
      status,
      more,
      document,
      items: [],
      itemKeys: new Set(),
      total: Math.max(items.length, Number(payload?.total || items.length)),
      nextCursor: payload?.next_cursor == null ? null : String(payload.next_cursor),
      reference: String(payload?.reference || ""),
      selection: {...(options.selection || {})},
      offline: options.offline === true || rootNavigator()?.onLine === false,
      loadPage: options.loadPage,
      openMap: options.openMap,
      openCkl: options.openCkl,
      onChange: options.onChange,
      controller: new AbortController(),
      active: true,
      loading: false,
    };
    states.set(panel, state);
    section.hidden = false;
    list.replaceChildren();
    appendUniqueItems(state, items);
    more.hidden = !state.nextCursor || state.items.length >= state.total;
    more.disabled = state.offline || !state.nextCursor;
    more.type = "button";
    more.textContent = state.offline
      ? `View all ${state.total} locations when online`
      : `View all ${state.total} locations`;
    more.setAttribute("aria-controls", "companion-locations-list");
    status.textContent = state.offline && !more.hidden
      ? `Showing ${state.items.length} of ${state.total} locations. Connect to load the rest.`
      : "";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.setAttribute("tabindex", "-1");
    more.onclick = () => { void loadAll(state); };
    return state;
  }

  function cancel(panel) {
    const state = states.get(panel);
    if (!state) return false;
    state.active = false;
    state.controller.abort();
    states.delete(panel);
    return true;
  }

  function appendUniqueItems(state, items) {
    for (const item of items) {
      const key = itemKey(item);
      if (!key || state.itemKeys.has(key)) continue;
      state.itemKeys.add(key);
      state.items.push(item);
      state.list.append(locationEntry(item, state));
    }
  }

  function locationEntry(item, state) {
    const document = state.document;
    const listItem = document.createElement("li");
    listItem.className = "companion-location-item";
    const article = document.createElement("article");
    article.className = "companion-location-card";
    article.dataset.locationOrigin = item.origin;
    article.dataset.locationId = item.id;

    const heading = document.createElement("h4");
    heading.textContent = item.title;
    article.append(heading);

    article.append(textBlock(
      document,
      "companion-location-identity",
      `${item.origin === "maps" ? "Maps" : "CKL"} identity: ${item.id}`,
    ));

    const references = Array.isArray(item.references) && item.references.length
      ? item.references
      : item.reference ? [item.reference] : [];
    if (references.length) article.append(textBlock(document, "companion-location-reference", references.join(" · ")));

    const identityOnlyDraft = item.origin === "ckl"
      && (String(item.content_status || "").toLowerCase() === "draft"
        || String(item.review_status || "").toLowerCase() === "unreviewed");
    if (!identityOnlyDraft) {
      if (item.region) article.append(textBlock(document, "companion-location-region", `Region: ${item.region}`));
      if (item.modern_location) {
        const uncertain = ["possible", "uncertain", "unknown"].includes(String(item.map_confidence || "").toLowerCase());
        const label = uncertain ? "Possible modern location in the map catalog" : "Map catalog suggestion";
        article.append(textBlock(document, "companion-location-modern", `${label}: ${item.modern_location}`));
      }
      if (item.passage_role) article.append(textBlock(document, "companion-location-role", item.passage_role));
      if (item.description) {
        const label = item.origin === "ckl" ? "CKL summary" : "Map catalog description";
        article.append(textBlock(document, "companion-location-description", `${label}: ${item.description}`));
      }
      if (item.identification_uncertainty) {
        article.append(textBlock(document, "companion-location-uncertainty", item.identification_uncertainty));
      }
    }

    if (item.origin === "maps") {
      if (item.relationship === "directly_named") {
        article.append(textBlock(document, "companion-location-role", item.passage_role || "Named in the passage."));
      }
      if (item.map_confidence) {
        article.append(textBlock(document, "companion-location-confidence", `Map catalog confidence: ${item.map_confidence}.`));
      }
      if (item.license || item.provenance?.license) {
        article.append(textBlock(document, "companion-location-license", `License: ${item.license || item.provenance.license}`));
      }
    } else if (item.source_lock?.status === "locked") {
      article.append(textBlock(document, "companion-location-provenance", "Includes source-locked geography evidence."));
    } else if (item.source_lock?.status && item.source_lock.status !== "not_recorded") {
      article.append(textBlock(
        document,
        "companion-location-uncertainty",
        `Related geography evidence is ${item.source_lock.status}; it is not used for identification.`,
      ));
    }

    if (item.origin === "ckl") {
      if (item.review_status) {
        article.append(textBlock(document, "companion-location-review", `Review status: ${formatStatus(item.review_status)}`));
      }
      if (item.content_status) {
        article.append(textBlock(document, "companion-location-content-status", `Content status: ${formatStatus(item.content_status)}`));
      }
      if (item.source_lock?.id) {
        article.append(textBlock(document, "companion-location-source-lock-id", `Source-lock identity: ${item.source_lock.id}`));
      }
    }

    const source = item.provenance || {};
    const sourceName = String(source.name || "").trim();
    const sourceNames = Array.isArray(source.sources) ? source.sources.filter(Boolean) : [];
    if (sourceName || sourceNames.length) {
      const sourceLine = document.createElement("p");
      sourceLine.className = "companion-location-source";
      const label = sourceName || "CKL sources";
      sourceLine.textContent = sourceNames.length
        ? `${label}: ${sourceNames.join(", ")}`
        : `Source: ${label}`;
      article.append(sourceLine);
    }
    if (source.license && item.origin !== "maps") {
      article.append(textBlock(document, "companion-location-license", `License: ${source.license}`));
    }
    if (source.url && isHttpUrl(source.url)) {
      const sourceLink = document.createElement("a");
      sourceLink.className = "companion-location-source-link";
      sourceLink.href = source.url;
      sourceLink.textContent = "Source record";
      sourceLink.target = "_blank";
      sourceLink.rel = "noopener noreferrer";
      article.append(sourceLink);
    }

    const action = document.createElement("button");
    action.type = "button";
    action.className = "secondary companion-location-action";
    action.dataset.locationId = item.id;
    if (item.origin === "maps" && item.map_focus_id) {
      action.dataset.locationAction = "open-map";
      action.textContent = `Open ${item.title} in Maps`;
      action.setAttribute("aria-label", `Open ${item.title} in Maps`);
      action.addEventListener("click", async () => {
        try {
          const acknowledgment = await state.openMap?.(item.map_focus_id, action);
          if (acknowledgment?.status === "selected"
            && String(acknowledgment.selectedId || "") === String(item.map_focus_id)) {
            announce(state, `Maps focused on ${item.title}.`);
          } else if (acknowledgment?.status) {
            announce(state, `Maps did not confirm focus on ${item.title}: ${acknowledgment.reason || acknowledgment.status}.`);
          } else {
            announce(state, `Opened Maps for ${item.title}.`);
          }
        } catch (_error) {
          announce(state, `Maps could not open ${item.title}.`, true);
        }
      });
    } else if (item.origin === "ckl") {
      action.dataset.locationAction = "open-ckl";
      action.textContent = `Open ${item.title} in CKL`;
      action.setAttribute("aria-label", `Open ${item.title} in Canonical Knowledge Library`);
      action.addEventListener("click", async () => {
        try {
          await state.openCkl?.(item.id, action);
          announce(state, `Opened CKL details for ${item.title}.`);
        } catch (_error) {
          announce(state, `CKL details for ${item.title} could not be opened.`, true);
        }
      });
    }
    if (action.dataset.locationAction) article.append(action);
    listItem.append(article);
    return listItem;
  }

  function textBlock(document, className, text) {
    const paragraph = document.createElement("p");
    paragraph.className = className;
    paragraph.textContent = String(text || "");
    return paragraph;
  }

  async function loadAll(state) {
    if (!state.active || state.loading || !state.nextCursor) return;
    if (state.offline || rootNavigator()?.onLine === false) {
      state.more.disabled = true;
      announce(state, `Showing ${state.items.length} of ${state.total} locations. Connect to load the rest.`);
      return;
    }
    if (typeof state.loadPage !== "function") {
      announce(state, "Additional locations could not be loaded.", true);
      return;
    }

    state.loading = true;
    state.more.disabled = true;
    state.more.textContent = "Loading locations…";
    state.status.setAttribute("role", "status");
    announce(state, `Loading locations for ${state.reference || "this chapter"}.`);
    const requestedCursors = new Set();
    try {
      while (state.nextCursor) {
        if (!state.active || state.controller.signal.aborted) return;
        if (rootNavigator()?.onLine === false) throw new Error("Connection lost while loading locations.");
        const cursor = state.nextCursor;
        if (requestedCursors.has(cursor)) throw new Error("Location pagination returned a repeated page.");
        requestedCursors.add(cursor);
        const response = await state.loadPage({
          ...state.selection,
          cursor,
          limit: PAGE_SIZE,
          signal: state.controller.signal,
        });
        if (!state.active || state.controller.signal.aborted) return;
        if (!response || !Array.isArray(response.items)) throw new Error("Location page was incomplete.");
        const previousCount = state.items.length;
        appendUniqueItems(state, response.items.filter(isLocation));
        if (state.items.length === previousCount && response.next_cursor != null) {
          throw new Error("Location pagination did not add any new records.");
        }
        state.total = Math.max(state.items.length, Number(response.total || state.total));
        const nextCursor = response.next_cursor == null ? null : String(response.next_cursor);
        if (nextCursor && (nextCursor === cursor || requestedCursors.has(nextCursor))) {
          throw new Error("Location pagination returned a repeated page.");
        }
        state.nextCursor = nextCursor;
        state.onChange?.({
          reference: state.reference,
          items: [...state.items],
          total: state.total,
          page_size: PAGE_SIZE,
          next_cursor: state.nextCursor,
        });
        state.more.textContent = state.nextCursor ? `Loaded ${state.items.length} of ${state.total} locations…` : "All locations loaded";
        announce(state, `Loaded ${state.items.length} of ${state.total} locations.`);
      }
      if (state.items.length < state.total) {
        throw new Error(`Loaded ${state.items.length} of ${state.total} locations.`);
      }
      state.more.hidden = true;
      state.status.textContent = `Showing all ${state.items.length} locations for ${state.reference || "this chapter"}.`;
      state.status.setAttribute("role", "status");
      state.status.focus?.({preventScroll: true});
    } catch (error) {
      if (!state.active || state.controller.signal.aborted || error?.name === "AbortError") return;
      state.more.hidden = false;
      state.more.disabled = false;
      state.more.textContent = "Retry loading locations";
      announce(state, error?.message || "Additional locations could not be loaded.", true);
    } finally {
      if (state.active) state.loading = false;
    }
  }

  function announce(state, message, error = false) {
    state.status.textContent = message;
    state.status.setAttribute("role", error ? "alert" : "status");
  }

  function urlFor(selection = {}, cursor = null, limit = PAGE_SIZE) {
    const parameters = new URLSearchParams({
      book: String(selection.book || ""),
      chapter: String(selection.chapter || ""),
      limit: String(Math.max(1, Math.min(Number(limit) || PAGE_SIZE, PAGE_SIZE))),
    });
    const start = Number(selection.startVerse || selection.verse_start || 0);
    const end = Number(selection.endVerse || selection.verse_end || 0);
    if (start > 0) parameters.set("verse_start", String(start));
    if (end > 0) parameters.set("verse_end", String(end));
    if (cursor != null && String(cursor)) parameters.set("cursor", String(cursor));
    return `/api/study/companion-locations?${parameters.toString()}`;
  }

  function isLocation(item) {
    return Boolean(item && typeof item === "object" && item.id && item.title
      && (item.origin === "maps" || item.origin === "ckl"));
  }

  function itemKey(item) {
    return isLocation(item) ? `${item.origin}:${item.id}` : "";
  }

  function isHttpUrl(value) {
    try {
      return ["https:", "http:"].includes(new URL(String(value)).protocol);
    } catch (_error) {
      return false;
    }
  }

  function formatStatus(value) {
    return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function rootNavigator() {
    return typeof navigator !== "undefined" ? navigator : null;
  }

  function rootDocument() {
    return typeof document !== "undefined" ? document : null;
  }

  return Object.freeze({render, cancel, urlFor, pageSize: PAGE_SIZE});
});
