/* Pointer-driven mobile snap behavior for the Study Companion bottom sheet. */
(function () {
  "use strict";

  const ORDER = ["closed", "peek", "study", "full"];
  const DISTANCE_THRESHOLD = 34;
  const MIN_FLING_DISTANCE = 18;
  const VELOCITY_THRESHOLD = 0.42;

  function create(options) {
    const panel = options?.panel;
    if (!panel) return null;
    const handles = Array.from(panel.querySelectorAll("[data-companion-drag-handle]"));
    let gesture = null;
    let suppressClick = false;
    let suppressClickTimer = null;

    handles.forEach((handle) => {
      handle.addEventListener("pointerdown", pointerDown);
      handle.addEventListener("click", suppressDraggedClick, true);
    });

    function pointerDown(event) {
      if (!options.compactViewport() || event.button > 0 || !event.isPrimary) return;
      const state = options.getState();
      const height = panel.getBoundingClientRect().height || snapHeights()[state] || 0;
      gesture = {
        pointerId: event.pointerId,
        target: event.currentTarget,
        state,
        startY: event.clientY,
        lastY: event.clientY,
        lastTime: performance.now(),
        startHeight: height,
        height,
        velocity: 0,
        moved: false,
      };
      try {
        event.currentTarget.setPointerCapture?.(event.pointerId);
      } catch (_error) {
        // Synthetic and older pointer implementations may not support capture.
      }
      // Listen on the window as well as using pointer capture. Some embedded
      // browsers release capture while the sheet is changing height, but the
      // gesture must still finish and snap deterministically.
      window.addEventListener("pointermove", pointerMove, {passive: false});
      window.addEventListener("pointerup", pointerEnd);
      window.addEventListener("pointercancel", pointerCancel);
      panel.classList.add("is-sheet-dragging");
    }

    function pointerMove(event) {
      if (!gesture || event.pointerId !== gesture.pointerId) return;
      const now = performance.now();
      const deltaY = gesture.lastY - event.clientY;
      const elapsed = Math.max(1, now - gesture.lastTime);
      gesture.velocity = (gesture.velocity * 0.55) + ((deltaY / elapsed) * 0.45);
      gesture.lastY = event.clientY;
      gesture.lastTime = now;
      const totalDelta = gesture.startY - event.clientY;
      if (Math.abs(totalDelta) >= 6) gesture.moved = true;
      const heights = snapHeights();
      gesture.height = clamp(gesture.startHeight + totalDelta, 0, heights.full);
      panel.style.setProperty("--companion-drag-height", `${gesture.height}px`);
      panel.dataset.companionDragging = "true";
      if (gesture.moved) event.preventDefault();
    }

    function pointerEnd(event) {
      if (!gesture || event.pointerId !== gesture.pointerId) return;
      const endY = Number.isFinite(event.clientY) ? event.clientY : gesture.lastY;
      const finalDelta = gesture.startY - endY;
      if (Math.abs(finalDelta) >= 6) {
        gesture.moved = true;
        gesture.height = clamp(gesture.startHeight + finalDelta, 0, snapHeights().full);
      }
      const completed = gesture;
      cleanup();
      if (!completed.moved) return;
      suppressClick = true;
      window.clearTimeout(suppressClickTimer);
      suppressClickTimer = window.setTimeout(() => {
        suppressClick = false;
      }, 0);
      const distance = completed.height - completed.startHeight;
      let nextState = completed.state;
      const isFling = Math.abs(distance) >= MIN_FLING_DISTANCE
        && Math.abs(completed.velocity) >= VELOCITY_THRESHOLD;
      if (Math.abs(distance) >= DISTANCE_THRESHOLD || isFling) {
        const projected = completed.height + (completed.velocity * 150);
        nextState = nearestState(projected, snapHeights());
        const currentIndex = ORDER.indexOf(completed.state);
        const direction = distance === 0
          ? completed.velocity > 0 ? 1 : -1
          : distance > 0 ? 1 : -1;
        const nearestIndex = ORDER.indexOf(nextState);
        const adjacentIndex = clamp(currentIndex + direction, 0, ORDER.length - 1);
        const boundedIndex = clamp(nearestIndex, currentIndex - 1, currentIndex + 1);
        nextState = ORDER[boundedIndex === currentIndex ? adjacentIndex : boundedIndex];
      }
      options.setState(nextState, {focus: false, source: "drag"});
    }

    function pointerCancel(event) {
      if (!gesture || event.pointerId !== gesture.pointerId) return;
      const originalState = gesture.state;
      cleanup();
      options.setState(originalState, {focus: false, source: "drag-cancel"});
    }

    function cleanup() {
      if (!gesture) return;
      try {
        gesture.target.releasePointerCapture?.(gesture.pointerId);
      } catch (_error) {
        // Capture may already have been released by the browser.
      }
      window.removeEventListener("pointermove", pointerMove);
      window.removeEventListener("pointerup", pointerEnd);
      window.removeEventListener("pointercancel", pointerCancel);
      gesture = null;
      panel.classList.remove("is-sheet-dragging");
      panel.style.removeProperty("--companion-drag-height");
      delete panel.dataset.companionDragging;
    }

    function suppressDraggedClick(event) {
      if (suppressClick) {
        suppressClick = false;
        window.clearTimeout(suppressClickTimer);
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }

    function snapHeights() {
      const bottomInset = Math.max(0, window.innerHeight - panel.getBoundingClientRect().bottom);
      const full = Math.max(240, window.innerHeight - bottomInset);
      return {
        closed: 0,
        peek: 64,
        study: Math.min(full, Math.min(window.innerHeight * 0.68, 660)),
        full,
      };
    }

    return Object.freeze({
      cancel: cleanup,
      heights: snapHeights,
      isDragging: () => Boolean(gesture),
    });
  }

  function nearestState(height, heights) {
    return ORDER.reduce((best, state) => (
      Math.abs(heights[state] - height) < Math.abs(heights[best] - height) ? state : best
    ), ORDER[0]);
  }

  function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  window.BHFCompanionSheet = Object.freeze({create});
})();
