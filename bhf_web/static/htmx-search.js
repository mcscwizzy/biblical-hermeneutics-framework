const BHF_BIBLE_SEARCH_STATE = window.BHFBibleSearchState || (window.BHFBibleSearchState = {
  latestBibleSearchRequestId: 0,
});

async function submitBibleSearch(event) {
  event.preventDefault();
  const form = event.target;
  syncBibleSearchConfig(form);
  const queryInput = form.querySelector("[name='query']");
  const query = queryInput ? queryInput.value.trim() : "";
  const translationId = typeof selectedTranslationId === "function" ? selectedTranslationId() : "asv";
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

    if (data.ai_fallback_eligible) {
      updateBibleSearchSummary(`No local ${translationLabel} matches for “${query}”. Checking the Canonical Knowledge Library for likely passages.`);
      setBibleSearchStatus("No local match found. Checking the Canonical Knowledge Library...", "loading");
      await runBibleSearchFallback(form, query, requestId);
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

async function runBibleSearchFallback(form, query, requestId) {
  const payload = new FormData(form);
  const job = await requestJson("/api/bible/search/fallback/jobs", {
    method: "POST",
    body: payload,
    headers: { Accept: "application/json" },
  }, "Could not start the BHF search fallback.");
  if (!job.job_id) {
    throw new Error("Could not start the BHF search fallback.");
  }
  const result = await pollBibleSearchFallback(job.job_id, requestId);
  if (requestId !== BHF_BIBLE_SEARCH_STATE.latestBibleSearchRequestId) {
    return;
  }
  if (Array.isArray(result.results) && result.results.length > 0) {
    showBibleSearchResults();
    updateBibleSearchSummary(`BHF suggested ${result.results.length} likely passage${result.results.length === 1 ? "" : "s"} for “${query}”`);
    clearBibleSearchStatus();
    renderBibleSearchResults(result.results, { source: "ckl_fallback" });
    return;
  }
  clearBibleSearchResults();
}

function syncBibleSearchConfig(searchForm) {
  const askForm = document.querySelector(".ask-form");
  if (!askForm || !searchForm) {
    return;
  }
  for (const name of [
    "profile",
    "runtime_profile_mode",
    "answer_mode",
    "model",
    "base_url",
    "temperature",
    "max_tokens",
    "timeout_seconds",
    "memory_max_turns",
    "session_id",
    "memory_path",
    "reader_translation",
  ]) {
    const askInput = askForm.querySelector(`[name="${name}"]`);
    let searchInput = searchForm.querySelector(`[name="${name}"]`);
    if (!searchInput) {
      searchInput = document.createElement("input");
      searchInput.type = "hidden";
      searchInput.name = name;
      searchForm.appendChild(searchInput);
    }
    if (name === "reader_translation") {
      searchInput.value = askInput && askInput.value ? askInput.value : (typeof selectedTranslationId === "function" ? selectedTranslationId() : "asv");
    } else {
      searchInput.value = askInput ? askInput.value : "";
    }
  }
  syncBibleSearchCheckbox(searchForm, askForm, "show_method_notes");
  syncBibleSearchCheckbox(searchForm, askForm, "memory_enabled");
}

function syncBibleSearchCheckbox(searchForm, askForm, name) {
  const existing = searchForm.querySelector(`[name="${name}"]`);
  const askInput = askForm.querySelector(`[name="${name}"]`);
  const checked = Boolean(askInput && askInput.checked);
  if (!checked && existing) {
    existing.remove();
    return;
  }
  if (checked && !existing) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = "on";
    searchForm.appendChild(input);
    return;
  }
  if (existing) {
    existing.value = "on";
  }
}

async function pollBibleSearchFallback(jobId, requestId) {
  while (true) {
    const status = await requestJson(`/api/bible/search/fallback/status/${encodeURIComponent(jobId)}`, {}, "Could not check BHF fallback search status.");
    if (requestId !== BHF_BIBLE_SEARCH_STATE.latestBibleSearchRequestId) {
      return { results: [], message: "" };
    }
    if (status.done) {
      const result = await requestJson(`/api/bible/search/fallback/result/${encodeURIComponent(jobId)}`, {}, "BHF search fallback failed.");
      return result;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 750));
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
  const isFallbackSource = source !== "local";
  const translationLabel = options.translationLabel || "Text";
  const sourceBadge = isFallbackSource ? "CKL suggested passage" : result.match_type === "direct_reference" ? "Direct reference" : translationLabel;
  const confidenceBadge = isFallbackSource && result.confidence ? `<span class="search-badge">${escapeHtml(String(result.confidence))}</span>` : "";
  const subtitle = isFallbackSource
    ? escapeHtml(result.reason || result.excerpt || "Likely topical connection.")
    : escapeHtml(result.excerpt || "");
  return `
    <article class="search-result-card">
      <div class="search-result-header">
        <div>
          <h4>${escapeHtml(result.reference || "")}</h4>
          <p class="search-result-meta">${subtitle}</p>
        </div>
        <div class="search-result-badges">
          <span class="search-badge ${isFallbackSource ? "source-ckl" : ""}">${escapeHtml(sourceBadge)}</span>
          ${confidenceBadge}
        </div>
      </div>
      <div class="search-result-actions">
        ${canGoToVerse ? `<button type="button" class="secondary" data-search-action="go-to-verse" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}" data-verse-start="${escapeHtml(String(result.verse_start || ""))}" data-verse-end="${escapeHtml(String(result.verse_end || ""))}">Go to verse</button>` : ""}
        <button type="button" class="secondary" data-search-action="open-chapter" data-book="${escapeHtml(result.book || "")}" data-chapter="${escapeHtml(String(result.chapter || ""))}">Open chapter</button>
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
  await navigateToPassage(book, chapter, null, null);
}
