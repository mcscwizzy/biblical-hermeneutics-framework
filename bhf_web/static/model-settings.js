(function () {
  const SETTINGS_ID = "model-settings";
  const KEY_ID = "model-settings-key";
  const OPENROUTER = "openrouter";
  const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";

  let settings = null;
  let openRouterToken = null;
  let readyPromise = null;

  function defaultSettings() {
    return {
      id: SETTINGS_ID,
      activeProvider: null,
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
    if (provider === OPENROUTER) {
      return {
        baseUrl: OPENROUTER_BASE_URL,
        model: "openai/gpt-4o-mini",
      };
    }
    if (provider === "ollama") {
      return {
        baseUrl: "http://localhost:11434",
        model: "llama3.1:8b",
      };
    }
    return {
      baseUrl: "http://localhost:11434/v1",
      model: "llama3.1:8b",
    };
  }

  function providerState(provider) {
    const saved = settings?.providers?.[provider];
    return {
      ...providerDefaults(provider),
      ...(saved && typeof saved === "object" ? saved : {}),
    };
  }

  async function readSettings() {
    if (!window.BHFOfflineDB) {
      return defaultSettings();
    }
    return (await window.BHFOfflineDB.get("modelSettings", SETTINGS_ID)) || defaultSettings();
  }

  async function writeSettings() {
    if (!window.BHFOfflineDB) {
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
    settings.providers = settings.providers || {};
    settings.providers[provider] = {
      ...providerState(provider),
      model: providerInput(form, "model")?.value || providerState(provider).model,
      baseUrl: providerInput(form, "base_url")?.value || providerState(provider).baseUrl,
    };
  }

  async function persistFormSettings() {
    updateSettingsFromForm();
    await writeSettings();
  }

  function renderProviderState(form = currentForm()) {
    if (!form) {
      return;
    }
    const provider = currentProvider(form);
    const saved = providerState(provider);
    const model = providerInput(form, "model");
    const baseUrl = providerInput(form, "base_url");
    if (model && !model.value) {
      model.value = saved.model;
    }
    if (baseUrl) {
      if (provider === OPENROUTER) {
        baseUrl.value = OPENROUTER_BASE_URL;
        baseUrl.readOnly = true;
      } else {
        baseUrl.readOnly = false;
        if (!baseUrl.value || baseUrl.dataset.modelSettingsManaged === "true") {
          baseUrl.value = saved.baseUrl;
        }
      }
      baseUrl.dataset.modelSettingsManaged = "true";
    }
    const credentialPanel = form.querySelector("[data-openrouter-credential]");
    if (credentialPanel) {
      credentialPanel.hidden = provider !== OPENROUTER;
    }
    const privacyNote = form.querySelector("[data-openrouter-privacy]");
    if (privacyNote) {
      privacyNote.hidden = provider !== OPENROUTER;
    }
    updateTokenStatus(form);
  }

  function updateTokenStatus(form = currentForm(), message = "") {
    const status = form?.querySelector("[data-openrouter-token-status]");
    if (!status) {
      return;
    }
    if (message) {
      status.textContent = message;
      return;
    }
    status.textContent = openRouterToken ? "Token saved on this device." : "No token saved.";
  }

  async function ensureKey() {
    if (!window.crypto?.subtle || !window.BHFOfflineDB) {
      throw new Error("This browser cannot securely store an OpenRouter token.");
    }
    let key = await window.BHFOfflineDB.get("modelSettings", KEY_ID);
    if (key?.cryptoKey) {
      return key.cryptoKey;
    }
    const cryptoKey = await window.crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
    await window.BHFOfflineDB.put("modelSettings", { id: KEY_ID, cryptoKey });
    return cryptoKey;
  }

  function bytesToBase64(bytes) {
    let binary = "";
    for (const byte of bytes) {
      binary += String.fromCharCode(byte);
    }
    return btoa(binary);
  }

  function base64ToBytes(value) {
    return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
  }

  async function encryptToken(token) {
    const key = await ensureKey();
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      key,
      new TextEncoder().encode(token),
    );
    return {
      iv: bytesToBase64(iv),
      ciphertext: bytesToBase64(new Uint8Array(encrypted)),
    };
  }

  async function decryptToken(record) {
    if (!record?.ciphertext || !record?.iv || !window.BHFOfflineDB) {
      return null;
    }
    const keyRecord = await window.BHFOfflineDB.get("modelSettings", KEY_ID);
    if (!keyRecord?.cryptoKey) {
      return null;
    }
    try {
      const decrypted = await window.crypto.subtle.decrypt(
        { name: "AES-GCM", iv: base64ToBytes(record.iv) },
        keyRecord.cryptoKey,
        base64ToBytes(record.ciphertext),
      );
      return new TextDecoder().decode(decrypted);
    } catch (_error) {
      return null;
    }
  }

  async function saveToken() {
    const form = currentForm();
    const input = form?.querySelector("[data-openrouter-token]");
    const token = String(input?.value || "").trim();
    if (!token) {
      updateTokenStatus(form, "Enter a token before saving.");
      return;
    }
    const encrypted = await encryptToken(token);
    settings.providers = settings.providers || {};
    settings.providers[OPENROUTER] = {
      ...providerState(OPENROUTER),
      token: encrypted,
    };
    openRouterToken = token;
    await writeSettings();
    input.value = "";
    updateTokenStatus(form, "Token saved on this device.");
  }

  async function removeToken() {
    settings.providers = settings.providers || {};
    const provider = providerState(OPENROUTER);
    delete provider.token;
    settings.providers[OPENROUTER] = provider;
    openRouterToken = null;
    await writeSettings();
    updateTokenStatus(currentForm(), "Token removed from this device.");
  }

  async function getProviderHeaders() {
    await readyPromise;
    const provider = currentProvider();
    if (provider !== OPENROUTER) {
      return {};
    }
    if (!openRouterToken) {
      throw new Error("Save an OpenRouter API token in Model settings first.");
    }
    return { "X-BHF-OpenRouter-Key": openRouterToken };
  }

  async function initialize() {
    settings = await readSettings();
    const form = currentForm();
    const savedProvider = settings.activeProvider;
    if (form && savedProvider && settings.providers?.[savedProvider] && providerInput(form, "adapter")) {
      providerInput(form, "adapter").value = savedProvider;
      const saved = providerState(savedProvider);
      if (providerInput(form, "model")) {
        providerInput(form, "model").value = saved.model;
      }
      if (providerInput(form, "base_url")) {
        providerInput(form, "base_url").value = saved.baseUrl;
      }
    }
    openRouterToken = await decryptToken(settings.providers?.[OPENROUTER]?.token);
    renderProviderState(form);
    if (form) {
      providerInput(form, "adapter")?.addEventListener("change", async () => {
        updateSettingsFromForm(form);
        const provider = currentProvider(form);
        const saved = providerState(provider);
        if (providerInput(form, "model")) providerInput(form, "model").value = saved.model;
        if (providerInput(form, "base_url")) providerInput(form, "base_url").value = saved.baseUrl;
        renderProviderState(form);
        await writeSettings();
      });
      form.querySelector("[data-openrouter-token-save]")?.addEventListener("click", () => {
        saveToken().catch((error) => updateTokenStatus(form, error.message));
      });
      form.querySelector("[data-openrouter-token-remove]")?.addEventListener("click", () => {
        removeToken().catch((error) => updateTokenStatus(form, error.message));
      });
      form.addEventListener("change", () => {
        persistFormSettings().catch(() => {});
      });
    }
  }

  readyPromise = initialize().catch(() => {
    settings = defaultSettings();
  });

  window.BHFModelSettings = {
    getProviderHeaders,
    persistFormSettings,
    ready: () => readyPromise,
  };
})();
