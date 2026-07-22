const JOURNEY_FILES = [
  "abraham.json",
  "exodus.json",
  "joshua-conquest.json",
  "david-fleeing-saul.json",
  "elijah-elisha.json",
  "jesus-galilean-ministry.json",
  "jesus-final-week.json",
  "paul-first-missionary.json",
  "paul-second-missionary.json",
  "paul-third-missionary.json",
  "paul-rome-voyage.json",
  "exile-return.json",
];
const JOURNEY_DATA_BASE_PATHS = ["/static/data/journeys"];

const MAP_LAYER_FILES = [
  "ancientCities.json",
  "biblicalRegions.json",
  "rivers.json",
  "mountains.json",
  "tradeRoutes.json",
  "kingdoms.json",
];
const MAP_LAYER_DATA_BASE_PATHS = ["/static/data/mapLayers"];

let journeyCatalogPromise = null;
let mapLayerCatalogPromise = null;

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function normalizeSearchValue(value) {
  return String(value ?? "").trim().toLowerCase();
}

function getJourneyFacetValues(journeys, field) {
  return Array.from(
    new Set(
      journeys
        .flatMap((journey) => (Array.isArray(journey[field]) ? journey[field] : journey[field] ? [journey[field]] : []))
        .map((value) => String(value).trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));
}

function journeyMatchesFilters(journey, filters = {}) {
  const search = normalizeSearchValue(filters.search);
  if (filters.testament && journey.testament !== filters.testament) {
    return false;
  }
  if (filters.category && journey.category !== filters.category) {
    return false;
  }
  if (filters.era && journey.era !== filters.era) {
    return false;
  }
  if (!search) {
    return true;
  }
  const haystack = [
    journey.title,
    journey.description,
    journey.category,
    journey.testament,
    journey.era,
    ...(journey.tags || []),
    ...(journey.bookRange || []),
  ]
    .map(normalizeSearchValue)
    .join(" ");
  return haystack.includes(search);
}

function getOrderedJourneyStops(journey) {
  return (journey?.stops || [])
    .map((stop, index) => ({
      stop,
      index,
      hasOrder: isFiniteNumber(stop.order),
    }))
    .sort((a, b) => {
      if (a.hasOrder && b.hasOrder) {
        return a.stop.order - b.stop.order || a.index - b.index;
      }
      if (a.hasOrder !== b.hasOrder) {
        return a.hasOrder ? -1 : 1;
      }
      return a.index - b.index;
    })
    .map((entry) => entry.stop);
}

function validateJourney(journey, sourceLabel = "<unknown journey>") {
  const errors = [];
  if (!isPlainObject(journey)) {
    errors.push("journey must be an object");
  } else {
    if (typeof journey.id !== "string" || !journey.id.trim()) {
      errors.push("missing id");
    }
    if (typeof journey.title !== "string" || !journey.title.trim()) {
      errors.push("missing title");
    }
    if (!Array.isArray(journey.stops) || journey.stops.length === 0) {
      errors.push("stops must be a non-empty array");
    }
  }
  if (errors.length > 0) {
    console.warn(`[BHF Journey] Skipping invalid journey ${sourceLabel}: ${errors.join(", ")}`);
    return null;
  }

  const stopIds = new Set();
  for (const stop of journey.stops) {
    if (!isPlainObject(stop)) {
      errors.push(`stop entries must be objects (${sourceLabel})`);
      continue;
    }
    if (typeof stop.id !== "string" || !stop.id.trim()) {
      errors.push(`stop missing id (${sourceLabel})`);
    } else if (stopIds.has(stop.id)) {
      errors.push(`duplicate stop id "${stop.id}" (${sourceLabel})`);
    } else {
      stopIds.add(stop.id);
    }
    if (typeof stop.name !== "string" || !stop.name.trim()) {
      errors.push(`stop ${stop.id || "<unknown>"} missing name (${sourceLabel})`);
    }
    if (!isFiniteNumber(stop.lat) || !isFiniteNumber(stop.lng)) {
      errors.push(`stop ${stop.id || "<unknown>"} missing numeric lat/lng (${sourceLabel})`);
    }
    if (Object.prototype.hasOwnProperty.call(stop, "order") && !isFiniteNumber(stop.order)) {
      errors.push(`stop ${stop.id || "<unknown>"} has non-numeric order (${sourceLabel})`);
    }
  }

  const segmentIds = new Set();
  for (const segment of Array.isArray(journey.segments) ? journey.segments : []) {
    if (!isPlainObject(segment)) {
      errors.push(`segment entries must be objects (${sourceLabel})`);
      continue;
    }
    if (typeof segment.id !== "string" || !segment.id.trim()) {
      errors.push(`segment missing id (${sourceLabel})`);
    } else if (segmentIds.has(segment.id)) {
      errors.push(`duplicate segment id "${segment.id}" (${sourceLabel})`);
    } else {
      segmentIds.add(segment.id);
    }
    if (!stopIds.has(segment.from) || !stopIds.has(segment.to)) {
      errors.push(`segment "${segment.id || "<unknown>"}" must reference valid stop ids (${sourceLabel})`);
    }
  }

  if (errors.length > 0) {
    console.warn(`[BHF Journey] Skipping invalid journey ${sourceLabel}: ${errors.join(", ")}`);
    return null;
  }
  return {
    ...journey,
    segments: Array.isArray(journey.segments) ? journey.segments : [],
    primaryPassages: Array.isArray(journey.primaryPassages) ? journey.primaryPassages : [],
    tags: Array.isArray(journey.tags) ? journey.tags : [],
    bookRange: Array.isArray(journey.bookRange) ? journey.bookRange : [],
  };
}

function validateMapLayer(layer, sourceLabel = "<unknown layer>") {
  if (!isPlainObject(layer) || typeof layer.id !== "string" || !layer.id.trim()) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: missing id`);
    return null;
  }
  if (typeof layer.title !== "string" || !layer.title.trim()) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: missing title`);
    return null;
  }
  if (!["points", "lines", "polygons"].includes(layer.type)) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: type must be points, lines, or polygons`);
    return null;
  }
  if (!Array.isArray(layer.features) || layer.features.length === 0) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: features must be a non-empty array`);
    return null;
  }

  const featureIds = new Set();
  const features = [];
  for (const feature of layer.features) {
    if (!isPlainObject(feature) || typeof feature.id !== "string" || !feature.id.trim()) {
      continue;
    }
    if (featureIds.has(feature.id) || typeof feature.name !== "string" || !feature.name.trim()) {
      continue;
    }
    if (layer.type === "points") {
      if (!isFiniteNumber(feature.lat) || !isFiniteNumber(feature.lng)) {
        continue;
      }
    } else if (
      !Array.isArray(feature.points) ||
      feature.points.length === 0 ||
      feature.points.some((point) => !Array.isArray(point) || point.length < 2 || !isFiniteNumber(point[0]) || !isFiniteNumber(point[1]))
    ) {
      continue;
    }
    featureIds.add(feature.id);
    features.push({
      ...feature,
      periods: Array.isArray(feature.periods) ? feature.periods : [],
      passages: Array.isArray(feature.passages) ? feature.passages : [],
    });
  }

  if (features.length === 0) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: no valid features remain`);
    return null;
  }
  return {
    ...layer,
    defaultVisible: Boolean(layer.defaultVisible),
    features,
  };
}

async function fetchJsonFromBases(basePaths, fileName, version) {
  const failures = [];
  for (const basePath of basePaths) {
    const url = `${basePath}/${fileName}?v=${version}`;
    try {
      const response = await fetch(url);
      if (!response.ok) {
        failures.push(`${url}: ${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      failures.push(`${url}: ${error.message || "request failed"}`);
    }
  }
  throw new Error(`Could not load ${fileName}. Tried ${failures.join("; ")}`);
}

