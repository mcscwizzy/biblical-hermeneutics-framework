/* Selection-aware state for the Study Companion's Save Passage command. */
(function () {
  "use strict";

  function create(options = {}) {
    let selection = null;
    let selectionKey = "";
    let sequence = 0;

    document.addEventListener("bhf:saved-studies-changed", handleStudiesChanged);

    function setSelection(nextSelection) {
      const nextKey = passageKey(nextSelection);
      if (nextKey && nextKey === selectionKey) {
        selection = nextSelection;
        return;
      }
      selection = nextSelection || null;
      selectionKey = nextKey;
      sequence += 1;
      options.onChange?.({saved: false, loading: Boolean(selectionKey), selection});
      if (selectionKey) void refresh();
    }

    async function refresh(refreshOptions = {}) {
      const requestedSelection = selection ? {...selection} : null;
      const requestedKey = selectionKey;
      const requestSequence = sequence;
      if (!requestedSelection || !requestedKey || typeof options.loadStudies !== "function") {
        options.onChange?.({saved: false, loading: false, selection: requestedSelection});
        return false;
      }
      try {
        const studies = await options.loadStudies(requestedSelection, refreshOptions);
        if (requestSequence !== sequence || requestedKey !== selectionKey) return false;
        const saved = (Array.isArray(studies) ? studies : []).some(
          (study) => isSavedPassage(study, requestedSelection),
        );
        options.onChange?.({saved, loading: false, selection: requestedSelection});
        return saved;
      } catch (_error) {
        if (requestSequence === sequence && requestedKey === selectionKey) {
          options.onChange?.({saved: false, loading: false, unavailable: true, selection: requestedSelection});
        }
        return false;
      }
    }

    function handleStudiesChanged(event) {
      const detail = event.detail || {};
      if (!selectionKey || chapterKey(detail) !== chapterKey(selection)) return;
      const saved = (Array.isArray(detail.studies) ? detail.studies : []).some(
        (study) => isSavedPassage(study, selection),
      );
      options.onChange?.({saved, loading: false, selection});
    }

    function destroy() {
      sequence += 1;
      document.removeEventListener("bhf:saved-studies-changed", handleStudiesChanged);
    }

    return Object.freeze({setSelection, refresh, destroy});
  }

  function isSavedPassage(study, selection) {
    if (!study || !selection || String(study.study_type || "") !== "passage") return false;
    return passageKey({
      book: study.book,
      chapter: study.chapter,
      startVerse: study.start_verse,
      endVerse: study.end_verse,
    }) === passageKey(selection);
  }

  function chapterKey(value) {
    return `${String(value?.book || "").trim().toLowerCase()}|${Number(value?.chapter || 0)}`;
  }

  function passageKey(value) {
    const chapter = chapterKey(value);
    if (chapter.endsWith("|0") || chapter.startsWith("|")) return "";
    const start = Number(value?.startVerse ?? value?.start_verse ?? 0);
    const end = Number(value?.endVerse ?? value?.end_verse ?? start ?? 0);
    return `${chapter}|${start}|${end || start}`;
  }

  window.BHFSavedPassageState = Object.freeze({create, isSavedPassage, passageKey});
})();
