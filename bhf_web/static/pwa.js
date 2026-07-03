(function () {
  const runtime = window.BHFRuntimeConfig || {};
  const enableServiceWorker = runtime.enableServiceWorker !== false;

  if (!enableServiceWorker || !("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch((error) => {
        console.warn("BHF service worker registration failed:", error);
      });
  });
})();
