/* Native companion summaries and resource-first collection browsers. */
(function () {
  "use strict";

  const NATIVE_RESOURCES = new Set([
    "commentary", "canonical", "archaeology", "people", "places",
    "themes", "timeline", "cross_references", "historical_context",
    "cultural_context", "original_audience", "literary_context", "covenant_context",
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
    let nativeBackFocusSelector = "";

    host.addEventListener("click", handleClick);
    host.addEventListener("keydown", handleKeydown);

    async function open(resourceId, routeOptions = {}) {
      if (!NATIVE_RESOURCES.has(resourceId)) return false;
      sequence += 1;
      const requestSequence = sequence;
      controller?.abort();
      controller = new AbortController();
      nativeBackView = null;
      nativeBackFocusSelector = "";
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
      nativeBackFocusSelector = "";
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
      if (["historical_context", "cultural_context", "original_audience", "literary_context", "covenant_context", "archaeology"].includes(resourceId)) {
        const narration = context.summaries?.narration?.by_context?.[resourceId];
        if (resourceId === "archaeology" && !narration) {
          renderArchaeology(context.summaries?.archaeology || [], true);
        } else {
          renderNarration(narration, resourceId, context.summaries?.archaeology || []);
        }
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

    function renderArchaeology(items, contextual) {
      const body = resourceBody(
        contextual ? "Archaeology for this passage" : "Archaeology Collection",
        `${items.length} record${items.length === 1 ? "" : "s"}${contextual ? " related to this passage" : " available to browse"}`,
      );
      items.slice(0, 12).forEach((item) => {
        const subtitle = [item.item_type, item.period, item.confidence].filter(Boolean).join(" · ");
        body.append(archaeologySummaryCard(item, item.summary || item.why_it_matters || subtitle, subtitle));
      });
      const link = document.createElement("a");
      link.className = "companion-detail-action";
      link.href = "/archaeology";
      link.textContent = "Open Archaeology Library →";
      body.append(link);
      commit(body);
    }

    function renderNarration(narration, resourceId, supplemental = []) {
      const labels = {
        historical_context: "Historical Context",
        cultural_context: "Cultural Context",
        original_audience: "Original Audience",
        literary_context: "Literary Context",
        covenant_context: "Covenant Context",
        archaeology: "Archaeological Context",
      };
      const body = resourceBody(
        labels[resourceId] || narration?.title || "Context",
        narration?.source_count
          ? `Evidence · ${narration.source_count} source${narration.source_count === 1 ? "" : "s"}`
          : "Deterministic context from the selected CKL evidence",
      );
      if (!narration || !narration.has_content) {
        body.append(summaryCard("No narrated evidence", "The selected CKL records do not support a compact narration for this context."));
        commit(body);
        return;
      }
      if (narration.lead?.text) {
        const lead = summaryCard("In brief", narration.lead.text);
        lead.classList.add("companion-narration-lead");
        appendEvidenceDisclosure(lead, narration.lead);
        body.append(lead);
      }
      (narration.sections || []).forEach((section) => {
        const container = document.createElement("section");
        const heading = document.createElement("h4");
        heading.textContent = section.heading || "Context";
        container.append(heading);
        const sentences = (section.sentences || []).filter((sentence) => sentence?.text);
        if (section.type === "caution") {
          sentences.forEach((sentence) => {
            const paragraph = document.createElement("p");
            paragraph.textContent = sentence.text;
            container.append(paragraph);
          });
        } else if (sentences.length) {
          const paragraph = document.createElement("p");
          paragraph.textContent = sentences.map((sentence) => sentence.text).join(" ");
          container.append(paragraph);
        }
        appendSectionEvidenceDisclosure(container, sentences);
        body.append(container);
      });
      if (resourceId === "archaeology" && supplemental.length) {
        const related = document.createElement("section");
        const heading = document.createElement("h4");
        heading.textContent = "Related archaeology records";
        related.append(heading);
        supplemental.slice(0, 2).forEach((item) => {
          related.append(archaeologySummaryCard(item, item.summary || item.why_it_matters || ""));
        });
        body.append(related);
      }
      if (Number(narration.additional_evidence_count || 0) > 0) {
        const additional = document.createElement("p");
        additional.className = "companion-summary-meta";
        additional.textContent = `${narration.additional_evidence_count} additional related record${narration.additional_evidence_count === 1 ? "" : "s"} available.`;
        body.append(additional);
      }
      commit(body);
    }

    function appendEvidenceDisclosure(host, sentence) {
      const lines = evidenceLines(sentence);
      const claimIds = Array.isArray(sentence?.claim_ids) ? sentence.claim_ids : [];
      const sourceIds = Array.isArray(sentence?.source_ids) ? sentence.source_ids : [];
      const references = Array.isArray(sentence?.scripture_references) ? sentence.scripture_references : [];
      if (!claimIds.length && !sourceIds.length && !references.length && !lines.length) return;
      const details = document.createElement("details");
      details.className = "companion-evidence-disclosure";
      const summary = document.createElement("summary");
      summary.textContent = `Evidence · ${sourceIds.length || 0} source${sourceIds.length === 1 ? "" : "s"}`;
      details.append(summary);
      const list = document.createElement("ul");
      lines.forEach((value) => {
        const item = document.createElement("li");
        item.textContent = value;
        list.append(item);
      });
      details.append(list);
      host.append(details);
    }

    function appendSectionEvidenceDisclosure(host, sentences) {
      if (!sentences.length || !sentences.some((sentence) => evidenceLines(sentence).length)) return;
      const sourceIds = new Set(sentences.flatMap((sentence) => sentence.source_ids || []));
      const details = document.createElement("details");
      details.className = "companion-evidence-disclosure companion-section-evidence";
      const summary = document.createElement("summary");
      summary.textContent = `Evidence · ${sourceIds.size} source${sourceIds.size === 1 ? "" : "s"}`;
      details.append(summary);
      const sentenceList = document.createElement("ol");
      sentences.forEach((sentence, index) => {
        const entry = document.createElement("li");
        const label = document.createElement("strong");
        label.textContent = `Sentence ${index + 1}`;
        entry.append(label);
        const lines = document.createElement("ul");
        evidenceLines(sentence).forEach((value) => {
          const item = document.createElement("li");
          item.textContent = value;
          lines.append(item);
        });
        entry.append(lines);
        sentenceList.append(entry);
      });
      details.append(sentenceList);
      host.append(details);
    }

    function evidenceLines(sentence) {
      const claimIds = Array.isArray(sentence?.claim_ids) ? sentence.claim_ids : [];
      const sourceIds = Array.isArray(sentence?.source_ids) ? sentence.source_ids : [];
      const sourceDetails = Array.isArray(sentence?.source_details) ? sentence.source_details : [];
      const references = Array.isArray(sentence?.scripture_references) ? sentence.scripture_references : [];
      const parentRecords = Array.isArray(sentence?.parent_records) && sentence.parent_records.length
        ? sentence.parent_records
        : sentence?.parent_object_id ? [{id: sentence.parent_object_id, title: sentence.parent_title}] : [];
      const metadata = [
        sentence?.certainty ? `Certainty: ${humanizeMetadata(sentence.certainty)}` : "",
        sentence?.dispute_status ? `Dispute: ${humanizeMetadata(sentence.dispute_status)}` : "",
        sentence?.content_status ? `Status: ${humanizeMetadata(sentence.content_status)}` : "",
        sentence?.review_status ? `Review: ${humanizeMetadata(sentence.review_status)}` : "",
        sentence?.human_review_required ? "Human review required" : "",
        ...parentRecords.map((record) => `CKL record: ${record.title || record.id || "record"}${record.id && record.title ? ` · ${record.id}` : ""}`),
      ].filter(Boolean);
      const sourceLines = sourceDetails.length
        ? sourceDetails.map((source) => `Source: ${source.title || source.id || "record"}${source.locator ? ` · ${source.locator}` : ""}`)
        : sourceIds.map((value) => `Source: ${value}`);
      return [...metadata, ...claimIds.map((value) => `Claim: ${value}`), ...sourceLines, ...references.map((value) => `Scripture: ${value}`)];
    }

    function humanizeMetadata(value) {
      return String(value || "").replaceAll("_", " ").replaceAll("-", " ");
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

    function archaeologySummaryCard(item, summary, meta = "") {
      const card = summaryCard(item.title || item.name || item.id, summary, meta);
      if (item.id) {
        card.dataset.archaeologyId = item.id;
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute("aria-label", `View evidence details for ${item.title || item.name || item.id}`);
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
      const archaeologyCard = event.target.closest("[data-archaeology-id]");
      if (archaeologyCard) {
        void openArchaeologyDetail(archaeologyCard.dataset.archaeologyId);
        return;
      }
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
      const interactiveCard = event.target.closest("[data-archaeology-id], [data-canonical-id], [data-canonical-query]");
      if (!interactiveCard) return;
      event.preventDefault();
      interactiveCard.click();
    }

    async function openCanonicalDetail(objectId) {
      const normalized = String(objectId || "").trim();
      if (!normalized) return;
      saveNativeBackView("[data-canonical-id]");
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

    async function openArchaeologyDetail(itemId) {
      const normalized = String(itemId || "").trim();
      if (!normalized) return;
      saveNativeBackView("[data-archaeology-id]");
      sequence += 1;
      const requestSequence = sequence;
      controller?.abort();
      controller = new AbortController();
      renderLoading(host, "Loading archaeological evidence…");
      try {
        const detail = await requestJson(`/api/archaeology/items/${encodeURIComponent(normalized)}`, controller.signal);
        if (requestSequence !== sequence) return;
        renderArchaeologyDetail(detail);
      } catch (error) {
        if (error?.name !== "AbortError" && requestSequence === sequence) {
          renderError(host, error?.message || "This archaeology record could not be loaded.");
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

    function renderArchaeologyDetail(detail) {
      const evidence = detail?.evidence_details && typeof detail.evidence_details === "object"
        ? detail.evidence_details
        : {};
      const body = resourceBody(
        detail.name || detail.title || detail.id,
        detail.why_it_matters || evidence.biblical_relevance || "Curated archaeological evidence",
      );
      const metadata = [detail.item_type, evidence.date_display || detail.period, detail.confidence]
        .filter(Boolean)
        .join(" · ");
      if (metadata) {
        const label = document.createElement("p");
        label.className = "companion-summary-meta";
        label.textContent = metadata;
        body.append(label);
      }
      appendDetailSections(body, [
        ["What you’re looking at", evidence.description],
        ["Physical evidence", evidence.physical_description],
        ["Discovery", evidence.discovery_context],
        ["Dating", evidence.dating_basis],
        ["Why it matters for this passage", evidence.biblical_relevance || detail.why_it_matters],
        ["Scholarly context", evidence.scholarly_context],
        ["Archaeological caution", evidence.interpretive_caution || detail.bhf_caution],
      ]);
      const passages = (detail.scripture_links || [])
        .map(formatArchaeologyPassage)
        .filter(Boolean);
      if (passages.length) appendGroup(body, "Related Scripture", passages.map((title) => ({title})));
      appendArchaeologySource(body, detail.source);
      const back = actionButton("← Back to evidence", "");
      delete back.dataset.openLegacyResource;
      back.dataset.nativeResourceBack = "";
      body.append(back, actionButton("Open Archaeology Library →", "archaeology"));
      commit(body);
    }

    function appendDetailSections(body, sections) {
      sections.filter(([, value]) => value).forEach(([label, value]) => {
        const section = document.createElement("section");
        const heading = document.createElement("h4");
        const text = document.createElement("p");
        heading.textContent = label;
        text.textContent = value;
        section.append(heading, text);
        body.append(section);
      });
    }

    function formatArchaeologyPassage(link) {
      if (typeof link === "string") return link;
      if (!link || !link.book || !link.chapter) return "";
      const start = Number(link.verse_start || 0);
      const end = Number(link.verse_end || start);
      const verses = start ? `:${start}${end > start ? `–${end}` : ""}` : "";
      return `${link.book} ${link.chapter}${verses}`;
    }

    function appendArchaeologySource(body, source) {
      if (!source || (!source.label && !source.url)) return;
      const section = document.createElement("section");
      const heading = document.createElement("h4");
      heading.textContent = "Evidence source";
      section.append(heading);
      if (source.url && /^https?:\/\//i.test(source.url)) {
        const link = document.createElement("a");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = source.label || "View source ↗";
        section.append(link);
      } else {
        const text = document.createElement("p");
        text.textContent = source.label || "Source record available locally";
        section.append(text);
      }
      if (source.license) {
        const license = document.createElement("p");
        license.className = "companion-summary-meta";
        license.textContent = source.license;
        section.append(license);
      }
      body.append(section);
    }

    function saveNativeBackView(focusSelector) {
      if (nativeBackView) return;
      const fragment = document.createDocumentFragment();
      while (host.firstChild) fragment.append(host.firstChild);
      nativeBackView = fragment;
      nativeBackFocusSelector = focusSelector;
    }

    function restoreNativeBackView() {
      if (!nativeBackView) return;
      sequence += 1;
      controller?.abort();
      host.replaceChildren(nativeBackView);
      host.setAttribute("aria-busy", "false");
      nativeBackView = null;
      host.querySelector(nativeBackFocusSelector)?.focus({preventScroll: true});
      nativeBackFocusSelector = "";
    }

    function commit(content) {
      host.replaceChildren(content);
      host.setAttribute("aria-busy", "false");
    }

    return Object.freeze({
      open,
      close,
      showLegacy,
      openCanonicalDetail,
      openArchaeologyDetail,
    });
  }

  async function requestJson(url, signal) {
    if (window.BHFApi?.requestJson) {
      return window.BHFApi.requestJson(url, {signal, headers: {Accept: "application/json"}}, "Resource could not be loaded.");
    }
    let resolvedUrl = url;
    if (window.BHFBackendRouting?.resolveUrl) {
      resolvedUrl = window.BHFBackendRouting.resolveUrl(
        url,
        window.BHFRuntimeConfig || {},
      );
    } else if (String(window.BHFRuntimeConfig?.backendMode || "same-origin") === "remote") {
      throw new Error("BHF backend is not configured for this deployment.");
    }
    const response = await fetch(resolvedUrl, {signal, headers: {Accept: "application/json"}});
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
