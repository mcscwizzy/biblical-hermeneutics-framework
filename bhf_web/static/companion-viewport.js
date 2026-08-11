/* Visual-viewport and focused-input coordination for the mobile companion. */
(function () {
  "use strict";

  function create(options = {}) {
    const panel = options.panel;
    if (!panel) return null;
    const visualViewport = window.visualViewport;
    let scrollFrame = null;

    panel.addEventListener("focusin", handleFocusIn);
    panel.addEventListener("focusout", handleFocusOut);
    visualViewport?.addEventListener("resize", updateViewport);
    visualViewport?.addEventListener("scroll", updateViewport);
    window.addEventListener("resize", updateViewport);
    updateViewport();

    function handleFocusIn(event) {
      if (!isTextField(event.target) || !options.compactViewport?.()) return;
      document.body.classList.add("companion-input-focused");
      options.ensureVisible?.();
      updateViewport();
      window.cancelAnimationFrame(scrollFrame);
      scrollFrame = window.requestAnimationFrame(() => {
        event.target.scrollIntoView?.({block: "nearest", inline: "nearest"});
      });
    }

    function handleFocusOut() {
      window.setTimeout(() => {
        if (panel.contains(document.activeElement) && isTextField(document.activeElement)) return;
        document.body.classList.remove("companion-input-focused", "companion-keyboard-open");
        updateViewport();
      }, 0);
    }

    function updateViewport() {
      const viewport = window.visualViewport;
      const height = viewport?.height || window.innerHeight;
      const offsetTop = viewport?.offsetTop || 0;
      const hiddenBottom = Math.max(0, window.innerHeight - height - offsetTop);
      document.documentElement.style.setProperty("--companion-visual-height", `${height}px`);
      document.documentElement.style.setProperty("--companion-visual-bottom", `${hiddenBottom}px`);
      const focused = document.body.classList.contains("companion-input-focused");
      document.body.classList.toggle("companion-keyboard-open", focused && hiddenBottom > 80);
    }

    function destroy() {
      panel.removeEventListener("focusin", handleFocusIn);
      panel.removeEventListener("focusout", handleFocusOut);
      visualViewport?.removeEventListener("resize", updateViewport);
      visualViewport?.removeEventListener("scroll", updateViewport);
      window.removeEventListener("resize", updateViewport);
      window.cancelAnimationFrame(scrollFrame);
    }

    return Object.freeze({update: updateViewport, destroy});
  }

  function isTextField(target) {
    return target?.matches?.("input:not([type]), input[type='text'], input[type='search'], input[type='email'], input[type='url'], textarea, [contenteditable='true']");
  }

  window.BHFCompanionViewport = Object.freeze({create});
})();
