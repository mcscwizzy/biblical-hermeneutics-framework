const CACHE_VERSION = "v50";
const SHELL_CACHE = `bhf-shell-${CACHE_VERSION}`;
const STATIC_CACHE = `bhf-static-${CACHE_VERSION}`;
const API_CACHE = `bhf-api-${CACHE_VERSION}`;
const ALL_CACHES = [SHELL_CACHE, STATIC_CACHE, API_CACHE];
const MAX_MAP_API_CACHE_BYTES = 512 * 1024;
const MAX_MAP_API_CACHE_ENTRIES = 32;
const MAX_MAP_API_CACHE_TOTAL_BYTES = 8 * 1024 * 1024;

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
  "/static/styles/companion.css",
  "/static/styles/discoveries.css",
  "/static/api/http.js",
  "/static/api/backend-routing.js",
  "/static/offline/db.js",
  "/static/study-vault.js",
  "/static/htmx-lite.js",
  "/static/reader-selection.js",
  "/static/study-recommendations.js",
  "/static/companion-context.js",
  "/static/companion-context-controller.js",
  "/static/saved-passage-state.js",
  "/static/companion-history.js",
  "/static/companion-viewport.js",
  "/static/companion-sheet.js",
  "/static/narrative-explorer.js",
  "/static/resource-router.js",
  "/static/companion-discoveries.js",
  "/static/companion-locations.js",
  "/static/study-companion.js",
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
  "/static/maps/MapFocusAcknowledgment.js",
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

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
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
  const requestUrl = new URL(event.request.url);
  if (isLiveBackendJobRequest(requestUrl)) {
    event.respondWith(fetch(event.request));
    return;
  }

  if (event.request.method !== "GET") {
    return;
  }

  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  // OAuth returns a temporary authorization code in the callback URL. Never
  // let a service-worker cache or offline fallback retain that navigation.
  if (isAuthCallbackUrl(requestUrl)) {
    event.respondWith(fetch(event.request));
    return;
  }

  if (requestUrl.pathname.startsWith("/api/")) {
    if (isCacheableApiRequest(requestUrl)) {
      const preferNetwork = isRefreshRequest(event.request)
        || requestUrl.pathname === "/api/study/companion-context"
        || requestUrl.pathname === "/api/study/companion-locations"
        || requestUrl.pathname.startsWith("/api/maps/");
      let cacheWritePromise = Promise.resolve();
      const trackCacheWrite = (promise) => {
        cacheWritePromise = Promise.resolve(promise).catch(() => undefined);
      };
      const responsePromise = preferNetwork
        ? networkFirstApi(event.request, trackCacheWrite)
        : cacheFirstApi(event.request, trackCacheWrite);
      // Keep the worker alive until a successful network response has been
      // copied into Cache Storage. Returning the response alone can let Firefox
      // terminate the worker while the cloned body is still being consumed.
      event.waitUntil(responsePromise.then(() => cacheWritePromise, () => cacheWritePromise));
      event.respondWith(responsePromise);
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

async function networkFirstApi(request, trackCacheWrite = () => {}) {
  try {
    const response = await fetch(request);
    if (response.status === 200) {
      const url = new URL(request.url);
      const isMapResponse = url.pathname.startsWith("/api/maps/");
      const isMapsOfflinePack = url.pathname === "/api/offline/packs/maps";
      if (
        (isMapResponse || isMapsOfflinePack)
        && !isBoundedJsonMapResponse(response)
      ) {
        return response;
      }
      // The page can start consuming the response as soon as it is returned.
      // Tee eligible map bodies before awaiting Cache Storage so Firefox never
      // races page consumption against the cache clone.
      const responseForCache = (isMapResponse || isMapsOfflinePack)
        ? response.clone()
        : response;
      const cache = await caches.open(API_CACHE);
      trackCacheWrite(cacheApiResponse(cache, request, responseForCache));
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

async function cacheApiResponse(cache, request, response) {
  const url = new URL(request.url);
  const isMapResponse = url.pathname.startsWith("/api/maps/");
  const isMapsOfflinePack = url.pathname === "/api/offline/packs/maps";
  if ((isMapResponse || isMapsOfflinePack) && !isBoundedJsonMapResponse(response)) {
    return;
  }

  let responseToCache = response;
  if (isMapResponse) {
    const existing = await cache.match(request);
    const offlinePack = existing?.headers.get("X-BHF-Offline-Pack");
    if (offlinePack) {
      const headers = new Headers(response.headers);
      headers.set("X-BHF-Offline-Pack", offlinePack);
      responseToCache = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    }
  } else if (!isMapsOfflinePack) {
    // Non-map API responses still share their body with the page response.
    responseToCache = response.clone();
  }
  await cache.put(request, responseToCache);
  if (!isMapResponse) {
    return;
  }

  const mapRequests = (await cache.keys()).filter((cachedRequest) => {
    try {
      return new URL(cachedRequest.url).pathname.startsWith("/api/maps/");
    } catch {
      return false;
    }
  });
  const cachedMapEntries = [];
  let totalBytes = 0;
  for (const cachedRequest of mapRequests) {
    const cachedResponse = await cache.match(cachedRequest);
    const rawLength = cachedResponse?.headers.get("Content-Length") || "";
    const byteLength = /^\d+$/.test(rawLength)
      ? Number(rawLength)
      : MAX_MAP_API_CACHE_TOTAL_BYTES + 1;
    cachedMapEntries.push({
      request: cachedRequest,
      byteLength,
      offlinePack: Boolean(cachedResponse?.headers.get("X-BHF-Offline-Pack")),
    });
    totalBytes += byteLength;
  }
  while (
    cachedMapEntries.length > MAX_MAP_API_CACHE_ENTRIES
    || totalBytes > MAX_MAP_API_CACHE_TOTAL_BYTES
  ) {
    if (!cachedMapEntries.length) break;
    const dynamicIndex = cachedMapEntries.findIndex((entry) => !entry.offlinePack);
    const evictIndex = dynamicIndex >= 0 ? dynamicIndex : 0;
    const [evicted] = cachedMapEntries.splice(evictIndex, 1);
    await cache.delete(evicted.request);
    totalBytes -= evicted.byteLength;
  }
}

function isBoundedJsonMapResponse(response) {
  if (response.status !== 200) {
    return false;
  }
  const contentType = response.headers.get("Content-Type") || "";
  const rawLength = response.headers.get("Content-Length");
  const contentEncoding = (response.headers.get("Content-Encoding") || "identity").toLowerCase();
  if (!contentType.toLowerCase().includes("application/json") || contentEncoding !== "identity") {
    return false;
  }
  if (!rawLength || !/^\d+$/.test(rawLength)) {
    return false;
  }
  const byteLength = Number(rawLength);
  return Number.isSafeInteger(byteLength) && byteLength <= MAX_MAP_API_CACHE_BYTES;
}

async function cacheFirstApi(request, trackCacheWrite = () => {}) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  return networkFirstApi(request, trackCacheWrite);
}

function isRefreshRequest(request) {
  return request.headers.get("X-BHF-Refresh") === "true";
}

function isAuthCallbackUrl(url) {
  return url.pathname === "/oauth/callback"
    || url.searchParams.has("code")
    || url.searchParams.has("state")
    || url.searchParams.has("error")
    || url.searchParams.has("error_description");
}

function isLiveBackendJobRequest(url) {
  return false;
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
    "/api/canonical/search",
    "/api/canonical/entities-for-passage",
    "/api/study/companion-context",
    "/api/study/companion-locations",
    "/api/canonical/objects/",
    "/api/maps/",
    "/api/map-studies",
    "/api/sources",
    "/api/commentary/",
  ].some((path) => url.pathname === path || url.pathname.startsWith(path));
}

function isAiOnlyApiRequest(url) {
  return url.pathname === "/api/debug/ckl-search";
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
