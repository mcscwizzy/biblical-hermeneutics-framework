import { validateJourney } from "./validateJourney.js";

export const JOURNEY_FILES = [
  "abraham.json",
  "exodus.json",
  "joshua-conquest.json",
  "david-fleeing-saul.json",
  "elijah-elisha.json",
  "jesus-galilean-ministry.json",
  "jesus-final-week.json",
  "paul-first-missionary.json",
  "paul-second-missionary.json",
  "paul-third-missionary.json",
  "paul-rome-voyage.json",
  "exile-return.json",
];

let journeyCatalogPromise = null;

async function readJourneyFile(fileName) {
  const url = new URL(`./${fileName}`, import.meta.url);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load journey data from ${fileName}.`);
  }
  return response.json();
}

async function loadJourneyRecords() {
  const records = await Promise.allSettled(JOURNEY_FILES.map((fileName) => readJourneyFile(fileName)));
  const journeys = [];
  for (const [index, record] of records.entries()) {
    const fileName = JOURNEY_FILES[index];
    if (record.status !== "fulfilled") {
      console.warn(`[BHF Journey] Skipping journey file ${fileName}: ${record.reason?.message || "unknown error"}`);
      continue;
    }
    const journey = record.value;
    if (validateJourney(journey, fileName)) {
      journeys.push(journey);
    }
  }
  return journeys;
}

function collectFacetList(journeys, field) {
  return Array.from(
    new Set(
      journeys
        .flatMap((journey) => (Array.isArray(journey[field]) ? journey[field] : journey[field] ? [journey[field]] : []))
        .map((value) => String(value).trim())
        .filter(Boolean)
    )
  ).sort((a, b) => a.localeCompare(b));
}

export async function loadJourneys() {
  if (!journeyCatalogPromise) {
    journeyCatalogPromise = loadJourneyRecords();
  }
  return journeyCatalogPromise;
}

export async function loadJourneyCatalog() {
  const journeys = await loadJourneys();
  return {
    journeys,
    defaultJourneyId: journeys.find((journey) => journey.id === "abraham")?.id || journeys[0]?.id || "",
    categories: collectFacetList(journeys, "category"),
    eras: collectFacetList(journeys, "era"),
    testaments: collectFacetList(journeys, "testament"),
    tags: collectFacetList(journeys, "tags"),
  };
}
