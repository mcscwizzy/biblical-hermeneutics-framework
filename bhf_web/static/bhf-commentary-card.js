/* Read-only BHF Commentary v1.0 projection for the Study Companion. */
(function () {
  "use strict";

  const AVAILABILITY_LABELS = Object.freeze({
    AVAILABLE: "Context available",
    THIN: "Limited contextual evidence",
    DATA_GAP: "Contextual evidence not currently available",
  });
  const cache = new Map();

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
    };
  }

  function clearChildren(element) {
    if (element) element.replaceChildren();
  }

  function setText(element, value) {
    if (element) element.textContent = value || "";
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

  function init(root) {
    const parts = elements(root);
    let sequence = 0;
    let controller = null;

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
    });
    window.BHFStudySelection?.subscribe?.((selection) => { void load(selection); });
    return {load, render: (payload) => renderReady(parts, normalizePayload(payload))};
  }

  window.BHFCommentaryCard = Object.freeze({
    init,
    normalizePayload,
    availabilityLabel,
  });

  function boot() {
    const root = document.querySelector("[data-bhf-commentary-card]");
    if (root) init(root);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
