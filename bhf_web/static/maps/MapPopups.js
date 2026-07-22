function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderRoutePopup(route) {
  const name = escapeHtml(route.name || "Unnamed route");
  const period = escapeHtml(route.period || "Unknown period");
  const routeType = escapeHtml(route.route_type || "route");
  const description = escapeHtml(route.description || "No description available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${period}</p>
      <p class="map-popup-confidence">${routeType}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderHistoricalLayerPopup(layerItem) {
  const name = escapeHtml(layerItem.name || "Unnamed layer");
  const period = escapeHtml(layerItem.period || "Unknown period");
  const layerType = escapeHtml(layerItem.layer_type || "layer");
  const description = escapeHtml(layerItem.description || "No description available.");
  const confidence = escapeHtml(layerItem.confidence || "unknown");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${period}</p>
      <p class="map-popup-confidence">${layerType} · Confidence: ${confidence}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderPoliticalContextPopup(layerItem) {
  const name = escapeHtml(layerItem.name || "Unnamed context");
  const entityType = escapeHtml(layerItem.entity_type || "political context");
  const period = escapeHtml(layerItem.period || "Unknown period");
  const summary = escapeHtml(layerItem.summary || layerItem.description || "No summary available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${entityType}</p>
      <p class="map-popup-confidence">${period}</p>
      <p class="map-popup-description">${summary}</p>
    </article>
  `;
}

function renderJourneyStopPopup(journey, stop) {
  const title = escapeHtml(stop?.name || "Unnamed stop");
  const journeyTitle = escapeHtml(journey?.title || "Journey");
  const location = escapeHtml([stop?.region, stop?.modernLocation].filter(Boolean).join(" · ") || "Location not supplied");
  const description = escapeHtml(stop?.description || "No description available.");
  return `
    <article class="map-popup">
      <h3>${title}</h3>
      <p class="map-popup-region">${journeyTitle}</p>
      <p class="map-popup-confidence">${location}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderJourneySegmentPopup(journey, segment) {
  const stopById = new Map((journey?.stops || []).map((stop) => [stop.id, stop]));
  const from = stopById.get(segment?.from);
  const to = stopById.get(segment?.to);
  const title = escapeHtml(segment?.label || "Journey segment");
  const route = escapeHtml(`${from?.name || segment?.from || "Unknown"} → ${to?.name || segment?.to || "Unknown"}`);
  const description = escapeHtml(segment?.description || "No description available.");
  return `
    <article class="map-popup">
      <h3>${title}</h3>
      <p class="map-popup-region">${escapeHtml(journey?.title || "Journey")}</p>
      <p class="map-popup-confidence">${route}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderReferenceFeaturePopup(layer, feature) {
  const title = escapeHtml(feature?.name || "Unnamed feature");
  const layerTitle = escapeHtml(layer?.title || "Reference layer");
  const periods = Array.isArray(feature?.periods) && feature.periods.length
    ? feature.periods.join(" · ")
    : "No period tags";
  const description = escapeHtml(feature?.summary || feature?.description || "No description available.");
  return `
    <article class="map-popup">
      <h3>${title}</h3>
      <p class="map-popup-region">${layerTitle}</p>
      <p class="map-popup-confidence">${escapeHtml(periods)}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}

function renderArchaeologyPopup(item) {
  const name = escapeHtml(item.name || "Unnamed archaeology item");
  const siteName = escapeHtml(item.site_name || "Unknown site");
  const period = escapeHtml(item.period || "Unknown period");
  const itemType = escapeHtml(item.item_type || "archaeology item");
  const relationship = escapeHtml(item.relationship || "");
  const whyItMatters = escapeHtml(item.why_it_matters || "No explanation available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${siteName}</p>
      <p class="map-popup-confidence">${period} · ${itemType}</p>
      <p class="map-popup-description">${relationship ? `${relationship}. ` : ""}${whyItMatters}</p>
    </article>
  `;
}

function renderManuscriptPopup(item) {
  const name = escapeHtml(item.name || "Unnamed manuscript");
  const manuscriptType = escapeHtml(item.manuscript_type || "manuscript");
  const language = escapeHtml(item.language || "Unknown language");
  const date = escapeHtml(item.date || "Unknown date");
  const significance = escapeHtml(item.significance || "No summary available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${manuscriptType}</p>
      <p class="map-popup-confidence">${language} · ${date}</p>
      <p class="map-popup-description">${significance}</p>
    </article>
  `;
}

export {
  escapeHtml,
  renderArchaeologyPopup,
  renderHistoricalLayerPopup,
  renderJourneySegmentPopup,
  renderJourneyStopPopup,
  renderManuscriptPopup,
  renderPoliticalContextPopup,
  renderReferenceFeaturePopup,
  renderRoutePopup,
};