async function loadJourneyCatalog() {
  if (!journeyCatalogPromise) {
    journeyCatalogPromise = Promise.allSettled(
      JOURNEY_FILES.map((fileName) => fetchJsonFromBases(JOURNEY_DATA_BASE_PATHS, fileName, "20260722a"))
    ).then((records) => {
      const journeys = [];
      for (const [index, record] of records.entries()) {
        const fileName = JOURNEY_FILES[index];
        if (record.status !== "fulfilled") {
          console.warn(`[BHF Journey] Skipping journey file ${fileName}: ${record.reason?.message || "unknown error"}`);
          continue;
        }
        const journey = validateJourney(record.value, fileName);
        if (journey) {
          journeys.push(journey);
        }
      }
      return {
        journeys,
        defaultJourneyId: "",
        facets: {
          categories: getJourneyFacetValues(journeys, "category"),
          eras: getJourneyFacetValues(journeys, "era"),
          testaments: getJourneyFacetValues(journeys, "testament"),
          tags: getJourneyFacetValues(journeys, "tags"),
        },
      };
    });
  }
  return journeyCatalogPromise;
}

async function loadMapLayerCatalog() {
  if (!mapLayerCatalogPromise) {
    mapLayerCatalogPromise = Promise.allSettled(
      MAP_LAYER_FILES.map((fileName) => fetchJsonFromBases(MAP_LAYER_DATA_BASE_PATHS, fileName, "20260722a"))
    ).then((records) => {
      const layers = [];
      for (const [index, record] of records.entries()) {
        const fileName = MAP_LAYER_FILES[index];
        if (record.status !== "fulfilled") {
          console.warn(`[BHF Layer] Skipping layer file ${fileName}: ${record.reason?.message || "unknown error"}`);
          continue;
        }
        const layer = validateMapLayer(record.value, fileName);
        if (layer) {
          layers.push(layer);
        }
      }
      return {
        layers,
        mapLayersById: Object.fromEntries(layers.map((layer) => [layer.id, layer])),
        defaultVisibleLayerIds: layers.filter((layer) => layer.defaultVisible).map((layer) => layer.id),
      };
    });
  }
  return mapLayerCatalogPromise;
}

export {
  getOrderedJourneyStops,
  journeyMatchesFilters,
  loadJourneyCatalog,
  loadMapLayerCatalog,
};
