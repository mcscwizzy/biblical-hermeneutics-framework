/* Passage-scoped, source-grounded Narrative Explorer view and request lifecycle. */
(function (root, factory) {
  const explorer = factory(root);
  if (typeof module === "object" && module.exports) module.exports = explorer;
  root.BHFNarrativeExplorer = explorer;
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  "use strict";

  const PAGE_SIZE = 12;
  const pendingRequests = new Map();
  const SECTIONS = [
    {
      id: "biblical_narrative",
      title: "Biblical Narrative",
      description: "Literary observations and narrative records linked to this passage.",
    },
    {
      id: "archaeology_ancient_history",
      title: "Archaeology & Ancient History",
      description: "Artifacts, manuscripts, historical records, and ancient literary comparisons, kept distinct by evidence type.",
    },
    {
      id: "biblical_geography",
      title: "Biblical Geography",
      description: "Physical places, regions, and routes with the identification limits recorded by BHF.",
    },
    {
      id: "divine_council_cosmic_geography",
      title: "Divine Council & Cosmic Geography",
      description: "Textual records about heavenly assemblies, divine beings, sacred space, and cosmic imagery; this lens does not settle interpretation.",
    },
    {
      id: "themes_biblical_connections",
      title: "Themes & Biblical Connections",
      description: "Authored themes and passage links with their recorded relationship types and evidence basis.",
    },
    {
      id: "people_events_relationships",
      title: "People, Events & Relationships",
      description: "People, groups, events, and institutions connected through recorded source identities and relationships.",
    },
  ];
  const SOURCE_LABELS = {
    canonical_knowledge_library: "CKL",
    passage_maps: "Maps",
    archaeology_passage_resolver: "Archaeology service",
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

  function subscribe(entry, signal) {
    entry.subscribers += 1;
    return new Promise((resolve, reject) => {
      let complete = false;
      const finish = (aborted) => {
        if (complete) return false;
        complete = true;
        signal?.removeEventListener?.("abort", onAbort);
        entry.subscribers = Math.max(0, entry.subscribers - 1);
        if (aborted && entry.subscribers === 0 && !entry.settled) {
          if (pendingRequests.get(entry.url) === entry) pendingRequests.delete(entry.url);
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

    const header = element(document, "header", "narrative-explorer-header");
    appendTextElement(document, header, "h3", "Narrative evidence and connections");
    appendTextElement(
      document,
      header,
      "p",
      "Counts separate parent records, claims, and evidence entries. Multiple projections of one claim are not separate discoveries.",
    );
    rootElement.append(header);

    const passage = projection?.passage?.reference;
    if (passage) {
      appendTextElement(document, rootElement, "p", `Evidence linked to ${passage}`, "narrative-explorer-passage");
    }
    const sectionsHost = element(document, "div", "narrative-explorer-sections");
    const itemsById = new Map((Array.isArray(projection?.items) ? projection.items : []).map((item) => [item.id, item]));
    const connectionsByItem = groupConnections(projection?.connections);
    const sectionsById = new Map((Array.isArray(projection?.sections) ? projection.sections : []).map((section) => [section.id, section]));
    const coverageBySource = new Map((Array.isArray(projection?.coverage) ? projection.coverage : []).map((entry) => [entry.source_domain, entry]));

    SECTIONS.forEach((definition) => {
      const section = sectionsById.get(definition.id) || {id: definition.id, state: "unknown", item_ids: [], source_domains: []};
      const items = (Array.isArray(section.item_ids) ? section.item_ids : [])
        .map((id) => itemsById.get(id))
        .filter(Boolean);
      sectionsHost.append(renderSection(document, definition, section, items, coverageBySource, connectionsByItem, options));
    });
    rootElement.append(sectionsHost);
    return rootElement;
  }

  function renderSection(document, definition, section, items, coverageBySource, connectionsByItem, options) {
    const card = element(document, "section", "narrative-explorer-section");
    card.dataset.sectionId = definition.id;
    const heading = element(document, "div", "narrative-explorer-section-heading");
    appendTextElement(document, heading, "h4", definition.title);
    appendTextElement(document, heading, "p", definition.description);
    card.append(heading);

    const state = normalizeState(section.state);
    const stateLabel = {
      available: "Available",
      partial: "Partial coverage",
      not_represented: "No linked records are represented here yet",
      unknown: "Availability could not be checked",
    }[state];
    appendTextElement(document, card, "p", stateLabel, `narrative-explorer-availability is-${state}`);
    const recordCounts = countRecords(items);
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
      appendTextElement(document, card, "p", "An empty lookup describes the records linked in BHF; it does not disprove a biblical account.", "narrative-explorer-caution");
    }

    const previewList = element(document, "div", "narrative-explorer-previews");
    const fullList = element(document, "div", "narrative-explorer-record-list");
    fullList.hidden = true;
    const ordered = orderForPreview(items);
    ordered.slice(0, 2).forEach((item) => previewList.append(renderItem(document, item, connectionsByItem.get(item.id) || [], options)));
    card.append(previewList, fullList);

    const inspect = element(document, "button", "secondary narrative-explorer-inspect");
    inspect.type = "button";
    inspect.textContent = items.length ? `Inspect ${items.length} eligible records` : "No records to inspect";
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
        inspect.textContent = expanded ? "Hide records" : `Inspect ${items.length} eligible records`;
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

  function countRecords(items) {
    const counts = {objects: 0, claims: 0, evidence: 0, notes: 0, maps: 0, archaeology: 0};
    items.forEach((item) => {
      if (item.domain === "ckl" && item.record_kind === "object") counts.objects += 1;
      else if (item.domain === "ckl" && item.record_kind === "claim") counts.claims += 1;
      else if (item.domain === "ckl" && item.record_kind === "evidence") counts.evidence += 1;
      else if (item.domain === "ckl" && item.record_kind === "interpretive_note") counts.notes += 1;
      else if (item.domain === "maps") counts.maps += 1;
      else if (item.domain === "archaeology") counts.archaeology += 1;
    });
    return [
      `${counts.objects} CKL parent ${counts.objects === 1 ? "record" : "records"}`,
      `${counts.claims} ${counts.claims === 1 ? "claim" : "claims"}`,
      `${counts.evidence} evidence ${counts.evidence === 1 ? "record" : "records"}`,
      `${counts.notes} interpretive ${counts.notes === 1 ? "note" : "notes"}`,
      `${counts.maps} map ${counts.maps === 1 ? "record" : "records"}`,
      `${counts.archaeology} archaeology-service ${counts.archaeology === 1 ? "record" : "records"}`,
    ].join(" · ");
  }

  function coverageLine(sourceDomain, entry) {
    const label = SOURCE_LABELS[sourceDomain] || sourceDomain;
    if (!entry) return `${label}: availability could not be checked.`;
    if (entry.state === "available") {
      const count = Number(entry.query_returned_count);
      return `${label}: lookup completed${Number.isFinite(count) ? `; ${count} source records returned` : ""}.`;
    }
    if (entry.state === "partial") {
      const missing = Array.isArray(entry.missing_subdomains) && entry.missing_subdomains.length
        ? ` Missing areas: ${entry.missing_subdomains.join(", ")}.`
        : " Some source records could not be checked.";
      return `${label}: partial coverage.${missing}`;
    }
    if (entry.state === "not_represented" && entry.query_status === "complete") {
      const emptyLabel = sourceDomain === "archaeology_passage_resolver"
        ? "linked archaeology-service records"
        : "eligible linked records";
      return `${label}: lookup completed; no ${emptyLabel} returned for this passage.`;
    }
    return `${label}: availability is unknown because the lookup did not complete.`;
  }

  function renderItem(document, item, connections, options) {
    const card = element(document, "article", "narrative-explorer-item");
    const title = readerText(item.title) || readerText(item.claim_text) || readerText(item.description) || readerText(item.id) || "Source record";
    appendTextElement(document, card, "h5", title);
    const authoredText = readerText(item.claim_text) && readerText(item.claim_text) !== title
      ? readerText(item.claim_text)
      : readerText(item.description) && readerText(item.description) !== title
        ? readerText(item.description)
        : "";
    if (authoredText) appendTextElement(document, card, "p", authoredText, "narrative-explorer-item-copy");
    const visibleKind = [item.evidence_category, item.claim_type, item.assertion_type, item.domain]
      .map(readerText)
      .filter(Boolean)
      .join(" · ");
    if (visibleKind) appendTextElement(document, card, "p", visibleKind, "narrative-explorer-item-kind");

    const provenance = element(document, "details", "narrative-explorer-provenance");
    appendTextElement(document, provenance, "summary", "Evidence and source details");
    const metadata = provenanceLines(item, connections);
    if (metadata.length) {
      const list = element(document, "ul");
      metadata.forEach((line) => {
        const entry = element(document, "li");
        entry.textContent = line;
        list.append(entry);
      });
      provenance.append(list);
    }
    card.append(provenance);

    const action = supportedAction(item);
    if (action && typeof options.onNavigate === "function") {
      const button = element(document, "button", "secondary narrative-explorer-item-action");
      button.type = "button";
      button.textContent = action.label;
      if (action.ariaLabel) button.setAttribute("aria-label", action.ariaLabel.replace("{title}", title));
      button.addEventListener("click", () => options.onNavigate(item, action, button));
      card.append(button);
    }
    return card;
  }

  function provenanceLines(item, connections) {
    const lines = [`Projected source identity: ${readerText(item.id) || "unavailable"}`];
    const subject = readerText(item.parent_object_id || item.object_id);
    if (subject) lines.push(`CKL subject: ${subject}`);
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
    anchors.slice(0, 8).forEach((anchor) => {
      const reference = readerText(anchor.reference);
      if (reference) lines.push(`Passage relationship: ${reference}${anchor.relationship ? ` · ${readerText(anchor.relationship)}` : ""}`);
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
      ["Place identification confidence", item.place_identification_confidence],
    ].forEach(([label, value]) => {
      const text = metadataText(value);
      if (text) lines.push(`${label}: ${text}`);
    });
    if (item.coordinates_displayable === false && item.geography_kind && PHYSICAL_GEOGRAPHY.has(item.geography_kind)) {
      if (readerText(item.coordinate_display_reason)) lines.push(`Map point withheld: ${readerText(item.coordinate_display_reason)}`);
      else lines.push("Map point withheld because the source does not establish a precise physical identification.");
    }
    if (item.rationale && Object.keys(item.rationale).length) {
      lines.push(`Recorded basis: ${compactObject(item.rationale)}`);
    }
    connections.slice(0, 4).forEach((edge) => {
      const relation = readerText(edge.connection_type || edge.original_relationship_type);
      if (relation) lines.push(`Connection: ${relation}${edge.original_relationship_type ? ` · original relationship ${readerText(edge.original_relationship_type)}` : ""}`);
      if (readerText(edge.relationship_mode)) lines.push(`Connection mode: ${readerText(edge.relationship_mode)}`);
      if (readerText(edge.direction)) lines.push(`Connection direction: ${readerText(edge.direction)}`);
      if (readerText(edge.temporal_layer)) lines.push(`Connection temporal layer: ${readerText(edge.temporal_layer)}`);
      if (edge.basis && Object.keys(edge.basis).length) lines.push(`Connection basis: ${compactObject(edge.basis)}`);
    });
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

  function renderFailure(state, selection, options = {}) {
    const document = options.document || root.document;
    if (!document) throw new Error("A document is required to render Narrative Explorer status.");
    const container = element(document, "section", "narrative-explorer-state");
    container.setAttribute("role", "alert");
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
    value.textContent = String(text ?? "");
    parent.append(value);
    return value;
  }

  function readerText(value) {
    return typeof value === "string" || typeof value === "number" ? String(value).trim() : "";
  }

  function metadataText(value) {
    if (value === null || value === undefined || value === "") return "";
    if (typeof value === "boolean") return value ? "Yes" : "No";
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
    urlFor,
    load,
    createSession,
    renderOverview,
    renderFailure,
    classifyError,
  });
});
