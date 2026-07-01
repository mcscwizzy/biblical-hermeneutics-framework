function normalizeHistoricalPeriod(value, options = []) {
  const normalized = String(value || "all").trim();
  if (!normalized || normalized.toLowerCase() === "all") {
    return "all";
  }
  const aliases = {
    "New Testament / Roman period": "NT / Roman period",
    "new testament / roman period": "NT / Roman period",
    "Broad / uncertain": "Broad / uncertain period",
    "broad / uncertain period": "Broad / uncertain period",
    "uncertain / broad period": "Broad / uncertain period",
  };
  const canonical = aliases[normalized] || normalized;
  return options.some((option) => option.value === canonical) ? canonical : "all";
}

function syncRouteToggle(mapController, routeToggle) {
  if (!routeToggle || !mapController) {
    return;
  }
  routeToggle.checked = mapController.getRouteVisibility();
}

function syncArchaeologyToggle(mapController, archaeologyToggle) {
  if (!archaeologyToggle || !mapController) {
    return;
  }
  archaeologyToggle.checked = mapController.getArchaeologyVisibility();
}

function syncManuscriptToggle(mapController, manuscriptToggle) {
  if (!manuscriptToggle || !mapController) {
    return;
  }
  manuscriptToggle.checked = mapController.getManuscriptVisibility();
}

function syncHistoricalLayerToggles(details, visibleHistoricalLayerIds) {
  if (!details) {
    return;
  }
  const toggles = details.querySelectorAll("[data-historical-layer-toggle]");
  toggles.forEach((toggle) => {
    const layerId = String(toggle.getAttribute("data-layer-id") || "");
    if (!layerId) {
      return;
    }
    toggle.checked = visibleHistoricalLayerIds.has(layerId);
  });
}

function syncPoliticalContextLayerToggles(details, visiblePoliticalContextLayerIds) {
  if (!details) {
    return;
  }
  const toggles = details.querySelectorAll("[data-political-context-toggle]");
  toggles.forEach((toggle) => {
    const layerId = String(toggle.getAttribute("data-layer-id") || "");
    if (!layerId) {
      return;
    }
    toggle.checked = visiblePoliticalContextLayerIds.has(layerId);
  });
}

function getCurrentMapSelection(state) {
  if (state.selectedMarker) {
    return {
      kind: "place",
      item: state.selectedMarker,
    };
  }
  if (state.selectedArchaeology) {
    return {
      kind: "archaeology",
      item: state.selectedArchaeology,
    };
  }
  if (state.selectedManuscript) {
    return {
      kind: "manuscript",
      item: state.selectedManuscript,
    };
  }
  if (state.selectedRoute) {
    return {
      kind: "route",
      item: state.selectedRoute,
    };
  }
  if (state.selectedHistoricalLayer) {
    return {
      kind: "layer",
      item: state.selectedHistoricalLayer,
    };
  }
  if (state.selectedPoliticalContext) {
    return {
      kind: "political_context",
      item: state.selectedPoliticalContext,
    };
  }
  return null;
}

function buildCurrentMapStudyPayload(state) {
  const context = state.lastPassageContext || {};
  const selection = getCurrentMapSelection(state);
  const mapViewState = state.mapController?.getViewState ? state.mapController.getViewState() : {};
  const selectedLayers = [
    ...(state.mapController?.getHistoricalLayerIds ? state.mapController.getHistoricalLayerIds() : Array.from(state.visibleHistoricalLayerIds || [])),
    ...(state.mapController?.getPoliticalContextLayerIds
      ? state.mapController.getPoliticalContextLayerIds()
      : Array.from(state.visiblePoliticalContextLayerIds || [])),
  ];

  return {
    book: context.book,
    chapter: context.chapter,
    start_verse: context.verseStart || context.startVerse,
    end_verse: context.verseEnd || context.endVerse || context.verseStart || context.startVerse,
    passage_reference: state.formatReference ? state.formatReference(context) : "",
    selected_place_id: selection?.kind === "place" ? selection.item.id : "",
    selected_archaeology_id: selection?.kind === "archaeology" ? selection.item.id : "",
    selected_manuscript_id: selection?.kind === "manuscript" ? selection.item.id : "",
    selected_route_id: selection?.kind === "route" ? selection.item.id : "",
    selected_layer_id:
      selection?.kind === "layer" || selection?.kind === "political_context" ? selection.item.id : "",
    selected_place_name: selection?.kind === "place" ? selection.item.name : "",
    selected_archaeology_name: selection?.kind === "archaeology" ? selection.item.name : "",
    selected_manuscript_name: selection?.kind === "manuscript" ? selection.item.name : "",
    selected_route_name: selection?.kind === "route" ? selection.item.name : "",
    selected_layer_name:
      selection?.kind === "layer" || selection?.kind === "political_context" ? selection.item.name : "",
    modern_location: selection?.kind === "place" ? selection.item.modern_location : "",
    ancient_region: selection?.kind === "place" ? selection.item.ancient_region : "",
    archaeology_location: selection?.kind === "archaeology" ? selection.item.location : "",
    confidence: selection?.item?.confidence || "",
    description: selection?.item?.description || "",
    period:
      selection?.kind === "layer" || selection?.kind === "political_context"
        ? selection.item.period
        : selection?.kind === "route"
          ? selection.item.period
          : selection?.kind === "archaeology"
            ? selection.item.period
            : selection?.kind === "manuscript"
              ? selection.item.period
            : "",
    selected_layers: Array.from(new Set(selectedLayers)),
    map_view_state: {
      ...mapViewState,
      historicalPeriod: state.historicalPeriod,
    },
    generated_summary: state.buildMapStudySummary ? state.buildMapStudySummary(selection, context) : "",
    user_notes: "",
  };
}

export {
  buildCurrentMapStudyPayload,
  getCurrentMapSelection,
  normalizeHistoricalPeriod,
  syncArchaeologyToggle,
  syncHistoricalLayerToggles,
  syncManuscriptToggle,
  syncPoliticalContextLayerToggles,
  syncRouteToggle,
};
