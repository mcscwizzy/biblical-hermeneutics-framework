/* Deterministic passage-aware ranking. No AI or network dependency. */
(function () {
  "use strict";

  const BOOK_GROUPS = {
    law: new Set(["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]),
    narrative: new Set([
      "Genesis", "Exodus", "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
      "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
      "Esther", "Matthew", "Mark", "Luke", "John", "Acts",
    ]),
    poetry: new Set(["Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Lamentations"]),
    prophecy: new Set([
      "Isaiah", "Jeremiah", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
      "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
      "Zechariah", "Malachi",
    ]),
    gospel: new Set(["Matthew", "Mark", "Luke", "John"]),
    epistle: new Set([
      "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
      "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
      "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
      "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
    ]),
    apocalyptic: new Set(["Daniel", "Revelation"]),
  };

  const RESOURCES = Object.freeze({
    historical_context: {label: "Historical Context", icon: "⌛", description: "Setting, period, and historical background"},
    cultural_context: {label: "Cultural Context", icon: "◫", description: "Customs and social world behind the text"},
    literary_context: {label: "Literary Context", icon: "¶", description: "Genre, structure, and nearby argument"},
    original_audience: {label: "Original Audience", icon: "◎", description: "How the first hearers may have understood it"},
    covenant_context: {label: "Covenant Context", icon: "∞", description: "Promises and covenant relationships"},
    word_study: {label: "Word Study", icon: "Aa", description: "Greek or Hebrew terms in this passage"},
    commentary: {label: "Tyndale Study Notes", icon: "▤", description: "Published local commentary for this chapter"},
    cross_references: {label: "Cross References", icon: "↗", description: "Related passages across Scripture"},
    people: {label: "People", icon: "♙", description: "People connected with this passage"},
    places: {label: "Places", icon: "⌖", description: "Places connected with this passage"},
    themes: {label: "Themes", icon: "◇", description: "Canonical themes and relationships"},
    archaeology: {label: "Archaeology", icon: "▥", description: "Related records with provenance and cautions"},
    maps: {label: "Maps", icon: "⌖", description: "Places and journeys in this passage"},
    timeline: {label: "Timeline", icon: "⇥", description: "Events and historical relationships"},
    compare_translations: {label: "Compare Translations", icon: "≋", description: "Read wording across installed translations"},
    canonical: {label: "Canonical Knowledge", icon: "⌘", description: "People, places, events, themes, and evidence"},
  });

  const BASE_SCORES = {
    narrative: {historical_context: 18, maps: 18, people: 16, places: 16, archaeology: 14, timeline: 13, commentary: 11, cross_references: 10, literary_context: 8, themes: 7},
    law: {covenant_context: 18, historical_context: 16, cultural_context: 15, word_study: 13, cross_references: 12, themes: 11, archaeology: 9, maps: 8},
    poetry: {literary_context: 20, word_study: 17, themes: 16, cross_references: 14, commentary: 13, cultural_context: 7},
    prophecy: {historical_context: 20, timeline: 18, themes: 16, cross_references: 15, people: 11, places: 11, literary_context: 10, word_study: 9},
    gospel: {historical_context: 18, cultural_context: 17, people: 16, places: 14, maps: 13, word_study: 12, cross_references: 11, commentary: 10},
    epistle: {historical_context: 20, original_audience: 19, word_study: 17, cross_references: 15, themes: 14, commentary: 13, literary_context: 11},
    apocalyptic: {historical_context: 19, timeline: 18, themes: 18, cross_references: 17, literary_context: 15, people: 9, places: 9},
    default: {historical_context: 14, literary_context: 13, word_study: 12, cross_references: 11, themes: 10, commentary: 9},
  };

  function classifyBook(book) {
    const name = String(book || "").trim();
    if (BOOK_GROUPS.apocalyptic.has(name)) return "apocalyptic";
    if (BOOK_GROUPS.gospel.has(name)) return "gospel";
    if (BOOK_GROUPS.epistle.has(name)) return "epistle";
    if (BOOK_GROUPS.poetry.has(name)) return "poetry";
    if (BOOK_GROUPS.prophecy.has(name)) return "prophecy";
    if (BOOK_GROUPS.law.has(name)) return "law";
    if (BOOK_GROUPS.narrative.has(name)) return "narrative";
    return "default";
  }

  function isAvailable(id, availability) {
    const explicit = availability?.[id];
    return explicit !== false;
  }

  function rank(selection, availability = {}) {
    const genre = classifyBook(selection?.book);
    const scores = {...BASE_SCORES.default, ...(BASE_SCORES[genre] || {})};
    const localSignals = {
      commentary: availability.commentary ? 8 : 0,
      word_study: availability.word_study ? 8 : 0,
      maps: Number(availability.mapCount || 0) * 3,
      archaeology: Number(availability.archaeologyCount || 0) * 3,
      people: Number(availability.peopleCount || 0) * 3,
      places: Number(availability.placeCount || 0) * 3,
      themes: Number(availability.themeCount || 0),
      canonical: Number(availability.canonicalCount || 0),
    };
    const ranked = Object.entries(RESOURCES)
      .filter(([id]) => isAvailable(id, availability))
      .map(([id, resource]) => ({
        id,
        ...resource,
        score: Number(scores[id] || 4) + Number(localSignals[id] || 0),
      }))
      .sort((left, right) => right.score - left.score || left.label.localeCompare(right.label));
    return {
      genre,
      recommended: ranked.slice(0, 4),
      deeper: ranked.slice(4),
      all: ranked,
      reason: recommendationReason(genre, selection?.hasPassageSelection),
    };
  }

  function recommendationReason(genre, hasSelection) {
    const focus = hasSelection ? "this passage" : "this chapter";
    const labels = {
      narrative: `Geography, people, and historical setting are emphasized for ${focus}.`,
      law: `Covenant, cultural setting, and language are emphasized for ${focus}.`,
      poetry: `Literary form, key words, and themes are emphasized for ${focus}.`,
      prophecy: `Historical setting, timeline, and canonical themes are emphasized for ${focus}.`,
      gospel: `Historical setting, culture, people, and places are emphasized for ${focus}.`,
      epistle: `Original audience, historical setting, and word study are emphasized for ${focus}.`,
      apocalyptic: `Historical setting, imagery, timeline, and themes are emphasized for ${focus}.`,
      default: `Resources are ranked from locally available evidence for ${focus}.`,
    };
    return labels[genre] || labels.default;
  }

  function suggestedQuestions(selection) {
    const genre = classifyBook(selection?.book);
    const suggestions = {
      narrative: ["Why does this event matter?", "What places shape this scene?", "What historical context helps here?"],
      law: ["How does this fit the covenant?", "What custom is assumed here?", "What Hebrew words matter?"],
      poetry: ["What literary features matter?", "What images or parallel lines stand out?", "What words carry the main idea?"],
      prophecy: ["What historical crisis is in view?", "How would the first audience hear this?", "What themes connect elsewhere?"],
      gospel: ["How would the first audience understand this?", "What cultural detail matters here?", "How does this fit the Gospel’s purpose?"],
      epistle: ["How would the original audience understand this?", "What historical setting matters?", "What Greek words matter here?"],
      apocalyptic: ["What did these images mean to the first audience?", "What historical setting matters?", "Which themes echo earlier Scripture?"],
      default: ["What is the main point here?", "What context matters most?", "How does this connect elsewhere?"],
    };
    return suggestions[genre] || suggestions.default;
  }

  window.BHFStudyRecommendations = Object.freeze({
    resources: RESOURCES,
    classifyBook,
    rank,
    suggestedQuestions,
  });
})();
