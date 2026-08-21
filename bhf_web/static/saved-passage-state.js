/* Selection-aware state for the Study Companion's Save Passage command. */
(function () {
  "use strict";

  function create(options = {}) {
    let selection = null;
    let selectionKey = "";
    let sequence = 0;

    document.addEventListener("bhf:saved-studies-changed", handleStudiesChanged);

    function notify(status, currentSelection = selection) {
      options.onChange?.({
        status,
        saved: status === "saved" ? true : status === "not-saved" ? false : null,
        loading: status === "loading",
        unavailable: status === "unavailable",
        selection: currentSelection,
      });
    }

    function setSelection(nextSelection) {
      const nextKey = nextSelection?.hasPassageSelection === true
        ? passageKey(nextSelection)
        : "";
      if (nextKey && nextKey === selectionKey) {
        selection = nextSelection;
        return;
      }
      selection = nextSelection || null;
      selectionKey = nextKey;
      sequence += 1;
      notify(selectionKey ? "loading" : "not-saved");
      if (selectionKey) void refresh();
    }

    async function refresh(refreshOptions = {}) {
      const requestedSelection = selection ? {...selection} : null;
      const requestedKey = selectionKey;
      const requestSequence = sequence;
      if (!requestedSelection || !requestedKey) {
        notify("not-saved", requestedSelection);
        return false;
      }
      if (typeof options.loadStudies !== "function") {
        notify("unavailable", requestedSelection);
        return false;
      }
      try {
        const studies = await options.loadStudies(requestedSelection, refreshOptions);
        if (requestSequence !== sequence || requestedKey !== selectionKey) return false;
        if (!Array.isArray(studies)) throw new Error("Saved studies are unavailable.");
        const saved = studies.some(
          (study) => isSavedPassage(study, requestedSelection),
        );
        notify(saved ? "saved" : "not-saved", requestedSelection);
        return saved;
      } catch (_error) {
        if (requestSequence === sequence && requestedKey === selectionKey) {
          notify("unavailable", requestedSelection);
        }
        return false;
      }
    }

    function handleStudiesChanged(event) {
      const detail = event.detail || {};
      if (
        !selectionKey
        || chapterKey(detail) !== chapterKey(selection)
        || !Array.isArray(detail.studies)
      ) return;
      const saved = detail.studies.some(
        (study) => isSavedPassage(study, selection),
      );
      notify(saved ? "saved" : "not-saved");
    }

    function destroy() {
      sequence += 1;
      document.removeEventListener("bhf:saved-studies-changed", handleStudiesChanged);
    }

    return Object.freeze({setSelection, refresh, destroy});
  }

  function isSavedPassage(study, selection) {
    if (!study || !selection || String(study.study_type || "") !== "passage") return false;
    const selectedPassageKey = passageKey(selection);
    return Boolean(selectedPassageKey) && passageKey({
      book: study.book,
      chapter: study.chapter,
      startVerse: study.start_verse,
      endVerse: study.end_verse,
    }) === selectedPassageKey;
  }

  function chapterKey(value) {
    const book = String(value?.book || "").trim().toLowerCase();
    const chapter = Number(value?.chapter || 0);
    return `${book}|${Number.isInteger(chapter) && chapter > 0 ? chapter : 0}`;
  }

  function passageKey(value) {
    const chapter = chapterKey(value);
    if (chapter.endsWith("|0") || chapter.startsWith("|")) return "";
    const start = Number(value?.startVerse ?? value?.start_verse ?? 0);
    const end = Number(value?.endVerse ?? value?.end_verse ?? start ?? 0);
    if (!Number.isInteger(start) || start < 1) return "";
    const normalizedEnd = Number.isInteger(end) && end >= start ? end : start;
    return `${chapter}|${start}|${normalizedEnd}`;
  }

  window.BHFSavedPassageState = Object.freeze({create, isSavedPassage, passageKey});
})();
