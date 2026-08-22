(function (root, factory) {
  const jobFlow = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = jobFlow;
  }
  root.BHFJobFlow = jobFlow;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const LOST_JOB_MESSAGE =
    "The request state was lost during a server restart or deployment. Please submit the question again.";
  const BACKEND_CONFIGURATION_MESSAGE =
    "BHF backend is not configured for this deployment.";

  function backendStartError(http, runtime = {}) {
    if (http && typeof http.backendConfigurationError === "function") {
      return http.backendConfigurationError();
    }
    return String(runtime.backendMode || "same-origin") === "remote"
      ? BACKEND_CONFIGURATION_MESSAGE
      : "";
  }

  function missingJobStateMessage(error) {
    if (Number(error?.status) !== 404 || error?.errorCategory !== "job_state_missing") {
      return "";
    }
    return String(error.serverMessage || "").trim() || LOST_JOB_MESSAGE;
  }

  function shouldFetchResult(finalStatus) {
    return !finalStatus?.error;
  }

  return {
    BACKEND_CONFIGURATION_MESSAGE,
    LOST_JOB_MESSAGE,
    backendStartError,
    missingJobStateMessage,
    shouldFetchResult,
  };
});
