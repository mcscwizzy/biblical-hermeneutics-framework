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
    const configuredError = String(runtime.backendConfigError || "").trim();
    if (configuredError) return configuredError;
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

  function useSynchronousAsk(runtime = {}) {
    return runtime.asyncJobs === false;
  }

  async function pollJsonJob(options = {}) {
    const poll = options.poll;
    if (typeof poll !== "function") throw new Error("A job poll function is required.");
    const signal = options.signal;
    const initialDelay = Math.max(0, Number(options.initialDelay ?? 250));
    const interval = Math.max(250, Number(options.interval ?? 1000));
    const maxAttempts = Math.max(1, Number(options.maxAttempts ?? 36));
    await abortableDelay(initialDelay, signal);
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      throwIfAborted(signal);
      const status = await poll();
      throwIfAborted(signal);
      options.onStatus?.(status);
      const state = String(status?.status || "").toLowerCase();
      if (state === "succeeded") return status?.result || {};
      if (state === "failed" || state === "expired") {
        const error = new Error(
          status?.message || "AI presentation enhancement is unavailable.",
        );
        error.code = String(status?.error_category || "presentation_unavailable");
        error.jobStatus = status;
        throw error;
      }
      if (attempt + 1 < maxAttempts) {
        const modestBackoff = Math.min(1500, interval + attempt * 25);
        await abortableDelay(modestBackoff, signal);
      }
    }
    const error = new Error("AI presentation job polling expired.");
    error.code = "provider_timeout";
    throw error;
  }

  function abortableDelay(milliseconds, signal) {
    throwIfAborted(signal);
    if (!milliseconds) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const finish = () => {
        signal?.removeEventListener("abort", abort);
        resolve();
      };
      const abort = () => {
        clearTimeout(timer);
        signal?.removeEventListener("abort", abort);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = setTimeout(finish, milliseconds);
      signal?.addEventListener("abort", abort, {once: true});
    });
  }

  function throwIfAborted(signal) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
  }

  return {
    BACKEND_CONFIGURATION_MESSAGE,
    LOST_JOB_MESSAGE,
    backendStartError,
    missingJobStateMessage,
    pollJsonJob,
    shouldFetchResult,
    useSynchronousAsk,
  };
});
