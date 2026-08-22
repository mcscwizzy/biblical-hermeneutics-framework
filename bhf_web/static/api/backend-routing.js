(function (root, factory) {
  const routing = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = routing;
  }
  root.BHFBackendRouting = routing;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const CONFIGURATION_MESSAGE = "BHF backend is not configured for this deployment.";

  function isAbsoluteUrl(value) {
    return /^(?:[a-z]+:)?\/\//i.test(value)
      || value.startsWith("data:")
      || value.startsWith("blob:");
  }

  function isBackendPath(value) {
    if (!value || isAbsoluteUrl(value)) return false;
    let pathname;
    try {
      pathname = new URL(value, "https://bhf.invalid/").pathname;
    } catch (_error) {
      return false;
    }
    return pathname === "/ask"
      || pathname.startsWith("/ask/")
      || pathname === "/api"
      || pathname.startsWith("/api/");
  }

  function validRemoteBaseUrl(value) {
    try {
      const parsed = new URL(String(value || ""));
      return (parsed.protocol === "http:" || parsed.protocol === "https:")
        && Boolean(parsed.host)
        && !parsed.username
        && !parsed.password
        && !parsed.search
        && !parsed.hash;
    } catch (_error) {
      return false;
    }
  }

  function configurationError(runtime = {}) {
    const mode = String(runtime.backendMode || "same-origin").trim().toLowerCase();
    if (mode === "same-origin") return "";
    if (mode !== "remote" || !validRemoteBaseUrl(runtime.apiBaseUrl)) {
      return String(runtime.backendConfigError || "").trim() || CONFIGURATION_MESSAGE;
    }
    return "";
  }

  function resolveUrl(url, runtime = {}) {
    const raw = String(url || "");
    if (isAbsoluteUrl(raw) || !isBackendPath(raw)) return raw;

    const mode = String(runtime.backendMode || "same-origin").trim().toLowerCase();
    if (mode === "same-origin") return raw;

    const error = configurationError(runtime);
    if (error) {
      const configurationException = new Error(CONFIGURATION_MESSAGE);
      configurationException.name = "BHFBackendConfigurationError";
      throw configurationException;
    }

    const base = String(runtime.apiBaseUrl).replace(/\/+$/, "");
    return raw.startsWith("/") ? `${base}${raw}` : `${base}/${raw}`;
  }

  return {
    CONFIGURATION_MESSAGE,
    configurationError,
    isBackendPath,
    resolveUrl,
    validRemoteBaseUrl,
  };
});
