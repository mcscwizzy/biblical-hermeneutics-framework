export async function loadPlacesForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
  }

  const url = params.toString()
    ? `/api/maps/places-for-passage?${params.toString()}`
    : "/api/maps/places-for-passage";
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load passage map markers.");
  }
  return data;
}

export async function loadRoutesForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
  }

  const url = params.toString()
    ? `/api/maps/routes-for-passage?${params.toString()}`
    : "/api/maps/routes";
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load passage routes.");
  }
  return data;
}

export async function loadHistoricalLayers(context = {}) {
  const params = new URLSearchParams();
  if (context.period && String(context.period).trim() && String(context.period).trim().toLowerCase() !== "all") {
    params.set("period", String(context.period));
  }

  const url = params.toString()
    ? `/api/maps/historical-layers?${params.toString()}`
    : "/api/maps/historical-layers";
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load historical layers.");
  }
  return data;
}

export async function loadArchaeologyForPassage(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  if (context.verseStart || context.startVerse) {
    params.set("verse_start", String(context.verseStart || context.startVerse));
  }
  if (context.verseEnd || context.endVerse) {
    params.set("verse_end", String(context.verseEnd || context.endVerse));
  }
  if (context.selectedText || context.passageText || context.text) {
    params.set("passage_text", context.selectedText || context.passageText || context.text);
  }

  const url = params.toString()
    ? `/api/maps/archaeology-for-passage?${params.toString()}`
    : "/api/maps/archaeology";
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load archaeology markers.");
  }
  return data;
}

export async function loadSavedMapStudies(context = {}) {
  const params = new URLSearchParams();
  if (context.book) {
    params.set("book", context.book);
  }
  if (context.chapter) {
    params.set("chapter", String(context.chapter));
  }
  const url = params.toString() ? `/api/map-studies?${params.toString()}` : "/api/map-studies";
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load saved map studies.");
  }
  return data;
}

export async function loadSavedMapStudy(studyId) {
  const response = await fetch(`/api/map-studies/${encodeURIComponent(studyId)}`, {
    headers: { Accept: "application/json" },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not load saved map study.");
  }
  return data;
}
