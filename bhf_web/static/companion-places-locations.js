/* Focused, passage-scoped geography view for the Study Companion. */
(function (root, factory) {
  "use strict";

  const geography = factory();
  if (typeof module === "object" && module.exports) module.exports = geography;
  root.BHFCompanionPlacesLocations = geography;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function render(context = {}, options = {}) {
    const document = options.document || globalThis.document;
    if (!document?.createElement) return null;
    const view = document.createElement("div");
    view.className = "companion-places-locations";
    view.dataset.placesLocationsView = "";

    const heading = document.createElement("h3");
    heading.className = "companion-places-locations-title";
    heading.textContent = "Places & Locations";
    const reference = document.createElement("p");
    reference.className = "companion-places-locations-reference";
    reference.textContent = context.reference || options.selection?.reference || "Selected passage";
    view.append(heading, reference);

    const state = geographyState(context);
    const status = document.createElement("p");
    status.className = "companion-geography-status";
    status.dataset.geographyStatus = "";
    status.dataset.geographyState = state.kind;
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.textContent = state.message;
    view.append(status);

    const locations = buildSection(document, "locations", "Locations");
    locations.section.classList.add("companion-locations");
    locations.section.dataset.companionLocationsSection = "";
    const locationList = document.createElement("ol");
    locationList.className = "companion-location-list";
    locationList.id = "companion-locations-list";
    locationList.dataset.companionLocationsList = "";
    const locationStatus = document.createElement("p");
    locationStatus.className = "companion-location-status";
    locationStatus.dataset.companionLocationsStatus = "";
    locationStatus.setAttribute("role", "status");
    locationStatus.setAttribute("aria-live", "polite");
    locationStatus.setAttribute("tabindex", "-1");
    const more = document.createElement("button");
    more.type = "button";
    more.className = "secondary companion-locations-more";
    more.dataset.companionLocationsMore = "";
    more.hidden = true;
    more.textContent = "View all locations";
    locations.section.append(locationList, locationStatus, more);
    view.append(locations.section);
    let updateCanonicalPlaces = () => {};
    if (options.locationRenderer?.render) {
      options.locationRenderer.render(view, context.locations, {
        ...options.locationOptions,
        selection: options.selection,
        offline: context.offline === true || options.locationOptions?.offline === true,
        showEmpty: true,
        onChange: (locations) => {
          updateCanonicalPlaces(locations);
          options.locationOptions?.onChange?.(locations);
        },
      });
    }
    if ((!Array.isArray(context.locations?.items) || context.locations.items.length === 0)
      && locationList.children.length === 0) {
      locations.section.hidden = false;
      const empty = document.createElement("p");
      empty.className = "companion-geography-empty";
      empty.dataset.geographyEmpty = "";
      empty.textContent = `No source-grounded locations for ${context.reference || "this passage"}.`;
      locationList.append(empty);
    }

    const canonical = buildSection(document, "biblical-places", "Biblical Places");
    const placeList = document.createElement("ul");
    placeList.className = "companion-biblical-place-list";
    placeList.dataset.biblicalPlaceList = "";
    const locationCklIds = new Set((Array.isArray(context.locations?.items) ? context.locations.items : [])
      .filter((item) => item?.origin === "ckl" && typeof item.id === "string")
      .map((item) => item.id));
    const places = canonicalPlaces(context.entities?.places)
      .filter((place) => !locationCklIds.has(place.id));
    places.forEach((place) => placeList.append(canonicalPlace(document, place)));
    const canonicalEmpty = document.createElement("p");
    canonicalEmpty.className = "companion-geography-empty";
    canonicalEmpty.dataset.geographyEmpty = "";
    canonicalEmpty.textContent = "No CKL place records are available for this passage.";
    canonicalEmpty.hidden = places.length > 0;
    canonical.section.append(placeList, canonicalEmpty);
    updateCanonicalPlaces = (locations) => {
      const ids = new Set((Array.isArray(locations?.items) ? locations.items : [])
        .filter((item) => item?.origin === "ckl" && typeof item.id === "string")
        .map((item) => item.id));
      placeList.replaceChildren(...Array.from(placeList.children)
        .filter((place) => !ids.has(place.dataset.canonicalId)));
      canonicalEmpty.hidden = placeList.children.length > 0;
    };
    view.append(canonical.section);

    const walk = buildSection(document, "walk-the-land", "Walk the Land");
    walk.section.dataset.companionLandSection = "";
    const walkList = document.createElement("div");
    walkList.className = "companion-discovery-list";
    walkList.dataset.companionLand = "";
    walk.section.append(walkList);
    view.append(walk.section);
    const walkCards = (Array.isArray(context.presentation_packet?.cards) ? context.presentation_packet.cards : [])
      .filter((card) => card?.type === "walk_the_land");
    options.renderWalkTheLand?.(view, context);
    if (!walkCards.length && typeof options.renderWalkTheLand !== "function") {
      walk.section.hidden = false;
      const empty = document.createElement("p");
      empty.className = "companion-geography-empty";
      empty.dataset.geographyEmpty = "";
      empty.textContent = "No source-grounded journeys are available for this passage.";
      walk.section.append(empty);
    }
    return view;
  }

  function buildSection(document, id, title) {
    const section = document.createElement("section");
    section.className = `companion-section companion-geography-section companion-geography-${id}`;
    section.dataset.geographySection = id;
    const heading = document.createElement("h4");
    heading.textContent = title;
    section.append(heading);
    return {section, heading};
  }

  function canonicalPlaces(places) {
    const identities = new Set();
    return (Array.isArray(places) ? places : []).filter((place) => {
      if (!place
        || typeof place.id !== "string"
        || place.type !== "place"
        || place.relationship !== "direct Scripture anchor"
        || identities.has(place.id)) return false;
      identities.add(place.id);
      return true;
    });
  }

  function canonicalPlace(document, place) {
    const item = document.createElement("li");
    item.className = "companion-biblical-place";
    item.dataset.canonicalId = place.id;
    const title = document.createElement("strong");
    title.textContent = place.title || place.name || place.id;
    const action = document.createElement("button");
    action.type = "button";
    action.className = "secondary companion-location-action";
    action.dataset.companionEntity = place.id;
    action.textContent = `Open ${place.title || place.name || place.id} in CKL`;
    action.setAttribute("aria-label", `Open ${place.title || place.name || place.id} in Canonical Knowledge Library`);
    item.append(title, action);
    return item;
  }

  function geographyState(context) {
    const statuses = ["locations", "maps", "canonical"]
      .map((key) => String(context.subsystems?.[key]?.status || context.resources?.[key]?.state || "unknown").toLowerCase());
    if (context.offline === true || globalThis.navigator?.onLine === false) {
      return {kind: "offline", message: "Offline: showing cached geography; some sources may be unavailable."};
    }
    if (statuses.some((status) => ["unknown", "unavailable", "error"].includes(status))) {
      return {kind: "partial", message: "Partial geography: some CKL or Maps sources are unavailable for this passage."};
    }
    return {kind: "ready", message: ""};
  }

  return Object.freeze({render, canonicalPlaces, geographyState});
});
