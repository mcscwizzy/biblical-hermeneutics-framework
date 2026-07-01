function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatReference(context) {
  if (!context || !context.book || !context.chapter) {
    return "";
  }
  const verseStart = Number(context.verseStart || context.startVerse || 0);
  const verseEnd = Number(context.verseEnd || context.endVerse || verseStart || 0);
  if (!verseStart) {
    return `${context.book} ${context.chapter}`;
  }
  return verseStart === verseEnd
    ? `${context.book} ${context.chapter}:${verseStart}`
    : `${context.book} ${context.chapter}:${verseStart}-${verseEnd}`;
}

function formatStudyReference(study) {
  if (!study || !study.book || !study.chapter) {
    return "Unknown passage";
  }
  const suffix = Number(study.start_verse) === Number(study.end_verse)
    ? `${study.start_verse || ""}`
    : `${study.start_verse || ""}-${study.end_verse || ""}`;
  return suffix && suffix !== "-" ? `${study.book} ${study.chapter}:${suffix}` : `${study.book} ${study.chapter}`;
}

function buildPlaceExplanation(marker, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = marker.name || "This place";
  const region = marker.ancient_region || marker.region || "the ancient setting";
  return {
    why: `${name}${passagePhrase} helps orient the reader in the biblical story and keeps the geography concrete without overclaiming what the text does not say.`,
    context: `${name} sits in ${region}. The local data connects it to the passage through curated references, and the marker should be read as historical context rather than proof of interpretation.`,
  };
}

function buildRouteExplanation(route, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = route.name || "This route";
  const period = route.period || "the relevant biblical period";
  return {
    why: `${name}${passagePhrase} helps trace movement through ${period} and clarifies the narrative geography without locking the entire story into a single exact path.`,
    context: `The route is stored as curated GeoJSON. It is intended to show movement pattern and approximate waypoints, not a GPS-precise reconstruction.`,
  };
}

function buildHistoricalLayerExplanation(layer, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = layer.name || "This layer";
  const period = layer.period || "the relevant historical period";
  return {
    why: `${name}${passagePhrase} helps situate the passage in ${period} and gives the reader a broad political-geographic frame without pretending the borders are exact.`,
    context: `The overlay is a curated GeoJSON study layer. Its boundaries are schematic and should be treated as a historical orientation aid, not a precise political reconstruction.`,
  };
}

function buildPoliticalContextExplanation(layer, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = layer.name || "This political context";
  const entityType = layer.entity_type || "political background";
  return {
    why: `${name}${passagePhrase} helps locate the passage within the larger ${entityType} that shaped the world of the text.`,
    context: `The layer is a curated schematic overlay. It highlights dominant political background, not exact borders or a single fixed date.`,
  };
}

function buildArchaeologyExplanation(marker, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = marker.name || "This archaeology item";
  const location = marker.location || marker.site_name || "its discovery context";
  return {
    why: `${name}${passagePhrase} helps anchor the passage in a concrete historical setting at ${location}, while still leaving room for uncertainty where the evidence is debated.`,
    context: `The item is stored as curated local archaeology data. It should be read as a historical witness with a specific genre and confidence level, not as a flattening of the text's meaning.`,
  };
}

function buildManuscriptExplanation(marker, passageContext) {
  const passageReference = formatReference(passageContext);
  const passagePhrase = passageReference ? ` in ${passageReference}` : "";
  const name = marker.name || "This manuscript";
  const discoveryLocation = marker.discovery_location || marker.current_location || "a known repository";
  return {
    why: `${name}${passagePhrase} helps anchor textual transmission in a concrete witness from ${discoveryLocation}, which is useful when comparing wording without treating any one manuscript as the final word.`,
    context: `The manuscript is curated as a textual witness separate from archaeology. Its value comes from the transmission history it represents, not from proving the passage by itself.`,
  };
}

