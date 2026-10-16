const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const helperSource = fs.readFileSync(
  path.resolve("bhf_web/static/maps/MapFocusAcknowledgment.js"),
  "utf8",
);

async function helpers() {
  const dataUrl = `data:text/javascript;base64,${Buffer.from(helperSource).toString("base64")}`;
  return import(dataUrl);
}

test("focus acknowledgments are opt-in and preserve requested target identity", async () => {
  const {requestedMapFocus} = await helpers();

  assert.equal(requestedMapFocus({focusPlaceId: "eden"}), null);
  assert.deepEqual(
    requestedMapFocus({acknowledgeFocus: true, focusPlaceId: "eden"}),
    {kind: "place", id: "eden"},
  );
  assert.deepEqual(
    requestedMapFocus({acknowledgeFocus: true, focusRouteId: "exodus-route"}),
    {kind: "route", id: "exodus-route"},
  );
});

test("selected status requires exact loaded and selected kind and ID", async () => {
  const {acknowledgeMapFocus} = await helpers();
  const request = {kind: "place", id: "eden"};

  assert.deepEqual(
    acknowledgeMapFocus({
      request,
      markers: [{id: "eden"}],
      selected: {kind: "place", id: "eden"},
    }),
    {
      status: "selected",
      requestedKind: "place",
      requestedId: "eden",
      selectedKind: "place",
      selectedId: "eden",
      reason: null,
    },
  );
  assert.equal(
    acknowledgeMapFocus({
      request,
      markers: [{id: "eden"}],
      selected: {kind: "place", id: "other"},
    }).status,
    "failed",
  );
});

test("a completed online lookup distinguishes missing, unsupported, and offline targets", async () => {
  const {acknowledgeMapFocus} = await helpers();

  assert.equal(acknowledgeMapFocus({request: {kind: "place", id: "absent"}, markers: []}).status, "not_found");
  assert.equal(acknowledgeMapFocus({request: {kind: "historical_layer", id: "period"}}).status, "unsupported");
  assert.equal(acknowledgeMapFocus({request: {kind: "place", id: "absent"}, offline: true}).status, "unavailable");
  assert.equal(acknowledgeMapFocus({request: {kind: "place", id: "eden"}, failureReason: "lookup_failed"}).status, "failed");
  assert.equal(acknowledgeMapFocus({request: null}), null);
});
