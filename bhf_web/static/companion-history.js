/* Meaningful browser history for Study Companion states and resources. */
(function () {
  "use strict";

  const STATE_KEY = "bhfStudyCompanion";

  function create(options = {}) {
    let applying = false;

    window.addEventListener("popstate", handlePopState);

    function initialize(snapshot) {
      replace(snapshot);
    }

    function push(snapshot) {
      if (applying) return;
      window.history.pushState(mergedState(snapshot), "", window.location.href);
    }

    function replace(snapshot) {
      if (applying) return;
      window.history.replaceState(mergedState(snapshot), "", window.location.href);
    }

    function current() {
      return normalize(window.history.state?.[STATE_KEY]);
    }

    function isCurrentResource() {
      return Boolean(current()?.resource);
    }

    function backFromResource(fallback) {
      if (!isCurrentResource()) {
        fallback?.();
        return false;
      }
      window.history.back();
      return true;
    }

    function handlePopState(event) {
      const snapshot = normalize(event.state?.[STATE_KEY]);
      if (!snapshot) return;
      applying = true;
      Promise.resolve(options.apply?.(snapshot)).finally(() => {
        applying = false;
      });
    }

    function mergedState(snapshot) {
      return {...(window.history.state || {}), [STATE_KEY]: normalize(snapshot)};
    }

    function destroy() {
      window.removeEventListener("popstate", handlePopState);
    }

    return Object.freeze({initialize, push, replace, current, isCurrentResource, backFromResource, destroy});
  }

  function normalize(value) {
    if (!value || typeof value !== "object") return null;
    return {
      state: ["closed", "peek", "study", "full"].includes(value.state) ? value.state : "study",
      mode: value.mode === "explore" ? "explore" : "passage",
      resource: value.resource ? String(value.resource) : null,
      trail: normalizeTrail(value.trail),
    };
  }

  function normalizeTrail(value) {
    if (!value || typeof value !== "object" || !Array.isArray(value.nodes) || !value.nodes.length) return null;
    const sourceNodes = value.nodes.length > 12
      ? [value.nodes[0], ...value.nodes.slice(-11)]
      : value.nodes;
    const nodes = sourceNodes.map(normalizeTrailNode).filter(Boolean);
    if (!nodes.length) return null;
    return {
      originSelection: normalizeSelection(value.originSelection),
      nodes,
      activeIndex: Math.min(Math.max(Number(value.activeIndex) || 0, 0), nodes.length - 1),
    };
  }

  function normalizeTrailNode(value) {
    if (!value || typeof value !== "object" || !["passage", "evidence", "subject"].includes(value.kind)) return null;
    const node = {
      kind: value.kind,
      id: historyText(value.id, 240),
      label: historyText(value.label, 240),
      selection: normalizeSelection(value.selection),
      relationshipHops: Math.min(Math.max(Number(value.relationshipHops) || 0, 0), 3),
      focusControlId: historyText(value.focusControlId, 260),
    };
    ["reference", "targetId", "subjectId", "parentObjectId"].forEach((key) => {
      const text = historyText(value[key], 240);
      if (text) node[key] = text;
    });
    const relationship = normalizeRelationship(value.relationship);
    if (relationship) node.relationship = relationship;
    return node;
  }

  function normalizeSelection(value) {
    if (!value || typeof value !== "object") return null;
    const book = historyText(value.book, 80);
    const chapter = positiveInteger(value.chapter);
    if (!book || !chapter) return null;
    const selectedVerses = Array.isArray(value.selectedVerses)
      ? [...new Set(value.selectedVerses.map(positiveInteger).filter(Boolean))].slice(0, 200)
      : [];
    const selection = {
      book,
      chapter,
      startVerse: positiveInteger(value.startVerse) || null,
      endVerse: positiveInteger(value.endVerse) || null,
      selectedVerses,
      selectedText: historyText(value.selectedText, 2400),
      translation: historyText(value.translation, 40),
      reference: historyText(value.reference, 160),
    };
    if (value.selectedWord && typeof value.selectedWord === "object") {
      selection.selectedWord = Object.fromEntries(Object.entries(value.selectedWord)
        .slice(0, 8)
        .map(([key, entry]) => [historyText(key, 40), historyText(entry, 160)])
        .filter(([key, entry]) => key && entry));
    } else {
      selection.selectedWord = null;
    }
    return selection;
  }

  function normalizeRelationship(value) {
    if (!value || typeof value !== "object") return null;
    const result = {};
    [
      "id", "sourceId", "targetId", "connectionType", "originalRelationshipType", "direction",
      "relationshipMode", "temporalLayer", "basisKind", "parentObjectId", "localRecordId",
      "targetEvidenceId", "targetResolutionStatus", "notes", "weight", "anchor",
    ]
      .forEach((key) => {
        const text = historyText(value[key], 500);
        if (text) result[key] = text;
      });
    return Object.keys(result).length ? result : null;
  }

  function positiveInteger(value) {
    const number = Number(value || 0);
    return Number.isInteger(number) && number > 0 ? number : 0;
  }

  function historyText(value, limit) {
    return (typeof value === "string" || typeof value === "number")
      ? String(value).slice(0, limit)
      : "";
  }

  window.BHFCompanionHistory = Object.freeze({create});
})();