function buildCautionNote(marker) {
  const confidence = String(marker.confidence || "unknown").toLowerCase();
  if (confidence === "strong") {
    return "This is a curated local identification with a clear map coordinate, but it still functions as historical background rather than proof of the passage's meaning.";
  }
  if (confidence === "possible") {
    return "This location is possible, not certain. Treat the marker as a cautious guide to a debated or approximate identification.";
  }
  if (confidence === "disputed") {
    return "This location is disputed in the literature. Use it only as a debated reference point, not as settled geography.";
  }
  return "The location data is incomplete or uncertain. The app shows it only as a cautious reference point.";
}

function buildManuscriptCautionNote(marker) {
  const confidence = String(marker.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated textual witness with a clear local record, but it should still be read as one witness in a larger transmission history.";
  }
  if (confidence === "possible") {
    return "This manuscript witness is approximate or partly uncertain. Treat the location and transmission notes cautiously.";
  }
  if (confidence === "disputed") {
    return "This manuscript witness is disputed or unevenly documented. Use it only as a cautious historical reference.";
  }
  return "The manuscript data is uncertain. Read it as a cautious textual witness only.";
}

function buildPoliticalContextCautionNote(layer) {
  const confidence = String(layer.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated political-context layer. It is meant to orient the reader, not to settle border debates or compress historical change into one snapshot.";
  }
  if (confidence === "possible") {
    return "This political-context layer is broad and approximate. Treat it as a study guide, not a precise boundary map.";
  }
  if (confidence === "disputed") {
    return "This political-context layer is disputed or heavily simplified. Use it only as a cautious background frame.";
  }
  return "The political-context data is uncertain. Read it as a cautious historical backdrop only.";
}

function buildRouteCautionNote(route) {
  const confidence = String(route.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This route is a curated approximation. It should be read as a study overlay, not as a claim that every segment is certain.";
  }
  if (confidence === "possible") {
    return "This route is approximate and partly debated. The overlay marks a plausible path, not a settled reconstruction.";
  }
  if (confidence === "disputed") {
    return "This route is disputed in the literature. Use it as a debated heuristic only.";
  }
  return "The route geometry is uncertain. The overlay should be read cautiously.";
}

function buildHistoricalLayerCautionNote(layer) {
  const confidence = String(layer.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a broad study overlay. It is useful for orientation, but the exact borders remained fluid and should not be read too literally.";
  }
  if (confidence === "possible") {
    return "This overlay is approximate and intentionally broad. It helps with study context, not precise boundary claims.";
  }
  if (confidence === "disputed") {
    return "This overlay is disputed or heavily debated. Use it only as a cautious historical guide.";
  }
  return "The boundary data is uncertain. Read the overlay as a cautious background layer only.";
}

function buildArchaeologyCautionNote(marker) {
  const confidence = String(marker.confidence || "unknown").toLowerCase();
  if (confidence === "strong" || confidence === "likely") {
    return "This is a curated archaeology witness with a clear local data source, but it still functions as historical background rather than direct proof of interpretation.";
  }
  if (confidence === "possible") {
    return "This archaeology item is approximate or debated. Treat it as a study aid, not a settled identification.";
  }
  if (confidence === "disputed") {
    return "This archaeology item is disputed. Use it only as a debated historical reference point.";
  }
  return "The archaeology data is uncertain. Read it cautiously and avoid overclaiming what it proves.";
}

function renderMapActionBar(kind, item) {
  const selectedLabel = prettyConfidence(item.confidence || "unknown");
  const primaryLabel =
    kind === "archaeology"
      ? "Ask about this item"
      : kind === "political_context"
        ? "Ask about this context"
        : "Ask about this location";
  return `
    <section class="map-detail-section map-action-section">
      <div class="map-action-buttons">
        <button type="button" class="secondary" data-map-action="ask_location">${escapeHtml(primaryLabel)}</button>
        <button type="button" class="secondary" data-map-action="save_map_study">Save map study</button>
        <button type="button" class="secondary" data-map-action="map_note">Add map note</button>
        <button type="button" class="secondary" data-map-action="compare_archaeology">Compare with archaeology</button>
        <button type="button" class="secondary" data-map-action="related_passages">View related passages</button>
        <button type="button" class="secondary" data-map-action="reset_map_view">Reset map view</button>
        ${
          kind === "layer" || kind === "archaeology" || kind === "political_context" || kind === "manuscript"
            ? ""
            : '<button type="button" class="secondary" data-map-action="view_historical_layer">View historical layer</button>'
        }
      </div>
      <p class="map-layer-note">Selected ${escapeHtml(kind)} confidence: ${escapeHtml(selectedLabel)}. These actions use the local curated map record for the current selection.</p>
    </section>
  `;
}

