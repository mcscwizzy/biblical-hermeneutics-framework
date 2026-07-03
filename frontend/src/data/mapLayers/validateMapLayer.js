function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function describeMapLayer(layer) {
  return layer && typeof layer.id === "string" && layer.id ? layer.id : "<unknown layer>";
}

const VALID_LAYER_TYPES = new Set(["points", "lines", "polygons"]);

export function validateMapLayer(layer, sourceLabel = describeMapLayer(layer)) {
  const errors = [];
  const warnings = [];

  if (!isPlainObject(layer)) {
    errors.push("layer must be an object");
  } else {
    if (typeof layer.id !== "string" || !layer.id.trim()) {
      errors.push("missing id");
    }
    if (typeof layer.title !== "string" || !layer.title.trim()) {
      errors.push("missing title");
    }
    if (typeof layer.description !== "string") {
      warnings.push("description should be a string if provided");
    }
    if (typeof layer.type !== "string" || !VALID_LAYER_TYPES.has(layer.type)) {
      errors.push("type must be points, lines, or polygons");
    }
    if (!Array.isArray(layer.features) || layer.features.length === 0) {
      errors.push("features must be a non-empty array");
    }
    if (Object.prototype.hasOwnProperty.call(layer, "defaultVisible") && typeof layer.defaultVisible !== "boolean") {
      warnings.push("defaultVisible should be a boolean if provided");
    }
  }

  if (warnings.length > 0) {
    console.warn(`[BHF Layer] Metadata warnings for ${sourceLabel}: ${warnings.join(", ")}`);
  }

  if (errors.length > 0) {
    console.warn(`[BHF Layer] Skipping invalid layer ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }

  const featureIds = new Set();
  const features = [];

  for (const feature of layer.features) {
    if (!isPlainObject(feature)) {
      console.warn(`[BHF Layer] Skipping invalid feature in ${sourceLabel}: feature entries must be objects`);
      continue;
    }
    if (typeof feature.id !== "string" || !feature.id.trim()) {
      console.warn(`[BHF Layer] Skipping invalid feature in ${sourceLabel}: missing id`);
      continue;
    }
    if (featureIds.has(feature.id)) {
      console.warn(`[BHF Layer] Skipping duplicate feature id "${feature.id}" in ${sourceLabel}`);
      continue;
    }
    if (typeof feature.name !== "string" || !feature.name.trim()) {
      console.warn(`[BHF Layer] Skipping invalid feature "${feature.id}" in ${sourceLabel}: missing name`);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(feature, "periods") && !Array.isArray(feature.periods)) {
      console.warn(`[BHF Layer] Feature "${feature.id}" in ${sourceLabel} has non-array periods; ignoring the field`);
      feature.periods = [];
    }
    if (Object.prototype.hasOwnProperty.call(feature, "passages") && !Array.isArray(feature.passages)) {
      console.warn(`[BHF Layer] Feature "${feature.id}" in ${sourceLabel} has non-array passages; ignoring the field`);
      feature.passages = [];
    }

    if (layer.type === "points") {
      if (!isFiniteNumber(feature.lat) || !isFiniteNumber(feature.lng)) {
        console.warn(`[BHF Layer] Skipping invalid point feature "${feature.id}" in ${sourceLabel}: numeric lat/lng required`);
        continue;
      }
    } else {
      if (!Array.isArray(feature.points) || feature.points.length === 0) {
        console.warn(`[BHF Layer] Skipping invalid ${layer.type.slice(0, -1)} feature "${feature.id}" in ${sourceLabel}: points must be a non-empty array`);
        continue;
      }
      const invalidPoint = feature.points.some(
        (point) => !Array.isArray(point) || point.length < 2 || !isFiniteNumber(point[0]) || !isFiniteNumber(point[1])
      );
      if (invalidPoint) {
        console.warn(`[BHF Layer] Skipping invalid ${layer.type.slice(0, -1)} feature "${feature.id}" in ${sourceLabel}: each point must be [lat, lng]`);
        continue;
      }
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
    return false;
  }

  return {
    ...layer,
    defaultVisible: Boolean(layer.defaultVisible),
    features,
  };
}
