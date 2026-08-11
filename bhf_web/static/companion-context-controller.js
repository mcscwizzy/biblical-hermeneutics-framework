/* Selection ownership, aborts, and sequencing for companion context loads. */
(function () {
  "use strict";

  function create(options = {}) {
    let selection = null;
    let sequence = 0;
    let timer = null;
    let controller = null;
    let record = emptyRecord();

    function setSelection(nextSelection, behavior = {}) {
      const nextKey = keyFor(nextSelection);
      const changed = nextKey !== keyFor(selection);
      selection = nextSelection || null;
      if (changed) markStale(nextKey);
      if (behavior.load !== false && nextKey && (changed || !matchesSelection())) schedule();
      return {changed, key: nextKey};
    }

    function schedule() {
      if (!keyFor(selection)) return;
      window.clearTimeout(timer);
      controller?.abort();
      const requestSequence = ++sequence;
      record = {key: keyFor(selection), status: "loading", context: null, error: ""};
      options.onLoading?.(record);
      timer = window.setTimeout(() => load(requestSequence), Number(options.delay ?? 180));
    }

    async function load(requestSequence) {
      if (!selection?.book || !selection?.chapter || !window.BHFCompanionContext) return;
      const requestedSelection = {...selection};
      const requestedKey = keyFor(requestedSelection);
      const requestController = new AbortController();
      controller = requestController;
      try {
        const context = await window.BHFCompanionContext.load(requestedSelection, {
          signal: requestController.signal,
        });
        if (requestSequence !== sequence || requestController.signal.aborted || requestedKey !== keyFor(selection)) return;
        record = {key: requestedKey, status: "ready", context, error: ""};
        options.onReady?.(context, requestedSelection, record);
      } catch (error) {
        if (error?.name === "AbortError" || requestSequence !== sequence) return;
        record = {
          key: requestedKey,
          status: "error",
          context: null,
          error: error?.message || "Study resources could not be checked.",
        };
        options.onError?.(record.error, requestedSelection, record);
      }
    }

    function invalidate(key, behavior = {}) {
      const currentKey = keyFor(selection);
      if (!currentKey || (key && key !== currentKey)) return false;
      markStale(currentKey);
      if (behavior.load !== false) schedule();
      return true;
    }

    function markStale(key) {
      window.clearTimeout(timer);
      controller?.abort();
      controller = null;
      sequence += 1;
      record = {key: key || "", status: key ? "loading" : "idle", context: null, error: ""};
    }

    function matchesSelection() {
      return record.status === "ready" && Boolean(record.context) && record.key === keyFor(selection);
    }

    function getRecord() {
      return {...record, context: matchesSelection() ? record.context : null};
    }

    return Object.freeze({setSelection, schedule, invalidate, matchesSelection, getRecord, keyFor});
  }

  function keyFor(selection) {
    if (!selection?.book || !selection?.chapter) return "";
    return window.BHFCompanionContext?.requestKey?.(selection) || "";
  }

  function emptyRecord() {
    return {key: "", status: "idle", context: null, error: ""};
  }

  window.BHFCompanionContextController = Object.freeze({create});
})();
