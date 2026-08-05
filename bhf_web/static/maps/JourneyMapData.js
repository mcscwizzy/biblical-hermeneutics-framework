// Compatibility loader for the curated journey/map-layer data used by older
// map-panel integrations. The current panel can continue to use the API.
const JOURNEY_DATA_BASE_PATHS = ["/static/data/journeys", "/static/data/mapLayers"];
const MAP_LAYER_FILES = ["ancientCities.json", "biblicalRegions.json", "kingdoms.json", "mountains.json", "rivers.json", "tradeRoutes.json"];

async function loadJourneyCatalog() { return []; }
async function loadMapLayerCatalog() { return []; }
function journeyMatchesFilters() { return true; }
async function loadSupplementalMapData() { return { journeys: [], mapLayers: [] }; }

export { JOURNEY_DATA_BASE_PATHS, MAP_LAYER_FILES, loadJourneyCatalog, loadMapLayerCatalog, journeyMatchesFilters, loadSupplementalMapData };
