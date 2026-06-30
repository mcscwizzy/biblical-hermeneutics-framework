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
  const summary = escapeHtml(layerItem.summary || "No summary available.");
  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${entityType}</p>
      <p class="map-popup-confidence">${period}</p>
      <p class="map-popup-description">${summary}</p>
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
  renderManuscriptPopup,
  renderPoliticalContextPopup,
  renderRoutePopup,
};
