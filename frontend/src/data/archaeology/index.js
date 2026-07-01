import {
  CONFIDENCE_FRAMEWORK,
  VALID_CONFIDENCE_LEVELS,
  getConfidenceExplanation,
  normalizeConfidenceLevel,
  validateArchaeologyArtifact,
  validateArchaeologyCollection,
  validateArchaeologySite,
  validateExcavationReport,
  validateMuseum,
} from "./validateArchaeology.js";

export const ARCHAEOLOGY_FILES = {
  sites: "archaeologySites.json",
  artifacts: "artifacts.json",
  excavationReports: "excavationReports.json",
  museums: "museums.json",
};

let archaeologyCatalogPromise = null;

export let archaeologySites = [];
export let archaeologyArtifacts = [];
export let excavationReports = [];
export let museums = [];

export let archaeologySitesById = {};
export let archaeologyArtifactsById = {};
export let excavationReportsById = {};
export let museumsById = {};

function readArchaeologyFile(fileName) {
  const url = new URL(`./${fileName}`, import.meta.url);
  return fetch(url).then(async (response) => {
    if (!response.ok) {
      throw new Error(`Could not load archaeology data from ${fileName}.`);
    }
    return response.json();
  });
}

function collectFacetList(items, field) {
  return Array.from(
    new Set(
      items
        .flatMap((item) => (Array.isArray(item[field]) ? item[field] : item[field] ? [item[field]] : []))
        .map((value) => String(value).trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));
}

function collectCombinedFacetList(items, fields) {
  return Array.from(
    new Set(fields.flatMap((field) => collectFacetList(items, field)))
  ).sort((a, b) => a.localeCompare(b));
}

function enrichArtifact(artifact, siteMap, museumMap) {
  const site = artifact.siteId ? siteMap[artifact.siteId] || null : null;
  const museum = artifact.museumId ? museumMap[artifact.museumId] || null : null;
  return {
    ...artifact,
    site,
    museumRecord: museum,
    siteName: site?.name || artifact.siteName || artifact.siteId || "",
    museumName: museum?.name || artifact.museum || "",
    confidenceLevel: normalizeConfidenceLevel(artifact.confidence),
    confidenceExplanation: artifact.confidenceExplanation || getConfidenceExplanation(artifact.confidence),
  };
}

async function loadArchaeologyRecords() {
  const [siteResult, artifactResult, reportResult, museumResult] = await Promise.allSettled([
    readArchaeologyFile(ARCHAEOLOGY_FILES.sites),
    readArchaeologyFile(ARCHAEOLOGY_FILES.artifacts),
    readArchaeologyFile(ARCHAEOLOGY_FILES.excavationReports),
    readArchaeologyFile(ARCHAEOLOGY_FILES.museums),
  ]);

  const siteRecords = siteResult.status === "fulfilled" ? validateArchaeologyCollection(siteResult.value, validateArchaeologySite, ARCHAEOLOGY_FILES.sites) : [];
  const museumRecords = museumResult.status === "fulfilled" ? validateArchaeologyCollection(museumResult.value, validateMuseum, ARCHAEOLOGY_FILES.museums) : [];
  const reportRecords = reportResult.status === "fulfilled" ? validateArchaeologyCollection(reportResult.value, validateExcavationReport, ARCHAEOLOGY_FILES.excavationReports) : [];

  const siteMap = Object.fromEntries(siteRecords.map((site) => [site.id, site]));
  const museumMap = Object.fromEntries(museumRecords.map((museum) => [museum.id, museum]));
  const artifactRecords = artifactResult.status === "fulfilled"
    ? validateArchaeologyCollection(
        artifactResult.value.map((artifact) => enrichArtifact(artifact, siteMap, museumMap)),
        validateArchaeologyArtifact,
        ARCHAEOLOGY_FILES.artifacts
      )
    : [];

  archaeologySites = siteRecords;
  archaeologyArtifacts = artifactRecords;
  excavationReports = reportRecords;
  museums = museumRecords;

  archaeologySitesById = Object.fromEntries(siteRecords.map((site) => [site.id, site]));
  archaeologyArtifactsById = Object.fromEntries(artifactRecords.map((artifact) => [artifact.id, artifact]));
  excavationReportsById = Object.fromEntries(reportRecords.map((report) => [report.id, report]));
  museumsById = Object.fromEntries(museumRecords.map((museum) => [museum.id, museum]));

  const siteIds = new Set(artifactsToSiteIds(artifactRecords));
  const excavationReportsBySiteId = Object.fromEntries(
    siteRecords.map((site) => [
      site.id,
      reportRecords.filter((report) => report.siteId === site.id),
    ])
  );

  return {
    confidenceFramework: CONFIDENCE_FRAMEWORK,
    confidenceLevels: VALID_CONFIDENCE_LEVELS,
    sites: siteRecords,
    artifacts: artifactRecords,
    excavationReports: reportRecords,
    museums: museumRecords,
    sitesById: archaeologySitesById,
    artifactsById: archaeologyArtifactsById,
    excavationReportsById,
    museumsById,
    excavationReportsBySiteId,
    siteIds: Array.from(siteIds).sort((left, right) => left.localeCompare(right)),
    countries: collectFacetList([...siteRecords, ...artifactRecords], "country"),
    regions: collectFacetList([...siteRecords, ...artifactRecords], "region"),
    periods: collectCombinedFacetList([...siteRecords, ...artifactRecords, ...reportRecords], ["periods", "period"]),
    kingdoms: collectFacetList([...siteRecords, ...artifactRecords], "kingdom"),
    testaments: collectFacetList([...siteRecords, ...artifactRecords], "testament"),
    artifactTypes: collectFacetList(artifactRecords, "artifactType"),
    confidenceLevels: VALID_CONFIDENCE_LEVELS.slice(),
  };
}

function artifactsToSiteIds(artifacts) {
  return artifacts.map((artifact) => artifact.siteId).filter(Boolean);
}

export async function loadArchaeologyCatalog() {
  if (!archaeologyCatalogPromise) {
    archaeologyCatalogPromise = loadArchaeologyRecords().catch((error) => {
      archaeologyCatalogPromise = null;
      throw error;
    });
  }
  return archaeologyCatalogPromise;
}

export async function loadArchaeologySites() {
  const catalog = await loadArchaeologyCatalog();
  return catalog.sites;
}

export async function loadArchaeologyArtifacts() {
  const catalog = await loadArchaeologyCatalog();
  return catalog.artifacts;
}

export async function loadExcavationReports() {
  const catalog = await loadArchaeologyCatalog();
  return catalog.excavationReports;
}

export async function loadMuseums() {
  const catalog = await loadArchaeologyCatalog();
  return catalog.museums;
}

export async function loadArchaeologyReferenceCatalog() {
  const catalog = await loadArchaeologyCatalog();
  return {
    ...catalog,
    siteArtifacts: Object.fromEntries(
      catalog.sites.map((site) => [
        site.id,
        catalog.artifacts.filter((artifact) => artifact.siteId === site.id),
      ])
    ),
  };
}

export {
  CONFIDENCE_FRAMEWORK,
  VALID_CONFIDENCE_LEVELS,
  getConfidenceExplanation,
  normalizeConfidenceLevel,
  collectFacetList,
  collectCombinedFacetList,
};
