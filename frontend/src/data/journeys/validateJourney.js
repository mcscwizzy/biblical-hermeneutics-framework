function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function describeJourney(journey) {
  return journey && typeof journey.id === "string" && journey.id ? journey.id : "<unknown journey>";
}

const VALID_TESTAMENTS = new Set(["Old Testament", "New Testament"]);

export function validateJourney(journey, sourceLabel = describeJourney(journey)) {
  const errors = [];
  const warnings = [];

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
    if (Object.prototype.hasOwnProperty.call(journey, "testament") && typeof journey.testament === "string" && !VALID_TESTAMENTS.has(journey.testament)) {
      warnings.push(`testament "${journey.testament}" is not a standard testament label`);
    }
    if (Object.prototype.hasOwnProperty.call(journey, "testament") && journey.testament !== undefined && typeof journey.testament !== "string") {
      warnings.push("testament should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(journey, "bookRange") && !Array.isArray(journey.bookRange)) {
      warnings.push("bookRange should be an array if provided");
    }
    if (Object.prototype.hasOwnProperty.call(journey, "tags") && !Array.isArray(journey.tags)) {
      warnings.push("tags should be an array if provided");
    }
    if (Object.prototype.hasOwnProperty.call(journey, "category") && journey.category !== undefined && typeof journey.category !== "string") {
      warnings.push("category should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(journey, "era") && journey.era !== undefined && typeof journey.era !== "string") {
      warnings.push("era should be a string if provided");
    }
  }

  if (warnings.length > 0) {
    console.warn(`[BHF Journey] Metadata warnings for ${sourceLabel}: ${warnings.join(", ")}`);
  }

  if (errors.length > 0) {
    console.warn(`[BHF Journey] Skipping invalid journey ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }

  const stopIds = new Set();
  for (const stop of journey.stops) {
    if (!isPlainObject(stop)) {
      errors.push(`stop entries must be objects (${sourceLabel})`);
      continue;
    }
    if (typeof stop.id !== "string" || !stop.id.trim()) {
      errors.push(`stop missing id (${sourceLabel})`);
    } else {
      if (stopIds.has(stop.id)) {
        errors.push(`duplicate stop id "${stop.id}" (${sourceLabel})`);
      }
      stopIds.add(stop.id);
    }
    if (typeof stop.name !== "string" || !stop.name.trim()) {
      errors.push(`stop ${stop.id || "<unknown>"} missing name (${sourceLabel})`);
    }
    if (!isFiniteNumber(stop.lat)) {
      errors.push(`stop ${stop.id || "<unknown>"} missing numeric lat (${sourceLabel})`);
    }
    if (!isFiniteNumber(stop.lng)) {
      errors.push(`stop ${stop.id || "<unknown>"} missing numeric lng (${sourceLabel})`);
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
    } else {
      if (segmentIds.has(segment.id)) {
        errors.push(`duplicate segment id "${segment.id}" (${sourceLabel})`);
      }
      segmentIds.add(segment.id);
    }
    if (!stopIds.has(segment.from)) {
      errors.push(`segment from "${segment.from}" does not match a stop id (${sourceLabel})`);
    }
    if (!stopIds.has(segment.to)) {
      errors.push(`segment to "${segment.to}" does not match a stop id (${sourceLabel})`);
    }
  }

  if (errors.length > 0) {
    console.warn(`[BHF Journey] Skipping invalid journey ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }

  return true;
}