function buildSourceText(item) {
  const source = item?.source || {};
  const sourceName = source.label || item.source_name || "No source recorded";
  const sourceUrl = source.url || item.source_url || "";
  const license = source.license || item.license || "";
  const parts = [sourceName];
  if (sourceUrl) {
    parts.push(sourceUrl);
  }
  if (license) {
    parts.push(`License: ${license}`);
  }
  return parts.join(" · ");
}

function renderSourceAttribution(item, sourceText) {
  const source = item?.source || {};
  const sourceId = source.id || item.source_id || "";
  const sourceLink = sourceId ? `<a href="/sources/${encodeURIComponent(sourceId)}">Open source record</a>` : "No source record";
  const warning = sourceId ? "" : '<p class="map-source-warning">Missing source metadata in the local registry.</p>';
  const url = source.url || item.source_url || "";
  const license = source.license || item.license || "";
  return `
    <p class="map-attribution-source">${escapeHtml(sourceText)}</p>
    ${url ? `<p class="map-attribution-url">${escapeHtml(url)}</p>` : ""}
    ${license ? `<p class="map-attribution-license">${escapeHtml(license)}</p>` : ""}
    <p class="map-attribution-link">${sourceLink}</p>
    ${warning}
  `;
}

function prettyConfidence(value) {
  const normalized = String(value || "unknown").toLowerCase();
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatPeriodList(periods) {
  if (!Array.isArray(periods) || periods.length === 0) {
    return "Unknown period";
  }
  return periods.map((period) => prettyConfidence(period)).join(" · ");
}

function renderRelatedVerses(references) {
  if (!Array.isArray(references) || references.length === 0) {
    return "<p>No curated related verses are stored for this item.</p>";
  }
  const items = references
    .map((reference) => {
      const verseRange =
        Number(reference.verse_start) === Number(reference.verse_end)
          ? String(reference.verse_start)
          : `${reference.verse_start}-${reference.verse_end}`;
      return `
        <li class="map-related-item">
          <strong>${escapeHtml(reference.book)} ${escapeHtml(String(reference.chapter))}:${escapeHtml(verseRange)}</strong>
          <span>${escapeHtml(reference.relationship_type)}</span>
          <p>${escapeHtml(reference.notes || "")}</p>
          <button
            type="button"
            class="secondary map-shortcut"
            data-passage-shortcut
            data-book="${escapeHtml(reference.book || "")}"
            data-chapter="${escapeHtml(String(reference.chapter || ""))}"
            data-verse-start="${escapeHtml(String(reference.verse_start || ""))}"
            data-verse-end="${escapeHtml(String(reference.verse_end || ""))}"
            data-reference="${escapeHtml(reference.reference || `${reference.book || ""} ${reference.chapter || ""}:${verseRange}`)}"
          >Ask about this passage</button>
        </li>
      `;
    })
    .join("");
  return `<ul class="map-related-verses">${items}</ul>`;
}

function renderRelatedPassages(relatedPassages) {
  if (Array.isArray(relatedPassages)) {
    return renderRelatedVerses(relatedPassages);
  }
  const groups = Array.isArray(relatedPassages?.groups) ? relatedPassages.groups : [];
  if (!groups.length) {
    return "<p>No curated related passages are stored for this place.</p>";
  }
  const totalCount = Number(relatedPassages?.count || 0);
  const sections = groups
    .map((group) => {
      const testamentGroups = Array.isArray(group.testament_groups) ? group.testament_groups : [];
      const passageCount = Array.isArray(group.passages) ? group.passages.length : 0;
      const groupItems = testamentGroups.length
        ? testamentGroups
            .map((testamentGroup) => {
              const groupPassages = Array.isArray(testamentGroup.passages) ? testamentGroup.passages : [];
              return `
                <section class="map-related-group">
                  <h5>${escapeHtml(testamentGroup.label || "Location links")}</h5>
                  ${renderRelatedPassagesList(groupPassages)}
                </section>
              `;
            })
            .join("")
        : renderRelatedPassagesList(Array.isArray(group.passages) ? group.passages : []);
      return `
        <article class="map-related-passages-group">
          <h5>${escapeHtml(group.label || "Related passages")}</h5>
          <p class="map-related-group-summary">${escapeHtml(group.summary || "")}</p>
          ${groupItems}
          <p class="map-related-group-count">${escapeHtml(String(passageCount))} passage${passageCount === 1 ? "" : "s"}</p>
        </article>
      `;
    })
    .join("");
  return `
    <div class="map-related-passages">
      <p class="map-related-passages-total">${escapeHtml(String(totalCount))} curated passage${totalCount === 1 ? "" : "s"} linked to this place.</p>
      ${sections}
    </div>
  `;
}

function renderRelatedPassagesList(passages) {
  if (!Array.isArray(passages) || passages.length === 0) {
    return "<p class=\"empty\">No curated passages in this group.</p>";
  }
  const items = passages
    .map((passage) => {
      const source = passage.source || {};
      const sourceParts = [
        source.name ? escapeHtml(source.name) : null,
        source.label ? escapeHtml(source.label) : null,
      ].filter(Boolean);
      const sourceText = sourceParts.length ? sourceParts.join(" · ") : "Curated local data";
      return `
        <li class="map-related-item">
          <strong>${escapeHtml(passage.reference || "")}</strong>
          <span>${escapeHtml(passage.relationship_label || passage.relationship_type || "")}</span>
          <p>${escapeHtml(passage.notes || "")}</p>
          <p class="map-related-source">${sourceText}</p>
          <button
            type="button"
            class="secondary map-shortcut"
            data-passage-shortcut
            data-book="${escapeHtml(passage.book || "")}"
            data-chapter="${escapeHtml(String(passage.chapter || ""))}"
            data-verse-start="${escapeHtml(String(passage.verse_start || ""))}"
            data-verse-end="${escapeHtml(String(passage.verse_end || ""))}"
            data-reference="${escapeHtml(passage.reference || "")}"
          >Ask about this passage</button>
        </li>
      `;
    })
    .join("");
  return `<ul class="map-related-verses">${items}</ul>`;
}

function buildMapStudySummary(selection, context) {
  const reference = formatReference(context) || "the selected passage";
  if (!selection) {
    return `Map study for ${reference}.`;
  }
  const item = selection.item;
  const name = item.name || "Unnamed item";
  if (selection.kind === "route") {
    return `${name} in ${reference} with route confidence ${prettyConfidence(item.confidence)}.`;
  }
  if (selection.kind === "archaeology") {
    return `${name} in ${reference} as an archaeology witness with confidence ${prettyConfidence(item.confidence)}.`;
  }
  if (selection.kind === "manuscript") {
    return `${name} in ${reference} as a textual witness with confidence ${prettyConfidence(item.confidence)}.`;
  }
  if (selection.kind === "layer") {
    return `${name} in ${reference} as a ${item.period || "historical"} study layer.`;
  }
  if (selection.kind === "political_context") {
    return `${name} in ${reference} as a ${item.entity_type || "political"} context layer.`;
  }
  return `${name} in ${reference} with confidence ${prettyConfidence(item.confidence)}.`;
}

export {
  buildArchaeologyCautionNote,
  buildArchaeologyExplanation,
  buildCautionNote,
  buildHistoricalLayerCautionNote,
  buildHistoricalLayerExplanation,
  buildMapStudySummary,
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
  formatReference,
  formatStudyReference,
  prettyConfidence,
  renderMapActionBar,
  renderRelatedPassages,
  renderRelatedPassagesList,
  renderRelatedVerses,
  renderSourceAttribution,
};
