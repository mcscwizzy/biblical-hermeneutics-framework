(function () {
  const VAULT_FORMAT = "bhf-study-vault";
  const VAULT_VERSION = 1;
  const VAULT_FILE_NAME = "bhf-study-vault.bhfvault";
  const PBKDF2_ITERATIONS = 310000;
  const TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token";
  const AUTHORIZE_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize";
  const GRAPH_ROOT = "https://graph.microsoft.com/v1.0";
  const SETTINGS_ID = "study-vault-settings";
  const SETTINGS_KEY_ID = "study-vault-device-key";
  const CLOUDKIT_SCRIPT_URL = "https://cdn.apple-cloudkit.com/ck/2/CloudKit.js";
  const CLOUDKIT_RECORD_NAME = "bhf-study-vault";
  const CLOUDKIT_RECORD_TYPE = "StudyVault";
  let cloudKitConfigured = false;

  window.addEventListener("load", () => {
    wireVaultControls();
    completeOneDriveAuthorization().catch((error) => setVaultStatus(error.message, "Retry"));
    refreshProviderState();
  });

  function runtimeConfig() {
    return window.BHFRuntimeConfig?.studyVault || {};
  }

  function offlineDb() {
    return window.BHFOfflineDB;
  }

  function supported() {
    return Boolean(offlineDb()?.exportSnapshot && offlineDb()?.mergeSnapshot && window.crypto?.subtle);
  }

  function bytesToBase64(bytes) {
    let value = "";
    for (const byte of bytes) value += String.fromCharCode(byte);
    return btoa(value);
  }

  function base64ToBytes(value) {
    return Uint8Array.from(atob(String(value || "")), (character) => character.charCodeAt(0));
  }

  function safeFileDate() {
    return new Date().toISOString().slice(0, 10);
  }

  function setButtonState(button, message, label, busy) {
    if (!button) return;
    const key = button.dataset.vaultStatus;
    const labelKey = button.dataset.vaultLabel;
    const scope = button.closest(".reader-setting-action")?.parentElement || document;
    const status = key ? scope.querySelector(`[data-${key}]`) : null;
    const value = labelKey ? scope.querySelector(`[data-${labelKey}]`) : null;
    if (status) status.textContent = message;
    if (value) value.textContent = label;
    button.disabled = Boolean(busy);
  }

  function setVaultStatus(message, label = "Ready") {
    document.querySelectorAll("[data-study-vault-status]").forEach((node) => { node.textContent = message; });
    document.querySelectorAll("[data-study-vault-label]").forEach((node) => { node.textContent = label; });
  }

  function requestPassphrase({ confirmation = false } = {}) {
    const dialog = document.querySelector("[data-study-vault-passphrase-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") {
      return Promise.reject(new Error("This browser cannot securely collect a study-vault passphrase."));
    }
    const form = dialog.querySelector("form");
    const input = dialog.querySelector("[data-study-vault-passphrase]");
    const confirmationField = dialog.querySelector("[data-study-vault-passphrase-confirm-field]");
    const repeat = dialog.querySelector("input[data-study-vault-passphrase-confirm]");
    const error = dialog.querySelector("[data-study-vault-passphrase-error]");
    const cancel = dialog.querySelector("[data-study-vault-passphrase-cancel]");
    confirmationField.hidden = !confirmation;
    repeat.required = confirmation;
    input.value = "";
    repeat.value = "";
    error.textContent = "";
    return new Promise((resolve) => {
      const finish = (value) => {
        form.removeEventListener("submit", submit);
        cancel.removeEventListener("click", cancelDialog);
        dialog.removeEventListener("cancel", cancelDialog);
        if (dialog.open) dialog.close();
        resolve(value);
      };
      const cancelDialog = (event) => {
        event?.preventDefault();
        finish(null);
      };
      const submit = (event) => {
        event.preventDefault();
        if (input.value.length < 12) {
          error.textContent = "Use a passphrase with at least 12 characters.";
          return;
        }
        if (confirmation && input.value !== repeat.value) {
          error.textContent = "Passphrases did not match.";
          return;
        }
        finish(input.value);
      };
      form.addEventListener("submit", submit);
      cancel.addEventListener("click", cancelDialog);
      dialog.addEventListener("cancel", cancelDialog);
      dialog.showModal();
      input.focus();
    });
  }

  async function deriveVaultKey(passphrase, salt, usages, iterations = PBKDF2_ITERATIONS) {
    const material = await window.crypto.subtle.importKey(
      "raw", new TextEncoder().encode(passphrase), "PBKDF2", false, ["deriveKey"],
    );
    return window.crypto.subtle.deriveKey(
      { name: "PBKDF2", salt, iterations, hash: "SHA-256" },
      material,
      { name: "AES-GCM", length: 256 },
      false,
      usages,
    );
  }

  async function encryptSnapshot(snapshot, passphrase) {
    const salt = window.crypto.getRandomValues(new Uint8Array(16));
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const key = await deriveVaultKey(passphrase, salt, ["encrypt"]);
    const encrypted = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv }, key, new TextEncoder().encode(JSON.stringify(snapshot)),
    );
    return {
      format: VAULT_FORMAT,
      version: VAULT_VERSION,
      encrypted_at: new Date().toISOString(),
      kdf: { name: "PBKDF2", hash: "SHA-256", iterations: PBKDF2_ITERATIONS, salt: bytesToBase64(salt) },
      cipher: { name: "AES-GCM", iv: bytesToBase64(iv), ciphertext: bytesToBase64(new Uint8Array(encrypted)) },
    };
  }

  async function decryptVault(vault, passphrase) {
    if (!vault || vault.format !== VAULT_FORMAT || vault.version !== VAULT_VERSION || !vault.kdf?.salt || !vault.cipher?.iv || !vault.cipher?.ciphertext) {
      throw new Error("This is not a supported encrypted BHF study vault.");
    }
    try {
      const iterations = Number(vault.kdf.iterations);
      if (!Number.isInteger(iterations) || iterations < 100000 || iterations > 1000000) {
        throw new Error("This vault has unsupported encryption settings.");
      }
      const key = await deriveVaultKey(passphrase, base64ToBytes(vault.kdf.salt), ["decrypt"], iterations);
      const decrypted = await window.crypto.subtle.decrypt(
        { name: "AES-GCM", iv: base64ToBytes(vault.cipher.iv) }, key, base64ToBytes(vault.cipher.ciphertext),
      );
      return JSON.parse(new TextDecoder().decode(decrypted));
    } catch (_error) {
      throw new Error("BHF could not open that vault. Check the passphrase and file.");
    }
  }

  function downloadText(value, filename, mimeType) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([value], { type: mimeType }));
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  async function createEncryptedDownload(button) {
    if (!supported()) throw new Error("Encrypted study vaults require IndexedDB and Web Crypto in this browser.");
    const passphrase = await requestPassphrase({ confirmation: true });
    if (!passphrase) return;
    setButtonState(button, "Encrypting vault...", "Working", true);
    try {
      const vault = await encryptSnapshot(await offlineDb().exportSnapshot(), passphrase);
      downloadText(JSON.stringify(vault, null, 2), `bhf-study-vault-${safeFileDate()}.bhfvault`, "application/json");
      setButtonState(button, "Encrypted study vault downloaded", "Export", false);
    } catch (error) {
      setButtonState(button, error.message || "Vault export failed", "Retry", false);
    }
  }

  async function restoreEncryptedVault(file, button) {
    if (!file || !supported()) return;
    const passphrase = await requestPassphrase();
    if (!passphrase) return;
    setButtonState(button, "Opening encrypted vault...", "Working", true);
    try {
      const snapshot = await decryptVault(JSON.parse(await file.text()), passphrase);
      const result = await offlineDb().mergeSnapshot(snapshot);
      const conflictText = result.conflicts.length ? `; ${result.conflicts.length} conflict copy/copies kept` : "";
      setButtonState(button, `${result.imported_count} records merged${conflictText}`, "Import", false);
    } catch (error) {
      setButtonState(button, error.message || "Vault restore failed", "Retry", false);
    }
  }

  function markdownForSnapshot(snapshot) {
    const stores = snapshot.stores || {};
    const notes = Array.isArray(stores.notes) ? stores.notes : [];
    const studies = Array.isArray(stores.savedStudies) ? stores.savedStudies : [];
    const highlights = Array.isArray(stores.highlights) ? stores.highlights : [];
    const heading = `# BHF Studies and Notes\n\nExported ${new Date().toLocaleString()}\n`;
    const noteText = notes.map((note) => `## Note: ${note.book || "General"}${note.chapter ? ` ${note.chapter}` : ""}\n\n${note.body || ""}\n\n${note.selected_text ? `> ${note.selected_text}\n` : ""}`).join("\n");
    const studyText = studies.map((study) => `## ${study.title || "Saved study"}\n\n${study.book || ""} ${study.chapter || ""}${study.start_verse ? `:${study.start_verse}${study.end_verse && study.end_verse !== study.start_verse ? `-${study.end_verse}` : ""}` : ""}\n\n${study.answer || ""}\n\n${study.personal_notes ? `### Personal notes\n\n${study.personal_notes}\n` : ""}`).join("\n");
    const highlightText = highlights.map((highlight) => `- ${highlight.book} ${highlight.chapter}:${highlight.start_verse}${highlight.end_verse !== highlight.start_verse ? `-${highlight.end_verse}` : ""} — ${highlight.selected_text || "highlight"}`).join("\n");
    return `${heading}\n${noteText ? `# Notes\n\n${noteText}\n` : ""}${studyText ? `# Saved studies\n\n${studyText}\n` : ""}${highlightText ? `# Highlights\n\n${highlightText}\n` : ""}`;
  }

  async function shareReadableCopy(button) {
    if (!offlineDb()?.exportSnapshot) throw new Error("Offline records are unavailable.");
    setButtonState(button, "Preparing readable copy...", "Working", true);
    try {
      const markdown = markdownForSnapshot(await offlineDb().exportSnapshot());
      if (navigator.share) {
        await navigator.share({ title: "BHF Studies and Notes", text: markdown });
        setButtonState(button, "Shared a readable copy", "Share", false);
      } else {
        downloadText(markdown, `bhf-studies-notes-${safeFileDate()}.md`, "text/markdown");
        setButtonState(button, "Downloaded readable copy", "Share", false);
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        setButtonState(button, "Share cancelled", "Share", false);
      } else {
        setButtonState(button, error.message || "Share failed", "Retry", false);
      }
    }
  }

  function oneDriveConfigured() {
    return Boolean(runtimeConfig().oneDriveClientId);
  }

  function iCloudConfigured() {
    return Boolean(runtimeConfig().cloudKitContainerIdentifier && runtimeConfig().cloudKitApiToken);
  }

  function oneDriveRedirectUri() {
    return runtimeConfig().oneDriveRedirectUri || `${window.location.origin}${window.location.pathname}`;
  }

  async function deviceKey() {
    const existing = await offlineDb().get("vaultSettings", SETTINGS_KEY_ID);
    if (existing?.cryptoKey) return existing.cryptoKey;
    const cryptoKey = await window.crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
    await offlineDb().put("vaultSettings", { id: SETTINGS_KEY_ID, cryptoKey });
    return cryptoKey;
  }

  async function encryptSetting(value) {
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encrypted = await window.crypto.subtle.encrypt({ name: "AES-GCM", iv }, await deviceKey(), new TextEncoder().encode(JSON.stringify(value)));
    return { iv: bytesToBase64(iv), ciphertext: bytesToBase64(new Uint8Array(encrypted)) };
  }

  async function decryptSetting(value) {
    if (!value?.iv || !value?.ciphertext) return null;
    try {
      const decrypted = await window.crypto.subtle.decrypt({ name: "AES-GCM", iv: base64ToBytes(value.iv) }, await deviceKey(), base64ToBytes(value.ciphertext));
      return JSON.parse(new TextDecoder().decode(decrypted));
    } catch (_error) {
      return null;
    }
  }

  async function connection() {
    const record = await offlineDb().get("vaultSettings", SETTINGS_ID);
    return decryptSetting(record?.value);
  }

  async function saveConnection(value) {
    await offlineDb().put("vaultSettings", { id: SETTINGS_ID, value: await encryptSetting(value) });
  }

  function randomText() {
    return bytesToBase64(window.crypto.getRandomValues(new Uint8Array(32))).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
  }

  async function connectOneDrive() {
    if (!oneDriveConfigured()) throw new Error("OneDrive is not configured on this BHF server yet.");
    const verifier = randomText();
    const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
    const challenge = bytesToBase64(new Uint8Array(digest)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
    const state = randomText();
    sessionStorage.setItem("bhf-study-vault-onedrive", JSON.stringify({ state, verifier }));
    const query = new URLSearchParams({
      client_id: runtimeConfig().oneDriveClientId,
      response_type: "code",
      redirect_uri: oneDriveRedirectUri(),
      response_mode: "query",
      scope: "offline_access Files.ReadWrite.AppFolder",
      state,
      code_challenge: challenge,
      code_challenge_method: "S256",
    });
    window.location.assign(`${AUTHORIZE_ENDPOINT}?${query}`);
  }

  async function tokenRequest(parameters) {
    const response = await fetch(TOKEN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(parameters),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.access_token) throw new Error(data.error_description || "Microsoft did not complete the OneDrive connection.");
    return data;
  }

  async function completeOneDriveAuthorization() {
    const current = new URL(window.location.href);
    const code = current.searchParams.get("code");
    const state = current.searchParams.get("state");
    if (!code || !state || !oneDriveConfigured()) return;
    const pending = JSON.parse(sessionStorage.getItem("bhf-study-vault-onedrive") || "null");
    if (!pending || pending.state !== state) throw new Error("OneDrive connection could not be verified. Please try again.");
    const data = await tokenRequest({
      client_id: runtimeConfig().oneDriveClientId,
      grant_type: "authorization_code",
      code,
      redirect_uri: oneDriveRedirectUri(),
      code_verifier: pending.verifier,
    });
    await saveConnection({
      access_token: data.access_token,
      refresh_token: data.refresh_token || "",
      expires_at: Date.now() + Number(data.expires_in || 3600) * 1000,
    });
    sessionStorage.removeItem("bhf-study-vault-onedrive");
    current.searchParams.delete("code");
    current.searchParams.delete("state");
    current.searchParams.delete("session_state");
    window.history.replaceState({}, "", `${current.pathname}${current.search}${current.hash}`);
    setVaultStatus("OneDrive connected on this device", "Connected");
  }

  async function accessToken() {
    const saved = await connection();
    if (!saved?.access_token) throw new Error("Connect OneDrive before syncing.");
    if (Date.now() < Number(saved.expires_at || 0) - 60_000) return saved.access_token;
    if (!saved.refresh_token) throw new Error("The OneDrive connection expired. Connect it again.");
    const data = await tokenRequest({
      client_id: runtimeConfig().oneDriveClientId,
      grant_type: "refresh_token",
      refresh_token: saved.refresh_token,
      redirect_uri: oneDriveRedirectUri(),
    });
    await saveConnection({
      access_token: data.access_token,
      refresh_token: data.refresh_token || saved.refresh_token,
      expires_at: Date.now() + Number(data.expires_in || 3600) * 1000,
    });
    return data.access_token;
  }

  async function graphFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${await accessToken()}`);
    return fetch(`${GRAPH_ROOT}${path}`, { ...options, headers });
  }

  function oneDriveVaultPath() {
    return `/me/drive/special/approot:/${VAULT_FILE_NAME}:/content`;
  }

  async function syncOneDrive(button) {
    const passphrase = await requestPassphrase();
    if (!passphrase) return;
    setButtonState(button, "Syncing encrypted study vault...", "Working", true);
    try {
      const remote = await graphFetch(oneDriveVaultPath());
      let remoteEtag = "";
      let merged = { imported_count: 0, conflicts: [] };
      if (remote.ok) {
        remoteEtag = remote.headers.get("etag") || "";
        merged = await offlineDb().mergeSnapshot(await decryptVault(JSON.parse(await remote.text()), passphrase));
      } else if (remote.status !== 404) {
        throw new Error(`OneDrive could not read the study vault (HTTP ${remote.status}).`);
      }
      const vault = await encryptSnapshot(await offlineDb().exportSnapshot(), passphrase);
      const headers = { "Content-Type": "application/json" };
      if (remoteEtag) headers["If-Match"] = remoteEtag;
      const uploaded = await graphFetch(oneDriveVaultPath(), { method: "PUT", headers, body: JSON.stringify(vault) });
      if (uploaded.status === 412) throw new Error("Another device updated OneDrive. Sync again to merge safely.");
      if (!uploaded.ok) throw new Error(`OneDrive could not save the study vault (HTTP ${uploaded.status}).`);
      const conflicts = merged.conflicts.length ? `; ${merged.conflicts.length} conflict copy/copies kept` : "";
      setButtonState(button, `${merged.imported_count} records merged and encrypted vault saved${conflicts}`, "Sync", false);
    } catch (error) {
      setButtonState(button, error.message || "OneDrive sync failed", "Retry", false);
    }
  }

  async function loadCloudKit() {
    if (!iCloudConfigured()) throw new Error("iCloud is not configured on this BHF server yet.");
    if (!window.CloudKit) {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = CLOUDKIT_SCRIPT_URL;
        script.onload = resolve;
        script.onerror = () => reject(new Error("Could not load Apple’s CloudKit service."));
        document.head.append(script);
      });
    }
    if (!cloudKitConfigured) {
      const environment = runtimeConfig().cloudKitEnvironment === "development"
        ? window.CloudKit.DEVELOPMENT_ENVIRONMENT
        : window.CloudKit.PRODUCTION_ENVIRONMENT;
      window.CloudKit.configure({
        containers: [{
          containerIdentifier: runtimeConfig().cloudKitContainerIdentifier,
          environment,
          apiTokenAuth: {
            apiToken: runtimeConfig().cloudKitApiToken,
            persist: true,
            signInButton: { id: "study-vault-cloudkit-signin", theme: "medium" },
          },
        }],
      });
      cloudKitConfigured = true;
    }
    return window.CloudKit.getDefaultContainer();
  }

  async function connectICloud() {
    const container = await loadCloudKit();
    const user = await container.setUpAuth();
    if (!user) {
      setVaultStatus("Use the Apple sign-in button, then select Sync iCloud.", "Sign in");
      return null;
    }
    setVaultStatus("iCloud connected. Sync uses your passphrase and encrypted vault.", "Connected");
    const sync = document.querySelector("[data-vault-cloudkit-sync]");
    if (sync) sync.disabled = false;
    return container;
  }

  function cloudKitError(response, fallback) {
    const error = response?.errors?.[0];
    if (!response?.hasErrors) return null;
    const code = String(error?.code || "").toUpperCase();
    if (code === "NOT_FOUND" || code === "UNKNOWN_ITEM") return null;
    return new Error(error?.reason || error?.message || fallback);
  }

  async function syncICloud(button) {
    const passphrase = await requestPassphrase();
    if (!passphrase) return;
    setButtonState(button, "Syncing encrypted study vault...", "Working", true);
    try {
      const container = await connectICloud();
      if (!container) {
        setButtonState(button, "Sign in to iCloud before syncing", "Sign in", false);
        return;
      }
      const database = container.privateCloudDatabase;
      const fetched = await database.fetchRecords(CLOUDKIT_RECORD_NAME);
      const fetchError = cloudKitError(fetched, "iCloud could not read the study vault.");
      if (fetchError) throw fetchError;
      const remoteRecord = fetched.records?.[0] || null;
      let merged = { imported_count: 0, conflicts: [] };
      const remotePayload = remoteRecord?.fields?.payload?.value;
      if (remotePayload) {
        merged = await offlineDb().mergeSnapshot(await decryptVault(JSON.parse(remotePayload), passphrase));
      }
      const vault = await encryptSnapshot(await offlineDb().exportSnapshot(), passphrase);
      const record = {
        recordName: CLOUDKIT_RECORD_NAME,
        recordType: CLOUDKIT_RECORD_TYPE,
        fields: { payload: { value: JSON.stringify(vault) } },
      };
      if (remoteRecord?.recordChangeTag) record.recordChangeTag = remoteRecord.recordChangeTag;
      const saved = await database.saveRecords(record);
      const saveError = cloudKitError(saved, "iCloud could not save the study vault.");
      if (saveError) throw saveError;
      const conflicts = merged.conflicts.length ? `; ${merged.conflicts.length} conflict copy/copies kept` : "";
      setButtonState(button, `${merged.imported_count} records merged and encrypted vault saved${conflicts}`, "Sync", false);
    } catch (error) {
      setButtonState(button, error.message || "iCloud sync failed", "Retry", false);
    }
  }

  async function refreshProviderState() {
    const connect = document.querySelector("[data-vault-onedrive-connect]");
    const sync = document.querySelector("[data-vault-onedrive-sync]");
    const iCloudConnect = document.querySelector("[data-vault-cloudkit-connect]");
    const iCloudSync = document.querySelector("[data-vault-cloudkit-sync]");
    if (!oneDriveConfigured()) {
      if (connect) connect.disabled = true;
      if (sync) sync.disabled = true;
    }
    const saved = await connection().catch(() => null);
    if (saved?.access_token) {
      setVaultStatus("OneDrive connected. Sync uses your passphrase and encrypted vault.", "Connected");
      if (sync) sync.disabled = false;
    } else if (oneDriveConfigured()) {
      setVaultStatus("Connect OneDrive to synchronize encrypted study data.", "Connect");
    }
    if (!iCloudConfigured()) {
      if (iCloudConnect) iCloudConnect.disabled = true;
      if (iCloudSync) iCloudSync.disabled = true;
      if (!oneDriveConfigured()) setVaultStatus("Cloud providers need server setup. Apple Notes and Google Keep use Share copy.", "Set up");
    }
  }

  function wireVaultControls() {
    const exportButton = document.querySelector("[data-study-vault-export]");
    const importButton = document.querySelector("[data-study-vault-import]");
    const importInput = document.querySelector("[data-study-vault-file]");
    const shareButton = document.querySelector("[data-study-vault-share]");
    const connectButton = document.querySelector("[data-vault-onedrive-connect]");
    const syncButton = document.querySelector("[data-vault-onedrive-sync]");
    const iCloudConnectButton = document.querySelector("[data-vault-cloudkit-connect]");
    const iCloudSyncButton = document.querySelector("[data-vault-cloudkit-sync]");
    exportButton?.addEventListener("click", () => createEncryptedDownload(exportButton).catch((error) => setButtonState(exportButton, error.message || "Vault export failed", "Retry", false)));
    importButton?.addEventListener("click", () => importInput?.click());
    importInput?.addEventListener("change", () => {
      const file = importInput.files?.[0];
      if (file) restoreEncryptedVault(file, importButton).catch((error) => setButtonState(importButton, error.message || "Vault restore failed", "Retry", false));
      importInput.value = "";
    });
    shareButton?.addEventListener("click", () => shareReadableCopy(shareButton).catch((error) => setButtonState(shareButton, error.message || "Share failed", "Retry", false)));
    connectButton?.addEventListener("click", () => connectOneDrive().catch((error) => setVaultStatus(error.message, "Retry")));
    syncButton?.addEventListener("click", () => syncOneDrive(syncButton).catch((error) => setButtonState(syncButton, error.message || "OneDrive sync failed", "Retry", false)));
    iCloudConnectButton?.addEventListener("click", () => connectICloud().catch((error) => setVaultStatus(error.message, "Retry")));
    iCloudSyncButton?.addEventListener("click", () => syncICloud(iCloudSyncButton).catch((error) => setButtonState(iCloudSyncButton, error.message || "iCloud sync failed", "Retry", false)));
  }
})();
