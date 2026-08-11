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
    };
  }

  window.BHFCompanionHistory = Object.freeze({create});
})();
