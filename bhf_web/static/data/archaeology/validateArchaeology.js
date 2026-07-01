function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function describeArchaeologyRecord(record) {
  return record && typeof record.id === "string" && record.id ? record.id : "<unknown archaeology record>";
}

const VALID_CONFIDENCE_LEVELS = [
  "Established",
  "Well Supported",
  "Reasonably Supported",
  "Tentative",
  "Traditional Identification",
];

const CONFIDENCE_FRAMEWORK = {
  "Established": {
    explanation: "Broad scholarly agreement and stable identification across the literature.",
  },
  "Well Supported": {
    explanation: "Strong evidence supports the identification, with only limited disagreement.",
  },
  "Reasonably Supported": {
    explanation: "The evidence is good, but important questions or alternative views remain.",
  },
  "Tentative": {
    explanation: "The evidence is limited or the identification remains significantly debated.",
  },
  "Traditional Identification": {
    explanation: "The identification rests mainly on historical tradition rather than conclusive archaeology.",
  },
};

const CONFIDENCE_ALIASES = new Map([
  ["established", "Established"],
  ["strong", "Established"],
  ["well supported", "Well Supported"],
  ["likely", "Well Supported"],
  ["reasonably supported", "Reasonably Supported"],
  ["moderate", "Reasonably Supported"],
  ["tentative", "Tentative"],
  ["possible", "Tentative"],
  ["disputed", "Tentative"],
  ["traditional", "Traditional Identification"],
  ["traditional identification", "Traditional Identification"],
  ["well-supported", "Well Supported"],
  ["reasonably-supported", "Reasonably Supported"],
]);

export function normalizeConfidenceLevel(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return "Tentative";
  }
  const alias = CONFIDENCE_ALIASES.get(normalized.toLowerCase());
  if (alias) {
    return alias;
  }
  return VALID_CONFIDENCE_LEVELS.includes(normalized) ? normalized : "Tentative";
}

export function getConfidenceExplanation(value) {
  const normalized = normalizeConfidenceLevel(value);
  return CONFIDENCE_FRAMEWORK[normalized]?.explanation || CONFIDENCE_FRAMEWORK.Tentative.explanation;
}

function pushStringError(errors, field, label) {
  errors.push(`${label} ${field} must be a non-empty string`);
}

function validateStringList(value, field, label, errors, warnings, { required = true } = {}) {
  if (!Array.isArray(value)) {
    if (required) {
      errors.push(`${label} ${field} must be a non-empty array`);
    } else {
      warnings.push(`${label} ${field} should be an array if provided`);
    }
    return [];
  }
  const items = value.map((entry) => String(entry).trim()).filter(Boolean);
  if (required && items.length === 0) {
    errors.push(`${label} ${field} must be a non-empty array`);
  }
  return items;
}

function validateCommonFields(record, label, errors, warnings) {
  if (typeof record.id !== "string" || !record.id.trim()) {
    pushStringError(errors, "id", label);
  }
  if (typeof record.name !== "string" || !record.name.trim()) {
    pushStringError(errors, "name", label);
  }
  if (typeof record.description !== "string" || !record.description.trim()) {
    pushStringError(errors, "description", label);
  }
  if (typeof record.confidence !== "string" || !record.confidence.trim()) {
    pushStringError(errors, "confidence", label);
  } else if (!VALID_CONFIDENCE_LEVELS.includes(normalizeConfidenceLevel(record.confidence))) {
    warnings.push(`${label} confidence "${record.confidence}" is not a canonical archaeology confidence level`);
  }
  if (Object.prototype.hasOwnProperty.call(record, "confidenceExplanation") && (typeof record.confidenceExplanation !== "string" || !record.confidenceExplanation.trim())) {
    warnings.push(`${label} confidenceExplanation should explain why the confidence level was chosen`);
  }
  if (typeof record.caution !== "string" || !record.caution.trim()) {
    warnings.push(`${label} caution should be a string`);
  }
}

function finalizeWarnings(sourceLabel, warnings) {
  if (warnings.length > 0) {
    console.warn(`[BHF Archaeology] Metadata warnings for ${sourceLabel}: ${warnings.join(", ")}`);
  }
}

function finalizeErrors(sourceLabel, errors) {
  if (errors.length > 0) {
    console.warn(`[BHF Archaeology] Skipping invalid archaeology record ${sourceLabel}: ${errors.join(", ")}`);
    return false;
  }
  return true;
}

