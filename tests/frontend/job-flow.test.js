const test = require("node:test");
const assert = require("node:assert/strict");

const {
  BACKEND_CONFIGURATION_MESSAGE,
  LOST_JOB_MESSAGE,
  backendStartError,
  missingJobStateMessage,
  shouldFetchResult,
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

test("an explicit same-origin deployment error blocks job startup", () => {
  const message = "A durable backend is required.";
  const error = backendStartError(null, {
    backendMode: "same-origin",
    backendConfigError: message,
  });

  assert.equal(error, message);
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
