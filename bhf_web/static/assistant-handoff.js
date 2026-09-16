(function () {
  function formatReference(selection) {
    const selectedReference = String(selection?.reference || "").trim();
    if (selectedReference) return selectedReference;

    const book = String(selection?.book || "").trim();
    const chapter = String(selection?.chapter || "").trim();
    return [book, chapter].filter(Boolean).join(" ");
  }

  function buildHandoffText({reference, question}) {
    const trimmedQuestion = String(question || "").trim();
    if (!trimmedQuestion) {
      throw new Error("Please enter a question before opening BHF.");
    }
    return `I'm studying ${String(reference || "").trim()} in the Biblical Hermeneutics Framework (BHF).\n\nMy question:\n${trimmedQuestion}`;
  }

  function create(options = {}) {
    const dialog = options.dialog;
    const referenceNode = options.reference;
    const questionNode = options.question;
    const preparedNode = options.prepared;
    const statusNode = options.status;
    const primaryButton = options.primary;
    const manualCopyButton = options.manualCopy;
    const openFallback = options.openFallback;
    const getSelection = options.getSelection || (() => ({}));
    const assistantUrl = String(
      options.assistantUrl || window.BHFRuntimeConfig?.assistantUrl || "",
    ).trim();
    const openWindow = options.openWindow || ((...args) => window.open(...args));
    const writeClipboard = options.writeClipboard || ((text) => {
      if (!navigator.clipboard?.writeText) {
        return Promise.reject(new Error("Clipboard unavailable"));
      }
      return navigator.clipboard.writeText(text);
    });
    let selection = null;

    function setStatus(message) {
      if (statusNode) statusNode.textContent = message;
    }

    function setPrepared(text) {
      if (!preparedNode) return;
      preparedNode.value = text;
      preparedNode.textContent = text;
    }

    function showOpenFallback() {
      if (!openFallback) return;
      openFallback.href = assistantUrl;
      openFallback.hidden = false;
    }

    function prepare() {
      selection = selection || getSelection() || {};
      const text = buildHandoffText({
        reference: formatReference(selection),
        question: questionNode?.value,
      });
      setPrepared(text);
      return text;
    }

    function open() {
      selection = getSelection() || {};
      const reference = formatReference(selection);
      if (referenceNode) referenceNode.textContent = reference;
      if (openFallback) {
        openFallback.href = assistantUrl;
        openFallback.hidden = true;
      }
      setStatus("");
      if (typeof dialog?.showModal === "function" && !dialog.open) dialog.showModal();
      else if (dialog) dialog.hidden = false;
      questionNode?.focus?.();
    }

    function close() {
      if (typeof dialog?.close === "function" && dialog.open) dialog.close();
      else if (dialog) dialog.hidden = true;
    }

    async function copy(text) {
      try {
        await writeClipboard(text);
        return true;
      } catch (_error) {
        if (manualCopyButton) manualCopyButton.hidden = false;
        setStatus("BHF could not copy your question. Copy the prepared question manually, then open BHF.");
        preparedNode?.focus?.();
        preparedNode?.select?.();
        return false;
      }
    }

    async function handlePrimaryClick(event) {
      event?.preventDefault?.();
      let text;
      try {
        text = prepare();
      } catch (error) {
        setStatus(error.message);
        questionNode?.focus?.();
        return;
      }

      const popup = assistantUrl
        ? openWindow(assistantUrl, "_blank", "noopener,noreferrer")
        : null;
      if (!popup) showOpenFallback();
      const copied = await copy(text);
      if (copied) {
        setStatus(popup
          ? "Question copied. BHF is open in a new tab."
          : "Question copied. Use Open BHF to continue.");
      }
    }

    async function handleManualCopy(event) {
      event?.preventDefault?.();
      let text = preparedNode?.value || "";
      if (!text) {
        try {
          text = prepare();
        } catch (error) {
          setStatus(error.message);
          questionNode?.focus?.();
          return;
        }
      }
      if (await copy(text)) setStatus("Question copied. You can now open BHF.");
    }

    primaryButton?.addEventListener?.("click", handlePrimaryClick);
    manualCopyButton?.addEventListener?.("click", handleManualCopy);

    return {open, close, prepare};
  }

  window.BHFAssistantHandoff = {
    formatReference,
    buildHandoffText,
    create,
  };
}());
