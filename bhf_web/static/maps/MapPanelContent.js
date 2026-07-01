import {
  buildArchaeologyCautionNote,
  buildArchaeologyExplanation,
  buildCautionNote,
  buildHistoricalLayerCautionNote,
  buildHistoricalLayerExplanation,
  buildManuscriptCautionNote,
  buildManuscriptExplanation,
  buildPlaceExplanation,
  buildPoliticalContextCautionNote,
  buildPoliticalContextExplanation,
  buildRouteCautionNote,
  buildRouteExplanation,
  buildSourceText,
  escapeHtml,
  formatPeriodList,
  formatStudyReference,
  prettyConfidence,
  renderMapActionBar,
  renderRelatedPassages,
  renderRelatedPassagesList,
  renderRelatedVerses,
  renderSourceAttribution,
} from "./MapPanelText.js";

function renderMapOrientationCard(options = {}) {
  const {
    title = "How to read this map",
    summary = "This workspace combines exact place pins with broader study overlays. Some passages match a city or site. Others only match a region, empire, route, or historical frame.",
    callout = "",
  } = options;
  const calloutMarkup = callout
    ? `<p class="map-orientation-callout">${escapeHtml(callout)}</p>`
    : "";
  return `
    <section class="map-detail-section map-orientation-card">
      <div class="map-section-header map-section-header-stack">
        <h4>${escapeHtml(title)}</h4>
        <p class="map-orientation-summary">${escapeHtml(summary)}</p>
      </div>
      ${calloutMarkup}
      <div class="map-orientation-list">
        <div class="map-orientation-item">
          <strong>Place pins</strong>
          <p>Use these when the passage matches a curated location with coordinates.</p>
        </div>
        <div class="map-orientation-item">
          <strong>Historical and political layers</strong>
          <p>Use these when the passage is better understood as a region, kingdom, empire, or broad time-setting rather than one pin.</p>
        </div>
        <div class="map-orientation-item">
          <strong>Routes, archaeology, and manuscripts</strong>
          <p>These are optional study layers. Some passages have them; many do not.</p>
        </div>
      </div>
      <div class="map-next-steps">
        <strong>What to do next</strong>
        <p>Click a marker or overlay, toggle layers on the right, or use Expand for a larger map. If no local map data exists, BHF can still show a text-only geography fallback below.</p>
      </div>
    </section>
  `;
}

