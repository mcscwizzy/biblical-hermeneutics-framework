const SELECTABLE_MAP_KINDS = new Set(["place", "route"]);

export function requestedMapFocus(context = {}) {
  if (context.acknowledgeFocus !== true) return null;

  const explicitPlaceId = String(context.focusPlaceId || "").trim();
  const explicitRouteId = String(context.focusRouteId || "").trim();
  const kind = String(
    context.focusKind
      || context.mapFocus?.kind
      || (explicitPlaceId && explicitRouteId ? "multiple" : explicitPlaceId ? "place" : explicitRouteId ? "route" : ""),
  ).trim().toLowerCase();
  const id = String(
    context.focusTargetId
      || context.mapFocus?.targetId
      || explicitPlaceId
      || explicitRouteId,
  ).trim();
  return {kind, id};
}

export function acknowledgeMapFocus({
  request,
  markers = [],
  routes = [],
  selected = null,
  offline = false,
  failureReason = null,
  unsupportedReason = null,
} = {}) {
  if (!request) return null;
  const acknowledgment = {
    status: "failed",
    requestedKind: String(request.kind || ""),
    requestedId: String(request.id || ""),
    selectedKind: null,
    selectedId: null,
    reason: null,
  };

  if (
    unsupportedReason
    || !SELECTABLE_MAP_KINDS.has(acknowledgment.requestedKind)
    || !acknowledgment.requestedId
  ) {
    acknowledgment.status = "unsupported";
    acknowledgment.reason = unsupportedReason || "requested_map_target_not_supported";
    return acknowledgment;
  }

  if (failureReason) {
    acknowledgment.status = "failed";
    acknowledgment.reason = String(failureReason);
    return acknowledgment;
  }

  const loadedItems = acknowledgment.requestedKind === "place" ? markers : routes;
  const found = (Array.isArray(loadedItems) ? loadedItems : []).some(
    (item) => String(item?.id || "") === acknowledgment.requestedId,
  );
  if (!found) {
    acknowledgment.status = offline ? "unavailable" : "not_found";
    acknowledgment.reason = offline
      ? "requested_item_unavailable_offline"
      : "requested_item_not_found_in_loaded_map_data";
    return acknowledgment;
  }

  if (
    String(selected?.kind || "") !== acknowledgment.requestedKind
    || String(selected?.id || "") !== acknowledgment.requestedId
  ) {
    acknowledgment.status = "failed";
    acknowledgment.reason = "map_controller_did_not_select_requested_item";
    return acknowledgment;
  }

  acknowledgment.status = "selected";
  acknowledgment.selectedKind = acknowledgment.requestedKind;
  acknowledgment.selectedId = acknowledgment.requestedId;
  return acknowledgment;
}
