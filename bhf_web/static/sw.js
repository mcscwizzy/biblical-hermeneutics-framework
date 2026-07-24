const CACHE_VERSION = "v11";
const SHELL_CACHE = `bhf-shell-${CACHE_VERSION}`;
const STATIC_CACHE = `bhf-static-${CACHE_VERSION}`;
const API_CACHE = `bhf-api-${CACHE_VERSION}`;
const ALL_CACHES = [SHELL_CACHE, STATIC_CACHE, API_CACHE];

const SHELL_ASSETS = [
  "/",
  "/offline",
  "/manifest.webmanifest",
  "/api/offline/manifest",
];

const STATIC_ASSETS = [
  "/static/style.css",
  "/static/styles/layout.css",
  "/static/styles/maps.css",
  "/static/styles/utilities.css",
  "/static/styles/workspace.css",
  "/static/api/http.js",
  "/static/offline/db.js",
  "/static/htmx-lite.js",
  "/static/htmx-status.js",
  "/static/htmx-study-panels.js",
  "/static/htmx-search.js",
  "/static/pwa.js",
  "/static/vendor/leaflet/leaflet.css",
  "/static/vendor/leaflet/leaflet.js",
  "/static/vendor/leaflet/leaflet.js.map",
  "/static/vendor/leaflet/images/layers-2x.png",
  "/static/vendor/leaflet/images/layers.png",
  "/static/vendor/leaflet/images/marker-icon-2x.png",
  "/static/vendor/leaflet/images/marker-icon.png",
  "/static/vendor/leaflet/images/marker-shadow.png",
  "/static/maps/BibleMap.js",
  "/static/maps/JourneyMapData.js",
  "/static/maps/MapMarkerPopup.js",
  "/static/maps/MapPanel.js",
  "/static/maps/MapPanelContent.js",
  "/static/maps/MapPanelSearch.js",
  "/static/maps/MapPanelStateHelpers.js",
  "/static/maps/MapPanelText.js",
  "/static/maps/MapPopups.js",
  "/static/maps/MapStyles.js",
  "/static/maps/mapService.js",
  "/static/icons/icon.svg",
  "/static/icons/maskable.svg",
  "/static/icons/apple-touch-icon.svg",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/maskable.png",
  "/static/data/archaeology/archaeologySites.json",
  "/static/data/archaeology/artifacts.json",
  "/static/data/archaeology/excavationReports.json",
  "/static/data/archaeology/museums.json",
  "/static/data/journeys/abraham.json",
  "/static/data/journeys/david-fleeing-saul.json",
  "/static/data/journeys/elijah-elisha.json",
  "/static/data/journeys/exile-return.json",
  "/static/data/journeys/exodus.json",
  "/static/data/journeys/jesus-final-week.json",
  "/static/data/journeys/jesus-galilean-ministry.json",
  "/static/data/journeys/joshua-conquest.json",
  "/static/data/journeys/paul-first-missionary.json",
  "/static/data/journeys/paul-rome-voyage.json",
  "/static/data/journeys/paul-second-missionary.json",
  "/static/data/journeys/paul-third-missionary.json",
  "/static/data/mapLayers/ancientCities.json",
  "/static/data/mapLayers/biblicalRegions.json",
  "/static/data/mapLayers/kingdoms.json",
  "/static/data/mapLayers/mountains.json",
  "/static/data/mapLayers/rivers.json",
  "/static/data/mapLayers/tradeRoutes.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(SHELL_CACHE).then((cache) => cacheAssets(cache, SHELL_ASSETS)),
      caches.open(STATIC_CACHE).then((cache) => cacheAssets(cache, STATIC_ASSETS)),
    ]).catch(() => undefined)
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (!ALL_CACHES.includes(key)) {
            return caches.delete(key);
          }
          return undefined;
        })
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  if (requestUrl.pathname.startsWith("/api/")) {
    if (isCacheableApiRequest(requestUrl)) {
      event.respondWith(networkFirstApi(event.request));
    }
    return;
  }

  if (requestUrl.pathname === "/sw.js") {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(event.request));
    return;
  }

  event.respondWith(networkFirstAsset(event.request));
});

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(SHELL_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    return caches.match("/offline");
  }
}

async function networkFirstAsset(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    return caches.match("/offline");
  }
}

async function networkFirstApi(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (_error) {
    const cached = await caches.match(request);
    if (cached) {
      return withOfflineHeaders(cached);
    }
    return jsonResponse(
      {
        error: "This data is not available offline yet.",
        offline: true,
        cache_status: "miss",
      },
      503
    );
  }
}

function isCacheableApiRequest(url) {
  if (isAiOnlyApiRequest(url)) {
    return false;
  }
  return [
    "/api/offline/manifest",
    "/api/offline/packs/",
    "/api/translations",
    "/api/translations/installed",
    "/api/translations/catalog",
    "/api/settings/reader",
    "/api/bible/books",
    "/api/bible/search",
    "/api/bible/",
    "/api/notes/",
    "/api/highlights/",
    "/api/saved-studies",
    "/api/canonical/search",
    "/api/canonical/objects/",
    "/api/maps/",
    "/api/map-studies",
    "/api/sources",
  ].some((path) => url.pathname === path || url.pathname.startsWith(path));
}

function isAiOnlyApiRequest(url) {
  return [
    "/api/llm/health",
    "/api/bible/search/fallback",
    "/api/debug/ckl-search",
    "/ask",
  ].some((path) => url.pathname === path || url.pathname.startsWith(path));
}

async function cacheAssets(cache, assets) {
  await Promise.all(
    assets.map(async (asset) => {
      try {
        await cache.add(asset);
      } catch (_error) {
        // Keep the service worker installable if one optional asset is missing.
      }
    })
  );
}

async function withOfflineHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set("X-BHF-Offline", "true");
  return new Response(await response.blob(), {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function jsonResponse(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-BHF-Offline": "true",
    },
  });
}