function renderSavedMapStudies(studies) {
  if (!Array.isArray(studies) || studies.length === 0) {
    return `<p class="empty">No saved map studies for this passage yet.</p>`;
  }
  return studies
    .map((study) => {
      const meta = [
        study.selected_place_id ? `Place: ${study.selected_place_id}` : null,
        study.selected_archaeology_id ? `Archaeology: ${study.selected_archaeology_id}` : null,
        study.selected_manuscript_id ? `Manuscript: ${study.selected_manuscript_id}` : null,
        study.selected_route_id ? `Route: ${study.selected_route_id}` : null,
        study.selected_layer_id ? `Layer: ${study.selected_layer_id}` : null,
      ].filter(Boolean).join(" · ") || "Map study";
      return `
        <article class="saved-map-study" data-saved-map-study-id="${escapeHtml(study.id || "")}">
          <h4>${escapeHtml(study.passage_reference || formatStudyReference(study))}</h4>
          <p class="saved-study-meta">${escapeHtml(meta)}</p>
          <p>${escapeHtml(study.generated_summary || "Saved map state")}</p>
          <div class="note-actions">
            <button type="button" class="secondary" data-saved-map-study-action="open" data-study-id="${escapeHtml(study.id || "")}">Open</button>
            <button type="button" class="secondary danger" data-saved-map-study-action="delete" data-study-id="${escapeHtml(study.id || "")}">Delete</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderSelectedMarker(marker, passageContext, options = {}) {
  const relatedPassages = marker.related_passages && Array.isArray(marker.related_passages.groups)
    ? marker.related_passages
    : null;
  const relatedVerses = Array.isArray(marker.related_references) ? marker.related_references : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildCautionNote(marker);
  const explanation = buildPlaceExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);
  const aliases = Array.isArray(marker.aliases) ? marker.aliases : [];
  const periods = formatPeriodList(marker.periods);
  const historicalOverview = options.historicalOverview || "";

  return `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(marker.name || "Unnamed place")}</h3>
          <div class="map-details-subtitle">${escapeHtml(marker.region || marker.ancient_region || "Unknown region")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(marker.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Aliases</h4>
        <p>${aliases.length ? aliases.map(escapeHtml).join(", ") : "No aliases in the local data."}</p>
      </section>

      <section class="map-detail-section">
        <h4>Periods</h4>
        <p>${escapeHtml(periods)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Modern location</h4>
        <p>${escapeHtml(marker.modern_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Ancient region</h4>
        <p>${escapeHtml(marker.ancient_region || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderRelatedPassages(relatedPassages || relatedVerses)}
      </section>

      <section class="map-detail-section map-attribution">
        <h4>Attribution</h4>
        ${renderSourceAttribution(marker, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this location matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Geographical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("place", marker)}
      ${historicalOverview}
    </div>
  `;
}

function renderSelectedArchaeology(marker, passageContext, options = {}) {
  const scriptureLinks = Array.isArray(marker.scripture_links) ? marker.scripture_links : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildArchaeologyCautionNote(marker);
  const explanation = buildArchaeologyExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);
  const archaeologyOverview = options.archaeologyOverview || "";

  return `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(marker.name || "Unnamed archaeology item")}</h3>
          <div class="map-details-subtitle">${escapeHtml(marker.site_name || marker.location || "Unknown location")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(marker.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Type</h4>
        <p>${escapeHtml(marker.item_type || "Archaeology item")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Period</h4>
        <p>${escapeHtml(marker.period || "Unknown period")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Location</h4>
        <p>${escapeHtml(marker.location || marker.site_name || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderRelatedVerses(scriptureLinks)}
      </section>

      <section class="map-detail-section">
        <h4>Relationship</h4>
        <p>${escapeHtml(marker.relationship || "No relationship text recorded in the local data.")}</p>
      </section>

      <section class="map-detail-section map-attribution">
        <h4>Attribution</h4>
        ${renderSourceAttribution(marker, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Archaeological context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("archaeology", marker)}
      ${archaeologyOverview}
    </div>
  `;
}

function renderSelectedManuscript(marker, passageContext, options = {}) {
  const scriptureLinks = Array.isArray(marker.scripture_links) ? marker.scripture_links : [];
  const confidenceLabel = prettyConfidence(marker.confidence);
  const caution = buildManuscriptCautionNote(marker);
  const explanation = buildManuscriptExplanation(marker, passageContext);
  const sourceText = buildSourceText(marker);
  const relatedBooks = Array.isArray(marker.related_books) ? marker.related_books : [];
  const manuscriptOverview = options.manuscriptOverview || "";

  return `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(marker.name || "Unnamed manuscript")}</h3>
          <div class="map-details-subtitle">${escapeHtml(marker.discovery_location || marker.current_location || "Unknown location")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(marker.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Type</h4>
        <p>${escapeHtml(marker.manuscript_type || "Manuscript")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Language</h4>
        <p>${escapeHtml(marker.language || "Unknown language")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Date</h4>
        <p>${escapeHtml(marker.date || "Unknown date")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Material</h4>
        <p>${escapeHtml(marker.material || "Unknown material")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Discovery location</h4>
        <p>${escapeHtml(marker.discovery_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Current location</h4>
        <p>${escapeHtml(marker.current_location || "Not supplied in the local data.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related books</h4>
        <p>${relatedBooks.length ? relatedBooks.map(escapeHtml).join(", ") : "No related books recorded."}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related passages</h4>
        ${renderRelatedVerses(scriptureLinks)}
      </section>

      <section class="map-detail-section">
        <h4>Significance</h4>
        <p>${escapeHtml(marker.significance || "No significance text recorded.")}</p>
      </section>

      <section class="map-detail-section map-attribution compact">
        <h4>Attribution</h4>
        ${renderSourceAttribution(marker, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Textual / Historical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution compact">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("manuscript", marker)}
      ${manuscriptOverview}
    </div>
  `;
}

function renderSelectedRoute(route, passageContext, options = {}) {
  const scriptureLinks = Array.isArray(route.scripture_links) ? route.scripture_links : [];
  const confidenceLabel = prettyConfidence(route.confidence);
  const caution = buildRouteCautionNote(route);
  const explanation = buildRouteExplanation(route, passageContext);
  const sourceText = buildSourceText(route);
  const historicalOverview = options.historicalOverview || "";

  return `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(route.name || "Unnamed route")}</h3>
          <div class="map-details-subtitle">${escapeHtml(route.period || "Unknown period")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(route.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Route type</h4>
        <p>${escapeHtml(route.route_type || "Route")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Related verses</h4>
        ${renderRelatedVerses(scriptureLinks)}
      </section>

      <section class="map-detail-section map-attribution compact">
        <h4>Attribution</h4>
        ${renderSourceAttribution(route, sourceText)}
      </section>

      <section class="map-detail-section">
        <h4>Why this route matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Geographical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution compact">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("route", route)}
      ${historicalOverview}
    </div>
  `;
}

function renderSelectedHistoricalLayer(layer, passageContext, options = {}) {
  const confidenceLabel = prettyConfidence(layer.confidence);
  const caution = buildHistoricalLayerCautionNote(layer);
  const explanation = buildHistoricalLayerExplanation(layer, passageContext);
  const sourceText = buildSourceText(layer);
  const historicalOverview = options.historicalOverview || "";

  return `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(layer.name || "Unnamed layer")}</h3>
          <div class="map-details-subtitle">${escapeHtml(layer.period || "Unknown period")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(layer.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Layer type</h4>
        <p>${escapeHtml(layer.layer_type || "Layer")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Description</h4>
        <p>${escapeHtml(layer.description || "No description available.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Why this layer matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Historical / Geographical context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("layer", layer)}
      ${historicalOverview}
    </div>
  `;
}

function renderSelectedPoliticalContext(layer, passageContext, options = {}) {
  const confidenceLabel = prettyConfidence(layer.confidence);
  const caution = buildPoliticalContextCautionNote(layer);
  const explanation = buildPoliticalContextExplanation(layer, passageContext);
  const sourceText = buildSourceText(layer);
  const politicalOverview = options.politicalOverview || "";

  return `
    <div class="map-details-card">
      <div class="map-details-header">
        <div>
          <h3>${escapeHtml(layer.name || "Unnamed political context")}</h3>
          <div class="map-details-subtitle">${escapeHtml(layer.entity_type || layer.period || "Unknown period")}</div>
        </div>
        <span class="map-confidence confidence-${escapeHtml(String(layer.confidence || "unknown"))}">
          ${escapeHtml(confidenceLabel)}
        </span>
      </div>

      <section class="map-detail-section">
        <h4>Summary</h4>
        <p>${escapeHtml(layer.summary || "No summary available.")}</p>
      </section>

      <section class="map-detail-section">
        <h4>Period</h4>
        <p>${escapeHtml(formatPeriodList(layer.periods))}</p>
      </section>

      <section class="map-detail-section">
        <h4>Passage links</h4>
        ${renderRelatedVerses(Array.isArray(layer.scripture_links) ? layer.scripture_links : [])}
      </section>

      <section class="map-detail-section">
        <h4>Source</h4>
        <p>${escapeHtml(sourceText)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Why this matters</h4>
        <p>${escapeHtml(explanation.why)}</p>
      </section>

      <section class="map-detail-section">
        <h4>Political context</h4>
        <p>${escapeHtml(explanation.context)}</p>
      </section>

      <section class="map-detail-section map-caution">
        <h4>BHF caution</h4>
        <p>${escapeHtml(caution)}</p>
      </section>

      ${renderMapActionBar("political_context", layer)}
      ${politicalOverview}
    </div>
  `;
}

function renderHistoricalLayerOverview(layers, visibleHistoricalLayerIds) {
  const visibleIds = visibleHistoricalLayerIds || new Set();
  const list = Array.isArray(layers) ? layers : [];
  const visibleCount = list.filter((layer) => visibleIds.has(layer.id)).length;
  const items = list
    .map((layer) => {
      const checked = visibleIds.has(layer.id) ? "checked" : "";
      return `
        <label class="map-layer-toggle">
          <input
            type="checkbox"
            data-historical-layer-toggle
            data-layer-id="${escapeHtml(layer.id)}"
            ${checked}
          >
          <span>
            <strong>${escapeHtml(layer.name || "Unnamed layer")}</strong>
            <span>${escapeHtml(layer.period || "Unknown period")} · ${escapeHtml(prettyConfidence(layer.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Historical layers</h4>
        <span>${visibleCount}/${list.length} shown</span>
      </div>
      ${
        list.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No historical layers match the selected period.</p>`
      }
      <p class="map-layer-note">These borders are broad study overlays. Use them to understand the setting and period, not as exact boundary claims.</p>
    </section>
  `;
}

function renderPoliticalContextLayerOverview(layers, visiblePoliticalContextLayerIds) {
  const visibleIds = visiblePoliticalContextLayerIds || new Set();
  const list = Array.isArray(layers) ? layers : [];
  const visibleCount = list.filter((layer) => visibleIds.has(layer.id)).length;
  const items = list
    .map((layer) => {
      const checked = visibleIds.has(layer.id) ? "checked" : "";
      return `
        <label class="map-layer-toggle">
          <input
            type="checkbox"
            data-political-context-toggle
            data-layer-id="${escapeHtml(layer.id)}"
            ${checked}
          >
          <span>
            <strong>${escapeHtml(layer.name || "Unnamed context")}</strong>
            <span>${escapeHtml(layer.entity_type || layer.period || "Unknown period")} · ${escapeHtml(prettyConfidence(layer.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Political context</h4>
        <span>${visibleCount}/${list.length} shown</span>
      </div>
      ${
        list.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No political context layers match the selected period.</p>`
      }
      <p class="map-layer-note">These overlays explain the larger world behind the passage. They are intentionally broad and may represent a region or empire rather than one exact place.</p>
    </section>
  `;
}

function renderArchaeologyLayerOverview(markers, archaeologyVisible) {
  const list = Array.isArray(markers) ? markers : [];
  const visibleCount = archaeologyVisible ? list.length : 0;
  const items = list
    .map((marker) => {
      return `
        <label class="map-layer-toggle">
          <input type="radio" name="archaeology-item" value="${escapeHtml(marker.id)}" disabled>
          <span>
            <strong>${escapeHtml(marker.name || "Unnamed item")}</strong>
            <span>${escapeHtml(marker.site_name || marker.location || "Unknown location")} · ${escapeHtml(prettyConfidence(marker.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Archaeology layer</h4>
        <span>${visibleCount}/${list.length} shown</span>
      </div>
      ${
        list.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No curated archaeology items are stored for this passage right now.</p>`
      }
      <p class="map-layer-note">Archaeology items are optional study aids. They can add historical texture, but they do not prove one interpretation by themselves.</p>
    </section>
  `;
}

function renderManuscriptLayerOverview(markers, manuscriptsVisible) {
  const list = Array.isArray(markers) ? markers : [];
  const visibleCount = manuscriptsVisible ? list.length : 0;
  const items = list
    .map((marker) => {
      return `
        <label class="map-layer-toggle">
          <input type="radio" name="manuscript-item" value="${escapeHtml(marker.id)}" disabled>
          <span>
            <strong>${escapeHtml(marker.name || "Unnamed manuscript")}</strong>
            <span>${escapeHtml(marker.discovery_location || marker.current_location || "Unknown location")} · ${escapeHtml(prettyConfidence(marker.confidence))}</span>
          </span>
        </label>
      `;
    })
    .join("");

  return `
    <section class="map-detail-section map-layer-section">
      <div class="map-section-header">
        <h4>Manuscript layer</h4>
        <span>${visibleCount}/${list.length} shown</span>
      </div>
      ${
        list.length
          ? `<div class="map-layer-list">${items}</div>`
          : `<p class="empty map-details-empty">No curated manuscript items are stored for this passage right now.</p>`
      }
      <p class="map-layer-note">Manuscripts are textual witnesses, not archaeology finds. Locations are shown cautiously when the local record includes them.</p>
    </section>
  `;
}

export {
  renderMapOrientationCard,
  renderSavedMapStudies,
  renderSelectedArchaeology,
  renderSelectedHistoricalLayer,
  renderSelectedMarker,
  renderSelectedManuscript,
  renderSelectedPoliticalContext,
  renderSelectedRoute,
  renderHistoricalLayerOverview,
  renderPoliticalContextLayerOverview,
  renderArchaeologyLayerOverview,
  renderManuscriptLayerOverview,
  renderRelatedPassages,
  renderRelatedPassagesList,
  renderRelatedVerses,
  renderSourceAttribution,
};
