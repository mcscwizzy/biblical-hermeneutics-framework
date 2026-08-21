/* Shared, framework-free Scripture context for every study surface. */
(function () {
  "use strict";

  const listeners = new Set();
  let state = Object.freeze(normalize({}));

  function positiveInteger(value) {
    const number = Number(value);
    return Number.isInteger(number) && number > 0 ? number : null;
  }

  function selectedVerseNumbers(value, startVerse, endVerse) {
    if (Array.isArray(value) && value.length) {
      return Array.from(new Set(value.map(positiveInteger).filter(Boolean)))
        .sort((left, right) => left - right);
    }
    if (!startVerse) return [];
    const last = endVerse || startVerse;
    return Array.from(
      {length: Math.max(0, last - startVerse + 1)},
      (_unused, index) => startVerse + index,
    );
  }

  function formatReference(book, chapter, verses) {
    if (!book || !chapter) return "";
    if (!verses.length) return `${book} ${chapter}`;
    const ranges = [];
    let start = verses[0];
    let end = start;
    verses.slice(1).forEach((verse) => {
      if (verse === end + 1) {
        end = verse;
        return;
      }
      ranges.push(start === end ? String(start) : `${start}-${end}`);
      start = verse;
      end = verse;
    });
    ranges.push(start === end ? String(start) : `${start}-${end}`);
    return `${book} ${chapter}:${ranges.join(",")}`;
  }

  function normalize(value) {
    const source = value && typeof value === "object" ? value : {};
    const book = String(source.book || "").trim();
    const chapter = positiveInteger(source.chapter);
    const proposedStart = positiveInteger(source.startVerse ?? source.verseStart);
    const proposedEnd = positiveInteger(source.endVerse ?? source.verseEnd);
    const verses = selectedVerseNumbers(
      source.selectedVerses,
      proposedStart,
      proposedEnd,
    );
    const startVerse = verses[0] || proposedStart;
    const endVerse = verses[verses.length - 1] || proposedEnd || startVerse;
    const selectedText = String(source.selectedText ?? source.text ?? "").trim();
    const translation = String(source.translation || "").trim().toLowerCase();
    const selectedWord = source.selectedWord && typeof source.selectedWord === "object"
      ? Object.freeze({...source.selectedWord})
      : null;
    const reference = formatReference(book, chapter, verses);
    const level = selectedWord
      ? "word"
      : verses.length > 1
        ? "passage"
        : verses.length === 1
          ? "verse"
          : chapter
            ? "chapter"
            : book
              ? "book"
              : "none";

    return {
      book,
      chapter,
      startVerse: startVerse || null,
      endVerse: endVerse || null,
      selectedVerses: Object.freeze(verses),
      selectedText,
      translation,
      selectedWord,
      reference,
      level,
      hasPassageSelection: verses.length > 0,
    };
  }

  function sameState(left, right) {
    return JSON.stringify(left) === JSON.stringify(right);
  }

  function publish(nextValue, source) {
    const nextState = Object.freeze(normalize(nextValue));
    if (sameState(state, nextState)) return state;
    const previous = state;
    state = nextState;
    const detail = {selection: state, previous, source: source || "unknown"};
    listeners.forEach((listener) => listener(state, detail));
    document.dispatchEvent(new CustomEvent("bhf:study-selection-changed", {detail}));
    return state;
  }

  function setChapter(value, source = "reader") {
    return publish({
      book: value?.book,
      chapter: value?.chapter,
      translation: value?.translation,
    }, source);
  }

  function setSelection(value, source = "reader") {
    return publish({...state, ...value}, source);
  }

  function clearSelection(source = "reader") {
    return publish({
      book: state.book,
      chapter: state.chapter,
      translation: state.translation,
    }, source);
  }

  function subscribe(listener, options = {}) {
    if (typeof listener !== "function") return function () {};
    listeners.add(listener);
    if (options.immediate !== false) listener(state, {selection: state, source: "subscribe"});
    return () => listeners.delete(listener);
  }

  window.BHFStudySelection = Object.freeze({
    getState: () => state,
    setChapter,
    setSelection,
    clearSelection,
    subscribe,
    normalize,
    formatReference,
  });
})();
