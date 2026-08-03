(function () {
  const SETTINGS_ID = "model-settings";
  const KEY_ID = "model-settings-key";
  const OPENROUTER = "openrouter";
  const AUTH_ATTEMPT_KEY = "bhf-openrouter-auth-attempt";
  const AUTH_ATTEMPT_TTL_MS = 10 * 60 * 1000;

  let settings = null;
  let openRouterToken = null;
  let readyPromise = null;

  function runtimeAi() {
    return window.BHFRuntimeConfig?.ai || {};
  }

  function openRouterConfig() {
    return runtimeAi().openrouter || {};
  }

  function defaultSettings() {
    return {
      id: SETTINGS_ID,
      version: 2,
      activeProvider: null,
      onboardingComplete: false,
      setupChoice: null,
      providers: {},
    };
  }

  function providerInput(form, name) {
    return form?.querySelector(`[name="${name}"]`);
  }

  function currentForm() {
    return document.querySelector(".ask-form");
  }

  function currentProvider(form = currentForm()) {
    return String(providerInput(form, "adapter")?.value || "openai_compatible");
  }

  function providerDefaults(provider) {
    const defaults = runtimeAi().defaults || {};
    if (provider === OPENROUTER) {
      return {
        baseUrl: openRouterConfig().baseUrl || "https://openrouter.ai/api/v1",
        model: openRouterConfig().defaultModel || "",
        temperature: 0.3,
        maxTokens: Number(defaults.max_tokens || 2048),
        contextWindow: Number(defaults.context_window || 12288),
        timeoutSeconds: 120,
        responseFormatPolicy: "auto",
      };
    }
    if (provider === "ollama") {
      return {
        baseUrl: "http://localhost:11434/v1",
        model: "llama3.1:8b",
        temperature: 0.3,
        maxTokens: Number(defaults.max_tokens || 2048),
        contextWindow: Number(defaults.context_window || 12288),
        timeoutSeconds: 360,
        responseFormatPolicy: "auto",
      };
    }
    return {
      baseUrl: "http://localhost:11434/v1",
      model: "llama3.1:8b",
      temperature: 0.3,
      maxTokens: Number(defaults.max_tokens || 2048),
      contextWindow: Number(defaults.context_window || 12288),
      timeoutSeconds: 360,
      responseFormatPolicy: "auto",
    };
  }

  function providerState(provider) {
    const saved = settings?.providers?.[provider];
    return {
      ...providerDefaults(provider),
      ...(saved && typeof saved === "object" ? saved : {}),
    };
  }

  function migrateSettings(value) {
    const migrated = value && typeof value === "object" ? {...value} : defaultSettings();
    migrated.id = SETTINGS_ID;
    migrated.version = 2;
    migrated.providers = migrated.providers && typeof migrated.providers === "object" ? migrated.providers : {};
    if (!Object.prototype.hasOwnProperty.call(migrated, "onboardingComplete")) {
      migrated.onboardingComplete = Boolean(migrated.activeProvider);
    }
    if (!Object.prototype.hasOwnProperty.call(migrated, "setupChoice")) {
      migrated.setupChoice = migrated.activeProvider ? "provider" : null;
    }
    for (const provider of Object.keys(migrated.providers)) {
      migrated.providers[provider] = {
        ...providerDefaults(provider),
        ...(migrated.providers[provider] && typeof migrated.providers[provider] === "object"
          ? migrated.providers[provider]
          : {}),
      };
    }
    if (!migrated.activeProvider && migrated.providers[OPENROUTER]?.token) {
      migrated.activeProvider = OPENROUTER;
      migrated.onboardingComplete = true;
      migrated.setupChoice = "provider";
    }
    return migrated;
  }

  async function readSettings() {
    if (!window.BHFOfflineDB) {
      throw new Error("BHF could not access this browser’s private app storage. Your connection was not saved.");
    }
    const stored = await window.BHFOfflineDB.get("modelSettings", SETTINGS_ID);
    const migrated = migrateSettings(stored);
    settings = migrated;
    if (!stored || JSON.stringify(stored) !== JSON.stringify(migrated)) {
      await writeSettings();
    }
    return migrated;
  }

  async function writeSettings() {
    if (!window.BHFOfflineDB || !settings) {
      return;
    }
    await window.BHFOfflineDB.put("modelSettings", {
      ...settings,
      id: SETTINGS_ID,
      updatedAt: new Date().toISOString(),
    });
  }

  function updateSettingsFromForm(form = currentForm()) {
    if (!form || !settings) {
      return;
    }
    const provider = currentProvider(form);
    settings.activeProvider = provider;
    settings.onboardingComplete = true;
    settings.setupChoice = "provider";
    settings.providers = settings.providers || {};
    const saved = providerState(provider);
    settings.providers[provider] = {
      ...saved,
      model: providerInput(form, "model")?.value || saved.model,
      baseUrl: providerInput(form, "base_url")?.value || saved.baseUrl,
      maxTokens: Number(providerInput(form, "max_tokens")?.value || saved.maxTokens),
      contextWindow: Number(providerInput(form, "context_window")?.value || saved.contextWindow),
      timeoutSeconds: Number(providerInput(form, "timeout_seconds")?.value || saved.timeoutSeconds),
      responseFormatPolicy: providerInput(form, "response_format_policy")?.value || saved.responseFormatPolicy,
    };
  }

  async function persistFormSettings() {
    updateSettingsFromForm();
    await writeSettings();
    updateConnectionStatus();
  }

  function fillOpenRouterModels(select) {
    if (!select || select.dataset.modelsReady === "true") {
      return;
    }
    select.replaceChildren();
    for (const model of openRouterConfig().models || []) {
      const option = document.createElement("option");
      option.value = model.id;
      option.textContent = `${model.label}${model.recommended ? " — Recommended" : model.experimental ? " — Experimental" : ""}`;
      select.appendChild(option);
    }
    const custom = document.createElement("option");
    custom.value = "__custom__";
    custom.textContent = "Custom OpenRouter model";
    select.appendChild(custom);
    select.dataset.modelsReady = "true";
  }

  function renderProviderState(form = currentForm()) {
    if (!form) {
      return;
    }
    const provider = currentProvider(form);
    const saved = providerState(provider);
    const model = providerInput(form, "model");
    const baseUrl = providerInput(form, "base_url");
    const modelSelect = form.querySelector("[data-openrouter-model]");
    if (modelSelect) modelSelect.hidden = provider !== OPENROUTER;
    if (provider === OPENROUTER && modelSelect) {
      fillOpenRouterModels(modelSelect);
      const known = [...modelSelect.options].some((option) => option.value === saved.model);
      modelSelect.value = known ? saved.model : "__custom__";
      const customModel = form.querySelector("[data-openrouter-custom-model]");
      if (customModel) {
        customModel.value = known ? "" : saved.model;
        customModel.hidden = modelSelect.value !== "__custom__";
      }
      if (model) {
        model.value = known ? saved.model : (customModel?.value || saved.model);
        model.hidden = modelSelect.value !== "__custom__";
      }
    } else if (model && !model.value) {
      model.value = saved.model;
    }
    if (baseUrl) {
      if (provider === OPENROUTER) {
        baseUrl.value = openRouterConfig().baseUrl || saved.baseUrl;
        baseUrl.readOnly = true;
      } else {
        baseUrl.readOnly = false;
        if (!baseUrl.value || baseUrl.dataset.modelSettingsManaged === "true") {
          baseUrl.value = saved.baseUrl;
        }
      }
      baseUrl.dataset.modelSettingsManaged = "true";
    }
    for (const [name, key] of [["max_tokens", "maxTokens"], ["context_window", "contextWindow"], ["timeout_seconds", "timeoutSeconds"]]) {
      const field = providerInput(form, name);
      if (field && (!field.value || field.dataset.modelSettingsManaged === "true")) {
        field.value = saved[key];
        field.dataset.modelSettingsManaged = "true";
      }
    }
    const credentialPanel = form.querySelector("[data-openrouter-credential]");
    if (credentialPanel) credentialPanel.hidden = provider !== OPENROUTER;
    const localFields = form.querySelector("[data-local-provider-fields]");
    if (localFields) localFields.hidden = provider === OPENROUTER;
    updateTokenStatus(form);
    updateConnectionStatus();
  }

  function updateTokenStatus(form = currentForm(), message = "") {
    const status = form?.querySelector("[data-openrouter-token-status]");
    if (!status) return;
    status.textContent = message || (openRouterToken ? "OpenRouter connected on this device." : "OpenRouter is not connected.");
  }

  function updateConnectionStatus(message = "") {
    const nodes = document.querySelectorAll("[data-ai-connection-status]");
    const provider = settings?.activeProvider;
    const label = provider === OPENROUTER && openRouterToken
      ? "OpenRouter connected on this device"
      : provider === "ollama"
        ? "Local AI connected"
        : provider === "openai_compatible"
          ? "Other OpenAI-compatible service connected"
          : "Not connected";
    nodes.forEach((node) => {
      node.textContent = message || label;
      node.dataset.status = message ? "error" : (provider && (provider !== OPENROUTER || openRouterToken) ? "connected" : "disconnected");
    });
  }

  async function ensureKey() {
    if (!window.crypto?.subtle || !window.BHFOfflineDB) {
      throw new Error("BHF could not access this browser’s private app storage. Your connection was not saved.");
    }
    const key = await window.BHFOfflineDB.get("modelSettings", KEY_ID);
    if (key?.cryptoKey) return key.cryptoKey;
    const cryptoKey = await window.crypto.subtle.generateKey(
      {name: "AES-GCM", length: 256}, false, ["encrypt", "decrypt"],
    );
    await window.BHFOfflineDB.put("modelSettings", {id: KEY_ID, cryptoKey});
    return cryptoKey;
  }

  function bytesToBase64(bytes) {
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return btoa(binary);
  }

  function base64ToBytes(value) {
    return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
  }

  function bytesToBase64Url(bytes) {
    return bytesToBase64(bytes).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
  }

  async function encryptToken(token) {
    const key = await ensureKey();
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await window.crypto.subtle.encrypt(
      {name: "AES-GCM", iv}, key, new TextEncoder().encode(token),
    );
    return {iv: bytesToBase64(iv), ciphertext: bytesToBase64(new Uint8Array(encrypted))};
  }

  async function decryptToken(record) {
    if (!record?.ciphertext || !record?.iv || !window.BHFOfflineDB || !window.crypto?.subtle) return null;
    const keyRecord = await window.BHFOfflineDB.get("modelSettings", KEY_ID);
    if (!keyRecord?.cryptoKey) return null;
    try {
      const decrypted = await window.crypto.subtle.decrypt(
        {name: "AES-GCM", iv: base64ToBytes(record.iv)}, keyRecord.cryptoKey, base64ToBytes(record.ciphertext),
      );
      return new TextDecoder().decode(decrypted);
    } catch (_error) {
      return null;
    }
  }

  async function saveTokenValue(token, {completeOnboarding = true} = {}) {
    const encrypted = await encryptToken(token);
    settings.providers = settings.providers || {};
    settings.providers[OPENROUTER] = {
      ...providerState(OPENROUTER),
      token: encrypted,
      model: providerState(OPENROUTER).model || openRouterConfig().defaultModel,
    };
    settings.activeProvider = OPENROUTER;
    settings.onboardingComplete = completeOnboarding;
    settings.setupChoice = "provider";
    openRouterToken = token;
    await writeSettings();
    const form = currentForm();
    if (form && providerInput(form, "adapter")) {
      providerInput(form, "adapter").value = OPENROUTER;
      providerInput(form, "model").value = providerState(OPENROUTER).model;
      renderProviderState(form);
    }
    updateConnectionStatus();
  }

  async function saveManualToken() {
    const form = currentForm();
    const input = form?.querySelector("[data-openrouter-token]")
      || document.querySelector("[data-ai-manual-token]");
    const token = String(input?.value || "").trim();
    if (!token) {
      updateTokenStatus(form, "Enter a key before saving it.");
      return;
    }
    try {
      await saveTokenValue(token);
      input.value = "";
      updateTokenStatus(form, "OpenRouter connected on this device.");
      closeSetup();
    } catch (error) {
      updateTokenStatus(form, friendlyStorageError(error));
    }
  }

  async function removeToken() {
    settings.providers = settings.providers || {};
    delete settings.providers[OPENROUTER];
    if (settings.activeProvider === OPENROUTER) settings.activeProvider = null;
    openRouterToken = null;
    await window.BHFOfflineDB?.remove("modelSettings", KEY_ID);
    await writeSettings();
    updateTokenStatus(currentForm(), "OpenRouter disconnected. No key is stored by BHF.");
    updateConnectionStatus();
  }

  function friendlyStorageError(error) {
    const message = String(error?.message || "");
    return message.includes("private app storage") ? message : "BHF could not save this connection in the browser.";
  }

  async function testConnection() {
    await readyPromise;
    const provider = settings?.activeProvider;
    if (!provider) throw new Error("Choose an AI provider before testing the connection.");
    const isOpenRouter = provider === OPENROUTER;
    if (isOpenRouter && !openRouterToken) throw new Error("OpenRouter is not connected on this device.");
    const state = providerState(provider);
    let response;
    try {
      response = await fetch(`${isOpenRouter ? (openRouterConfig().baseUrl || "https://openrouter.ai/api/v1") : state.baseUrl}/models`, {
        headers: isOpenRouter ? {Authorization: `Bearer ${openRouterToken}`} : {},
        cache: "no-store",
      });
    } catch (_error) {
      throw new Error(isOpenRouter ? "OpenRouter requires an internet connection." : "The local AI endpoint could not be reached. Check that it is running and that the address is correct.");
    }
    if (response.status === 401 || response.status === 403) throw new Error(isOpenRouter ? "The OpenRouter key is invalid or revoked." : "The configured AI service rejected the connection.");
    if (response.status === 429) throw new Error("OpenRouter is rate-limiting requests. Try again shortly.");
    if (!response.ok) throw new Error("OpenRouter is temporarily unavailable. Try again later.");
    const data = await response.json().catch(() => ({}));
    const ids = new Set(Array.isArray(data?.data) ? data.data.map((item) => String(item?.id || "")) : []);
    const selected = state.model;
    if (isOpenRouter && selected && ids.size && !ids.has(selected)) {
      throw new Error("The selected free model is temporarily unavailable. Choose another model or try again.");
    }
    updateConnectionStatus(`${isOpenRouter ? "OpenRouter" : "AI provider"} connection tested successfully`);
    return true;
  }

  function authAttempt() {
    try {
      const raw = sessionStorage.getItem(AUTH_ATTEMPT_KEY);
      sessionStorage.removeItem(AUTH_ATTEMPT_KEY);
      const value = raw ? JSON.parse(raw) : null;
      if (!value || Date.now() - Number(value.createdAt || 0) > AUTH_ATTEMPT_TTL_MS) return null;
      return value;
    } catch (_error) {
      return null;
    }
  }

  function cleanCallbackUrl() {
    const clean = `${window.location.origin}${window.location.pathname}`;
    try { window.history.replaceState({}, document.title, clean); } catch (_error) { /* best effort */ }
  }

  async function handleAuthCallback() {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("code") && !params.has("error") && !params.has("state")) return;
    const attempt = authAttempt();
    cleanCallbackUrl();
    if (params.get("error")) {
      throw new Error(params.get("error") === "access_denied"
        ? "OpenRouter connection was cancelled. No changes were made."
        : "OpenRouter authorization could not be completed. No changes were made.");
    }
    if (!attempt || params.get("state") !== attempt.state) {
      throw new Error("The OpenRouter setup attempt expired or could not be verified. Please try again.");
    }
    const code = params.get("code");
    if (!code) throw new Error("OpenRouter did not return an authorization code. Please try again.");
    const response = await fetch(openRouterConfig().keyExchangeUrl || "https://openrouter.ai/api/v1/auth/keys", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({code, code_verifier: attempt.verifier, code_challenge_method: "S256"}),
      cache: "no-store",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || typeof payload?.key !== "string" || !payload.key) {
      if (response.status === 403) throw new Error("OpenRouter could not verify this setup attempt. Please start again.");
      throw new Error("BHF could not finish the OpenRouter connection. Please try again.");
    }
    await saveTokenValue(payload.key);
    await testConnection().catch((error) => updateConnectionStatus(error.message));
    closeSetup();
  }

  async function connectOpenRouter() {
    const callbackOrigin = window.location.origin;
    const localHttp = window.location.protocol === "http:"
      && ["localhost", "127.0.0.1"].includes(window.location.hostname);
    if (window.location.protocol !== "https:" && !localHttp) {
      throw new Error("OpenRouter setup requires HTTPS on this address. Use the Synology HTTPS address, or open BHF on localhost.");
    }
    if (!window.crypto?.subtle || !window.crypto?.getRandomValues) {
      throw new Error("This browser cannot securely start an OpenRouter connection.");
    }
    let storage;
    try { storage = sessionStorage; } catch (_error) { throw new Error("BHF could not access temporary browser storage. Try a normal browser window."); }
    const verifier = bytesToBase64Url(window.crypto.getRandomValues(new Uint8Array(32)));
    const state = bytesToBase64Url(window.crypto.getRandomValues(new Uint8Array(24)));
    const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
    const challenge = bytesToBase64Url(new Uint8Array(digest));
    const callbackUrl = new URL("/", callbackOrigin);
    // OpenRouter documents callback_url and code, but not a separate state
    // parameter. Put our CSRF state in the callback URL so it comes back with
    // the authorization code and can be checked before exchange.
    callbackUrl.searchParams.set("state", state);
    storage.setItem(AUTH_ATTEMPT_KEY, JSON.stringify({state, verifier, createdAt: Date.now()}));
    const authUrl = new URL(openRouterConfig().authUrl || "https://openrouter.ai/auth");
    authUrl.searchParams.set("callback_url", callbackUrl.href);
    authUrl.searchParams.set("code_challenge", challenge);
    authUrl.searchParams.set("code_challenge_method", "S256");
    window.location.assign(authUrl.href);
  }

  function finishWithoutAi() {
    settings.onboardingComplete = true;
    settings.setupChoice = "without_ai";
    settings.activeProvider = null;
    writeSettings().catch(() => undefined);
    closeSetup();
  }

  function showSetup(message = "") {
    const dialog = document.querySelector("[data-ai-setup]");
    if (!dialog) return;
    const status = dialog.querySelector("[data-ai-setup-status]");
    if (status) status.textContent = message;
    if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
    else dialog.hidden = false;
  }

  function closeSetup() {
    const dialog = document.querySelector("[data-ai-setup]");
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    dialog.hidden = true;
  }

  async function initialize() {
    await readSettings();
    openRouterToken = await decryptToken(settings.providers?.[OPENROUTER]?.token);
    const form = currentForm();
    if (form && settings.activeProvider && settings.providers?.[settings.activeProvider]) {
      providerInput(form, "adapter").value = settings.activeProvider;
      const saved = providerState(settings.activeProvider);
      if (providerInput(form, "model")) providerInput(form, "model").value = saved.model;
      if (providerInput(form, "base_url")) providerInput(form, "base_url").value = saved.baseUrl;
    }
    renderProviderState(form);
    document.querySelectorAll("[data-openrouter-connect]").forEach((button) => button.addEventListener("click", () => {
      connectOpenRouter().catch((error) => showSetup(error.message));
    }));
    document.querySelectorAll("[data-ai-continue-without]").forEach((button) => button.addEventListener("click", finishWithoutAi));
    document.querySelectorAll("[data-ai-local-provider]").forEach((button) => button.addEventListener("click", () => {
      if (form && providerInput(form, "adapter")) {
        providerInput(form, "adapter").value = "ollama";
        renderProviderState(form);
      }
      settings.activeProvider = "ollama";
      settings.onboardingComplete = true;
      settings.setupChoice = "provider";
      writeSettings().catch(() => undefined);
      closeSetup();
    }));
    document.querySelectorAll("[data-ai-other-provider]").forEach((button) => button.addEventListener("click", () => {
      if (form && providerInput(form, "adapter")) {
        providerInput(form, "adapter").value = "openai_compatible";
        renderProviderState(form);
      }
      settings.activeProvider = "openai_compatible";
      settings.onboardingComplete = true;
      settings.setupChoice = "provider";
      writeSettings().catch(() => undefined);
      closeSetup();
    }));
    document.querySelectorAll("[data-ai-manual-save]").forEach((button) => button.addEventListener("click", () => saveManualToken()));
    document.querySelectorAll("[data-ai-manual-dialog-save]").forEach((button) => button.addEventListener("click", () => saveManualToken()));
    document.querySelectorAll("[data-ai-test-connection]").forEach((button) => button.addEventListener("click", () => {
      testConnection().catch((error) => updateConnectionStatus(error.message));
    }));
    document.querySelectorAll("[data-ai-reconnect]").forEach((button) => button.addEventListener("click", () => connectOpenRouter().catch((error) => showSetup(error.message))));
    document.querySelectorAll("[data-ai-disconnect]").forEach((button) => button.addEventListener("click", () => removeToken().catch((error) => updateConnectionStatus(friendlyStorageError(error)))));
    document.querySelectorAll("[data-ai-settings-open]").forEach((button) => button.addEventListener("click", () => showSetup()));
    if (form) {
      providerInput(form, "adapter")?.addEventListener("change", async () => {
        updateSettingsFromForm(form);
        renderProviderState(form);
        await writeSettings();
      });
      form.querySelector("[data-openrouter-model]")?.addEventListener("change", () => {
        const custom = form.querySelector("[data-openrouter-custom-model]");
        if (custom) custom.hidden = providerInput(form, "model")?.value !== "__custom__";
        const model = providerInput(form, "model");
        const selected = form.querySelector("[data-openrouter-model]");
        if (selected?.value === "__custom__") {
          if (custom) custom.hidden = false;
          if (model) {
            model.hidden = false;
            model.value = custom?.value || "";
          }
        } else if (selected && model) {
          model.hidden = true;
          model.value = selected.value;
        }
      });
      form.querySelector("[data-openrouter-custom-model]")?.addEventListener("input", (event) => {
        const model = providerInput(form, "model");
        const selected = form.querySelector("[data-openrouter-model]");
        if (selected?.value === "__custom__" && model) model.value = event.target.value;
      });
      form.addEventListener("change", () => persistFormSettings().catch(() => undefined));
    }
    try {
      await handleAuthCallback();
    } catch (error) {
      showSetup(error.message);
    }
    if (!settings.onboardingComplete) showSetup();
  }

  readyPromise = initialize().catch((error) => {
    settings = defaultSettings();
    showSetup(friendlyStorageError(error));
  });

  window.BHFModelSettings = {
    getProviderHeaders: async () => {
      await readyPromise;
      if (!settings?.onboardingComplete || !settings.activeProvider) {
        const error = new Error("Set up an AI provider before asking BHF.");
        error.code = "setup_required";
        showSetup("Choose an AI provider to ask BHF.");
        throw error;
      }
      if (settings.activeProvider !== OPENROUTER) return {};
      if (!openRouterToken) {
        const error = new Error("OpenRouter is not connected on this device.");
        error.code = "setup_required";
        showSetup(error.message);
        throw error;
      }
      return {"X-BHF-OpenRouter-Key": openRouterToken};
    },
    persistFormSettings,
    openSetup: showSetup,
    ready: () => readyPromise,
  };
})();
