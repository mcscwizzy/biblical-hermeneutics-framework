function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function renderMapMarkerPopup(marker) {
  const name = escapeHtml(marker.name || "Unnamed place");
  const region = escapeHtml(marker.region || "Unknown region");
  const description = escapeHtml(marker.description || "No description available.");
  const confidence = escapeHtml(marker.confidence || "unknown");

  return `
    <article class="map-popup">
      <h3>${name}</h3>
      <p class="map-popup-region">${region}</p>
      <p class="map-popup-confidence">Confidence: ${confidence}</p>
      <p class="map-popup-description">${description}</p>
    </article>
  `;
}