export function validateArchaeologySite(site, sourceLabel = describeArchaeologyRecord(site)) {
  const errors = [];
  const warnings = [];

  if (!isPlainObject(site)) {
    errors.push("site must be an object");
  } else {
    validateCommonFields(site, "site", errors, warnings);
    if (!isFiniteNumber(site.lat)) {
      errors.push("site lat must be a finite number");
    }
    if (!isFiniteNumber(site.lng)) {
      errors.push("site lng must be a finite number");
    }
    if (typeof site.country !== "string" || !site.country.trim()) {
      pushStringError(errors, "country", "site");
    }
    if (typeof site.region !== "string" || !site.region.trim()) {
      pushStringError(errors, "region", "site");
    }
    if (typeof site.siteType !== "string" && Object.prototype.hasOwnProperty.call(site, "siteType")) {
      warnings.push("site siteType should be a string if provided");
    }
    validateStringList(site.periods, "periods", "site", errors, warnings);
    validateStringList(site.discoveries, "discoveries", "site", errors, warnings);
    validateStringList(site.relatedPassages, "relatedPassages", "site", errors, warnings);
    if (Object.prototype.hasOwnProperty.call(site, "kingdom") && site.kingdom !== undefined && typeof site.kingdom !== "string") {
      warnings.push("site kingdom should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(site, "testament") && site.testament !== undefined && typeof site.testament !== "string") {
      warnings.push("site testament should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(site, "excavationSummary") && site.excavationSummary !== undefined && typeof site.excavationSummary !== "string") {
      warnings.push("site excavationSummary should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(site, "historicalSignificance") && site.historicalSignificance !== undefined && typeof site.historicalSignificance !== "string") {
      warnings.push("site historicalSignificance should be a string if provided");
    }
  }

  finalizeWarnings(sourceLabel, warnings);
  if (!finalizeErrors(sourceLabel, errors)) {
    return false;
  }

  return {
    ...site,
    periods: validateStringList(site.periods, "periods", "site", [], [], { required: true }),
    discoveries: validateStringList(site.discoveries, "discoveries", "site", [], [], { required: true }),
    relatedPassages: validateStringList(site.relatedPassages, "relatedPassages", "site", [], [], { required: true }),
    confidence: normalizeConfidenceLevel(site.confidence),
    confidenceExplanation: String(site.confidenceExplanation || getConfidenceExplanation(site.confidence)),
  };
}

export function validateArchaeologyArtifact(artifact, sourceLabel = describeArchaeologyRecord(artifact)) {
  const errors = [];
  const warnings = [];

  if (!isPlainObject(artifact)) {
    errors.push("artifact must be an object");
  } else {
    validateCommonFields(artifact, "artifact", errors, warnings);
    if (Object.prototype.hasOwnProperty.call(artifact, "siteId") && artifact.siteId !== undefined && typeof artifact.siteId !== "string") {
      warnings.push("artifact siteId should be a string if provided");
    }
    if (typeof artifact.museum !== "string" || !artifact.museum.trim()) {
      pushStringError(errors, "museum", "artifact");
    }
    if (typeof artifact.dateDiscovered !== "string" || !artifact.dateDiscovered.trim()) {
      pushStringError(errors, "dateDiscovered", "artifact");
    }
    validateStringList(artifact.relatedPassages, "relatedPassages", "artifact", errors, warnings);
    if (Object.prototype.hasOwnProperty.call(artifact, "artifactType") && artifact.artifactType !== undefined && typeof artifact.artifactType !== "string") {
      warnings.push("artifact artifactType should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(artifact, "discoveryLocation") && artifact.discoveryLocation !== undefined && typeof artifact.discoveryLocation !== "string") {
      warnings.push("artifact discoveryLocation should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(artifact, "currentLocation") && artifact.currentLocation !== undefined && typeof artifact.currentLocation !== "string") {
      warnings.push("artifact currentLocation should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(artifact, "significance") && artifact.significance !== undefined && typeof artifact.significance !== "string") {
      warnings.push("artifact significance should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(artifact, "kingdom") && artifact.kingdom !== undefined && typeof artifact.kingdom !== "string") {
      warnings.push("artifact kingdom should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(artifact, "country") && artifact.country !== undefined && typeof artifact.country !== "string") {
      warnings.push("artifact country should be a string if provided");
    }
    if (Object.prototype.hasOwnProperty.call(artifact, "region") && artifact.region !== undefined && typeof artifact.region !== "string") {
      warnings.push("artifact region should be a string if provided");
    }
  }

  finalizeWarnings(sourceLabel, warnings);
  if (!finalizeErrors(sourceLabel, errors)) {
    return false;
  }

  return {
    ...artifact,
    relatedPassages: validateStringList(artifact.relatedPassages, "relatedPassages", "artifact", [], [], { required: true }),
    confidence: normalizeConfidenceLevel(artifact.confidence),
    confidenceExplanation: String(artifact.confidenceExplanation || getConfidenceExplanation(artifact.confidence)),
  };
}

export function validateExcavationReport(report, sourceLabel = describeArchaeologyRecord(report)) {
  const errors = [];
  const warnings = [];

  if (!isPlainObject(report)) {
    errors.push("excavation report must be an object");
  } else {
    if (typeof report.id !== "string" || !report.id.trim()) {
      pushStringError(errors, "id", "excavation report");
    }
    if (typeof report.siteId !== "string" || !report.siteId.trim()) {
      pushStringError(errors, "siteId", "excavation report");
    }
    if (typeof report.title !== "string" || !report.title.trim()) {
      pushStringError(errors, "title", "excavation report");
    }
    if (typeof report.summary !== "string" || !report.summary.trim()) {
      pushStringError(errors, "summary", "excavation report");
    }
    validateStringList(report.periods, "periods", "excavation report", errors, warnings, { required: false });
    validateStringList(report.majorDiscoveries, "majorDiscoveries", "excavation report", errors, warnings, { required: false });
    validateStringList(report.debates, "debates", "excavation report", errors, warnings, { required: false });
    if (typeof report.confidence !== "string" || !report.confidence.trim()) {
      pushStringError(errors, "confidence", "excavation report");
    }
    if (Object.prototype.hasOwnProperty.call(report, "confidenceExplanation") && (typeof report.confidenceExplanation !== "string" || !report.confidenceExplanation.trim())) {
      warnings.push("excavation report confidenceExplanation should explain why the report's confidence level was chosen");
    }
    if (typeof report.caution !== "string" || !report.caution.trim()) {
      warnings.push("excavation report caution should be a string");
    }
  }

  finalizeWarnings(sourceLabel, warnings);
  if (!finalizeErrors(sourceLabel, errors)) {
    return false;
  }

  return {
    ...report,
    periods: validateStringList(report.periods, "periods", "excavation report", [], [], { required: false }),
    majorDiscoveries: validateStringList(report.majorDiscoveries, "majorDiscoveries", "excavation report", [], [], { required: false }),
    debates: validateStringList(report.debates, "debates", "excavation report", [], [], { required: false }),
    confidence: normalizeConfidenceLevel(report.confidence),
    confidenceExplanation: String(report.confidenceExplanation || getConfidenceExplanation(report.confidence)),
  };
}

export function validateMuseum(museum, sourceLabel = describeArchaeologyRecord(museum)) {
  const errors = [];
  const warnings = [];

  if (!isPlainObject(museum)) {
    errors.push("museum must be an object");
  } else {
    if (typeof museum.id !== "string" || !museum.id.trim()) {
      pushStringError(errors, "id", "museum");
    }
    if (typeof museum.name !== "string" || !museum.name.trim()) {
      pushStringError(errors, "name", "museum");
    }
    if (typeof museum.country !== "string" || !museum.country.trim()) {
      pushStringError(errors, "country", "museum");
    }
    if (typeof museum.city !== "string" || !museum.city.trim()) {
      pushStringError(errors, "city", "museum");
    }
    if (typeof museum.description !== "string" || !museum.description.trim()) {
      pushStringError(errors, "description", "museum");
    }
    if (Object.prototype.hasOwnProperty.call(museum, "website") && museum.website !== undefined && typeof museum.website !== "string") {
      warnings.push("museum website should be a string if provided");
    }
    validateStringList(museum.featuredArtifacts, "featuredArtifacts", "museum", errors, warnings, { required: false });
    validateStringList(museum.featuredSites, "featuredSites", "museum", errors, warnings, { required: false });
  }

  finalizeWarnings(sourceLabel, warnings);
  if (!finalizeErrors(sourceLabel, errors)) {
    return false;
  }

  return {
    ...museum,
    featuredArtifacts: validateStringList(museum.featuredArtifacts, "featuredArtifacts", "museum", [], [], { required: false }),
    featuredSites: validateStringList(museum.featuredSites, "featuredSites", "museum", [], [], { required: false }),
  };
}

export function validateArchaeologyCollection(collection, validator, sourceLabel) {
  if (!Array.isArray(collection)) {
    console.warn(`[BHF Archaeology] Skipping invalid archaeology file ${sourceLabel}: expected an array`);
    return [];
  }
  const seenIds = new Set();
  const records = [];

  for (const record of collection) {
    const validated = validator(record, sourceLabel);
    if (!validated) {
      continue;
    }
    if (seenIds.has(validated.id)) {
      console.warn(`[BHF Archaeology] Skipping duplicate archaeology id "${validated.id}" in ${sourceLabel}`);
      continue;
    }
    seenIds.add(validated.id);
    records.push(validated);
  }

  return records;
}

export { CONFIDENCE_FRAMEWORK, VALID_CONFIDENCE_LEVELS };
