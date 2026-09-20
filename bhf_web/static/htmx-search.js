const BHF_BIBLE_SEARCH_STATE = window.BHFBibleSearchState || (window.BHFBibleSearchState = {
  latestBibleSearchRequestId: 0,
});

async function submitBibleSearch(event) {
  event.preventDefault();
  const form = event.target;
  const queryInput = form.querySelector("[name='query']");
  const query = queryInput ? queryInput.value.trim() : "";
  const translationId = typeof selectedTranslationId === "function" ? selectedTranslationId() : "kjv";
  const translationLabel = typeof translationSelectOptionLabel === "function"
    ? translationSelectOptionLabel(translationId, typeof installedTranslationIds === "function" ? installedTranslationIds() : new Set([translationId]))
    : translationId.toUpperCase();
  if (!query) {
    clearBibleSearchResults();
    return;
  }

  const requestId = ++BHF_BIBLE_SEARCH_STATE.latestBibleSearchRequestId;
  updateBibleSearchSummary(`Searching ${translationLabel} for “${query}”`);
  setBibleSearchStatus(`Searching local ${translationLabel} text...`, "loading");
  try {
    const data = await requestJson(`/api/bible/search?${new URLSearchParams({ q: query, limit: "25", translation: translationId })}`, {}, `Could not search the ${translationLabel} text.`);
    if (requestId !== BHF_BIBLE_SEARCH_STATE.latestBibleSearchRequestId) {
      return;
    }
    if (Array.isArray(data.results) && data.results.length > 0) {
      showBibleSearchResults();
      updateBibleSearchSummary(`${data.total_results} local result${data.total_results === 1 ? "" : "s"} for “${query}”`);
      clearBibleSearchStatus();
      renderBibleSearchResults(data.results, { source: "local", translationLabel: data.translation || translationLabel });
      return;
    }

    updateBibleSearchSummary(`No local ${translationLabel} matches for “${query}”`);
    clearBibleSearchResults();
  } catch (error) {
    if (requestId !== BHF_BIBLE_SEARCH_STATE.latestBibleSearchRequestId) {
      return;
    }
    setBibleSearchStatus(error.message || `Could not search the ${translationLabel} text.`, "error");
  }
}

function showBibleSearchResults() {
  const panel = document.querySelector("#reader-search-results");
  if (panel) {
    panel.hidden = false;
  }
  syncBibleSearchClearState();
}

function clearBibleSearchResults() {
  BHF_BIBLE_SEARCH_STATE.latestBibleSearchRequestId += 1;
  const queryInput = document.querySelector("[data-bible-search] [name='query']");
  const panel = document.querySelector("#reader-search-results");
  const body = document.querySelector("#reader-search-results-body");
  const summary = document.querySelector("#reader-search-summary");
  const status = document.querySelector("#reader-search-status");
  if (queryInput) {
    queryInput.value = "";
  }
  if (panel) {
    panel.hidden = true;
  }
  if (body) {
    body.innerHTML = "";
  }
  if (summary) {
    summary.textContent = "";
  }
  if (status) {
    status.hidden = true;
    status.textContent = "";
    status.classList.remove("is-empty", "is-error");
  }
  syncBibleSearchClearState();
}

function updateBibleSearchSummary(text) {
  const summary = document.querySelector("#reader-search-summary");
  if (summary) {
    summary.textContent = text || "";
  }
  syncBibleSearchClearState();
}

function setBibleSearchStatus(message, state) {
  const status = document.querySelector("#reader-search-status");
  if (!status) {
    return;
  }
  status.hidden = false;
  status.textContent = message;
  status.classList.toggle("is-empty", state === "empty");
  status.classList.toggle("is-error", state === "error");
  syncBibleSearchClearState();
}

function clearBibleSearchStatus() {
  const status = document.querySelector("#reader-search-status");
  if (!status) {
    return;
  }
  status.hidden = true;
  status.textContent = "";
  status.classList.remove("is-empty", "is-error");
  syncBibleSearchClearState();
}

function syncBibleSearchClearState() {
  const form = document.querySelector("[data-bible-search]");
  const clearButton = form?.querySelector("[data-search-clear]");
  if (!clearButton) {
    return;
  }
  const queryInput = form.querySelector("[name='query']");
  const panel = document.querySelector("#reader-search-results");
  const hasQuery = Boolean(queryInput && queryInput.value.trim());
  const hasVisibleResults = Boolean(panel && !panel.hidden);
  clearButton.hidden = !(hasQuery || hasVisibleResults);
}

function renderBibleSearchResults(results, options = {}) {
  const body = document.querySelector("#reader-search-results-body");
  if (!body) {
    return;
  }
  if (!Array.isArray(results) || results.length === 0) {
    body.innerHTML = "";
    return;
  }
  const source = options.source || "local";
  body.innerHTML = `
    <div class="search-results-list">
      ${results.map((result) => renderBibleSearchResultCard(result, options)).join("")}
    </div>
  `;
}

function renderBibleSearchResultCard(result, options = {}) {
  const canGoToVerse = Boolean(result.verse_start);
  const source = options.source || "local";
  const translationLabel = options.translationLabel || "Text";
  const sourceBadge = result.match_type === "direct_reference" ? "Direct reference" : translationLabel;
  const subtitle = escapeHtml(result.excerpt || "");
  return `
    <article class="search-result-card">
      <div class="search-result-header">
        <div>
          <h4>${escapeHtml(result.reference || "")}</h4>
          <p class="search-result-meta">${subtitle}</p>
        </div>
        <div class="search-result-badges">
          <span class="search-badge">${escapeHtml(sourceBadge)}</span>
        </div>
      </div>
      <div class="search-result-actions">
        ${canGoToVerse ? `<button type="button" class="secondary" data-search-action="go-to-verse" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}" data-verse-start="${escapeHtml(String(result.verse_start || ""))}" data-verse-end="${escapeHtml(String(result.verse_end || ""))}">Go to verse</button>` : ""}
        <button type="button" class="secondary" data-search-action="open-chapter" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}">Open chapter</button>
        <button type="button" class="secondary" data-search-action="open-new-tab" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}">Open in new tab</button>
      </div>
    </article>
  `;
}

async function handleBibleSearchResultAction(event) {
  const button = event.target.closest("[data-search-action]");
  if (!button) {
    return;
  }
  const book = button.getAttribute("data-book") || "";
  const chapter = Number(button.getAttribute("data-chapter") || "0");
  if (!book || !chapter) {
    return;
  }
  if (button.getAttribute("data-search-action") === "go-to-verse") {
    await navigateToPassage(
      book,
      chapter,
      Number(button.getAttribute("data-verse-start") || "0"),
      Number(button.getAttribute("data-verse-end") || button.getAttribute("data-verse-start") || "0")
    );
    return;
  }
  await navigateToPassage(
    book,
    chapter,
    null,
    null,
    {newTab: button.getAttribute("data-search-action") === "open-new-tab"},
  );
}
