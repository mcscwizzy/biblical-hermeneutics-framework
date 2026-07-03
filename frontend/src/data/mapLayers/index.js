import { validateMapLayer } from "./validateMapLayer.js";

export const MAP_LAYER_FILES = [
  "ancientCities.json",
  "biblicalRegions.json",
  "rivers.json",
  "mountains.json",
  "tradeRoutes.json",
  "kingdoms.json",
];

let mapLayerCatalogPromise = null;

export let mapLayers = [];
export let mapLayersById = {};

async function readMapLayerFile(fileName) {
  const url = new URL(`./${fileName}`, import.meta.url);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load map layer data from ${fileName}.`);
  }
  return response.json();
}

async function loadMapLayerRecords() {
  const records = await Promise.allSettled(MAP_LAYER_FILES.map((fileName) => readMapLayerFile(fileName)));
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

  mapLayers = layers;
  mapLayersById = Object.fromEntries(layers.map((layer) => [layer.id, layer]));
  return layers;
}

export async function loadMapLayers() {
  if (!mapLayerCatalogPromise) {
    mapLayerCatalogPromise = loadMapLayerRecords().catch((error) => {
      mapLayerCatalogPromise = null;
      throw error;
    });
  }
  return mapLayerCatalogPromise;
}

export async function loadMapLayerCatalog() {
  const layers = await loadMapLayers();
  return {
    mapLayers: layers,
    mapLayersById,
    defaultVisibleLayerIds: layers.filter((layer) => layer.defaultVisible).map((layer) => layer.id),
    pointLayers: layers.filter((layer) => layer.type === "points"),
    lineLayers: layers.filter((layer) => layer.type === "lines"),
    polygonLayers: layers.filter((layer) => layer.type === "polygons"),
  };
}
