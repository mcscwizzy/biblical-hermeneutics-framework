const test = require("node:test");
const assert = require("node:assert/strict");

const {
  BACKEND_CONFIGURATION_MESSAGE,
  LOST_JOB_MESSAGE,
  backendStartError,
  missingJobStateMessage,
  pollJsonJob,
  shouldFetchResult,
  useSynchronousAsk,
} = require("../../bhf_web/static/api/job-flow.js");

test("a missing remote backend blocks job startup", () => {
  let jobPosts = 0;
  let polls = 0;
  let spinnerRunning = false;
  const error = backendStartError(
    {backendConfigurationError: () => BACKEND_CONFIGURATION_MESSAGE},
    {backendMode: "remote", apiBaseUrl: ""},
  );
  if (!error) {
    spinnerRunning = true;
    jobPosts += 1;
    polls += 1;
  }

  assert.equal(error, BACKEND_CONFIGURATION_MESSAGE);
  assert.equal(jobPosts, 0);
  assert.equal(polls, 0);
  assert.equal(spinnerRunning, false);
});

test("a Vercel same-origin deployment uses the synchronous ask route", () => {
  assert.equal(
    useSynchronousAsk({backendMode: "same-origin", asyncJobs: false}),
    true,
  );
  assert.equal(
    useSynchronousAsk({backendMode: "same-origin", asyncJobs: true}),
    false,
  );
  assert.equal(useSynchronousAsk({backendMode: "remote", asyncJobs: true}), false);
});

test("an explicit deployment error still blocks job startup", () => {
  const message = "Backend routing is invalid.";
  assert.equal(
    backendStartError(null, {
      backendMode: "same-origin",
      backendConfigError: message,
    }),
    message,
  );
});

test("a missing job stops polling with a useful retry message", () => {
  const message = missingJobStateMessage({
    status: 404,
    errorCategory: "job_state_missing",
    serverMessage: "",
  });

  assert.equal(message, LOST_JOB_MESSAGE);
  assert.match(message, /Please submit the question again/);
});

test("unrelated polling failures are not classified as lost job state", () => {
  assert.equal(
    missingJobStateMessage({status: 429, errorCategory: "provider_rate_limit"}),
    "",
  );
});

test("a known failed job does not fetch its result", () => {
  assert.equal(
    shouldFetchResult({done: true, status: "error", error: "Provider timed out"}),
    false,
  );
});

test("a successful job still fetches its result", () => {
  assert.equal(
    shouldFetchResult({done: true, status: "complete", error: null}),
    true,
  );
});

test("JSON job polling is bounded and returns the successful presentation payload", async () => {
  const states = [
    {status: "queued"},
    {status: "running"},
    {status: "succeeded", result: {presentation_packet: {cards: [{id: "ai"}]}}},
  ];
  let polls = 0;

  const result = await pollJsonJob({
    initialDelay: 0,
    interval: 250,
    maxAttempts: 4,
    poll: async () => states[polls++],
  });

  assert.equal(polls, 3);
  assert.equal(result.presentation_packet.cards[0].id, "ai");
});

test("failed presentation polling exposes only the public category", async () => {
  await assert.rejects(
    pollJsonJob({
      initialDelay: 0,
      poll: async () => ({
        status: "failed",
        error_category: "validation_rejected",
        message: "AI presentation output was rejected.",
      }),
    }),
    (error) => error.code === "validation_rejected"
      && !error.message.includes("provider response"),
  );
});

test("aborting ownership stops presentation polling silently", async () => {
  const controller = new AbortController();
  let polls = 0;
  const pending = pollJsonJob({
    initialDelay: 0,
    interval: 250,
    poll: async () => {
      polls += 1;
      return {status: "running"};
    },
    onStatus: () => controller.abort(),
    signal: controller.signal,
  });

  await assert.rejects(pending, (error) => error.name === "AbortError");
  assert.equal(polls, 1);
});

test("presentation polling expires after its configured attempt bound", async () => {
  let polls = 0;
  await assert.rejects(
    pollJsonJob({
      initialDelay: 0,
      interval: 250,
      maxAttempts: 2,
      poll: async () => {
        polls += 1;
        return {status: "running"};
      },
    }),
    (error) => error.code === "provider_timeout",
  );
  assert.equal(polls, 2);
});
