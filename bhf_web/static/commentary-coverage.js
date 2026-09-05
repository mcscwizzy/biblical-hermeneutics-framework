/* Read-only internal view over the released commentary and CKL coverage reports. */
(function () {
  "use strict";

  function text(value) {
    return String(value == null ? "—" : value);
  }

  function setDefinitionList(node, values) {
    if (!node) return;
    node.replaceChildren();
    Object.entries(values || {}).forEach(([key, value]) => {
      const term = document.createElement("dt");
      term.textContent = key.replaceAll("_", " ");
      const definition = document.createElement("dd");
      definition.textContent = text(value);
      node.append(term, definition);
    });
  }

  function render(root, data) {
    const commentary = data.commentary || {};
    const corpus = commentary.corpus_counts || {};
    const totals = (data.ckl || {}).coverage_totals || {};
    setDefinitionList(root.querySelector("[data-commentary-corpus]"), {
      generated: `${corpus.generated || 0} / ${corpus.total_chapters || 0}`,
      validated: corpus.validated || 0,
      partial: corpus.partial || 0,
      needs_review: corpus.needs_review || 0,
      failed: corpus.failed || 0,
    });
    setDefinitionList(root.querySelector("[data-commentary-ckl]"), {
      scope: data.scope || "entire Bible",
      chapters_analyzed: totals.chapters_analyzed || 0,
      evidence_available: totals.evidence_available || 0,
      thin: totals.thin || 0,
      data_gaps: totals.data_gaps || 0,
    });
    setDefinitionList(root.querySelector("[data-commentary-availability]"), commentary.evidence_availability_distribution || {});
    const list = root.querySelector("[data-commentary-expansion-list]");
    list?.replaceChildren(...((data.ckl || {}).expansion_candidates || []).slice(0, 50).map((candidate) => {
      const row = document.createElement("tr");
      [candidate.reference || `${candidate.book} ${candidate.chapter}`, candidate.status, candidate.valid_anchored_evidence, Object.keys(candidate.categories || {}).join(", ") || "—"].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = text(value);
        row.appendChild(cell);
      });
      return row;
    }));
    root.querySelector("[data-commentary-coverage-summary]").hidden = false;
    root.querySelector("[data-commentary-coverage-details]").hidden = false;
  }

  async function load(root) {
    const status = root.querySelector("[data-commentary-coverage-status]");
    const scope = root.querySelector("[data-commentary-coverage-scope]")?.value.trim();
    const query = scope ? `?scope=${encodeURIComponent(scope)}` : "";
    if (status) status.textContent = "Loading coverage…";
    try {
      const response = await fetch(`/api/internal/bhf-commentary/coverage${query}`, {headers: {Accept: "application/json"}});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Coverage report unavailable.");
      render(root, data);
      if (status) status.textContent = `Report loaded for ${data.scope || "the entire Bible"}.`;
    } catch (error) {
      if (status) status.textContent = error.message || "Coverage report unavailable.";
    }
  }

  function boot() {
    const root = document.querySelector("[data-commentary-coverage]");
    if (!root) return;
    root.querySelector("[data-commentary-coverage-refresh]")?.addEventListener("click", () => { void load(root); });
    root.querySelector("[data-commentary-coverage-scope]")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") { event.preventDefault(); void load(root); }
    });
    void load(root);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
