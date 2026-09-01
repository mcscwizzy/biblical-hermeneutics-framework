/* Selection ownership, aborts, and sequencing for companion context loads. */
(function () {
  "use strict";

  function create(options = {}) {
    let selection = null;
    let sequence = 0;
    let timer = null;
    let controller = null;
    let enhancementController = null;
    let enhancementSequence = 0;
    let record = emptyRecord();
    let localContext = null;

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
      enhancementController?.abort();
      enhancementController = null;
      enhancementSequence += 1;
      const requestSequence = ++sequence;
      localContext = null;
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
        localContext = context;
        record = {key: requestedKey, status: "ready", context, error: ""};
        options.onReady?.(context, requestedSelection, record);
        await enhance(context, requestedSelection, requestedKey, requestSequence);
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

    async function enhance(context, requestedSelection, requestedKey, requestSequence) {
      const enhancement = context?.presentation_enhancement;
      const eligibilitySequence = enhancementSequence;
      if (
        (enhancement?.supported !== true && enhancement?.available !== true)
        || context?.presentation_packet?.presentation_mode === "generated"
        || typeof window.BHFCompanionContext?.enhance !== "function"
      ) return;
      try {
        if (
          typeof window.BHFCompanionContext?.canEnhance === "function"
          && await window.BHFCompanionContext.canEnhance(context) !== true
        ) return;
      } catch (error) {
        options.onEnhancementError?.(error, requestedSelection, record);
        return;
      }
      if (
        requestSequence !== sequence
        || eligibilitySequence !== enhancementSequence
        || requestedKey !== keyFor(selection)
      ) return;
      enhancementController?.abort();
      const requestController = new AbortController();
      enhancementController = requestController;
      const currentEnhancementSequence = ++enhancementSequence;
      const requestedHash = String(enhancement.evidence_hash || "");
      try {
        const result = await window.BHFCompanionContext.enhance(
          requestedSelection,
          context,
          {signal: requestController.signal},
        );
        const responseHash = String(result?.evidence_bundle?.evidence_hash || "");
        if (
          requestSequence !== sequence
          || currentEnhancementSequence !== enhancementSequence
          || requestController.signal.aborted
          || requestedKey !== keyFor(selection)
          || !requestedHash
          || responseHash !== requestedHash
        ) return;
        const enhancedContext = {...context, ...result, presentation_enhancement: enhancement};
        record = {key: requestedKey, status: "ready", context: enhancedContext, error: ""};
        options.onEnhanced?.(enhancedContext, requestedSelection, record);
      } catch (error) {
        if (error?.name === "AbortError" || requestSequence !== sequence) return;
        options.onEnhancementError?.(error, requestedSelection, record);
      }
    }

    function refreshEnhancement() {
      if (!matchesSelection()) return false;
      const requestedSelection = {...selection};
      void enhance(record.context, requestedSelection, keyFor(requestedSelection), sequence);
      return true;
    }

    function cancelEnhancement() {
      enhancementSequence += 1;
      enhancementController?.abort();
      enhancementController = null;
      if (matchesSelection() && localContext) {
        record = {key: keyFor(selection), status: "ready", context: localContext, error: ""};
        options.onPresentationReset?.(localContext, selection, record);
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
      enhancementController?.abort();
      controller = null;
      enhancementController = null;
      sequence += 1;
      enhancementSequence += 1;
      localContext = null;
      record = {key: key || "", status: key ? "loading" : "idle", context: null, error: ""};
    }

    function matchesSelection() {
      return record.status === "ready" && Boolean(record.context) && record.key === keyFor(selection);
    }

    function getRecord() {
      return {...record, context: matchesSelection() ? record.context : null};
    }

    return Object.freeze({
      setSelection,
      schedule,
      invalidate,
      refreshEnhancement,
      cancelEnhancement,
      matchesSelection,
      getRecord,
      keyFor,
    });
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
