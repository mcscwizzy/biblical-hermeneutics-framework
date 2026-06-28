const POLL_INTERVAL_MS = 750;

document.addEventListener("submit", async function (event) {
  const form = event.target;
  if (!form.matches("[data-job-post]")) {
    return;
  }

  event.preventDefault();

  const answerPanel = document.querySelector(form.dataset.target);
  const statusPanel = document.querySelector(form.dataset.statusTarget);
  const submitButton = form.querySelector("button[type='submit']");
  if (!answerPanel || !statusPanel) {
    form.submit();
    return;
  }

  setRunning(form, submitButton, true);
  resetStatus(statusPanel);
  answerPanel.innerHTML = "<p class=\"empty\">The agent is running. Status updates will appear above.</p>";
  answerPanel.setAttribute("aria-busy", "true");

  try {
    const createResponse = await fetch(form.dataset.jobPost, {
      method: "POST",
      body: new FormData(form),
      headers: { "Accept": "application/json" }
    });
    const job = await createResponse.json();
    if (!createResponse.ok || !job.job_id) {
      throw new Error(job.error || "Could not start request.");
    }

    const finalStatus = await pollJob(form, statusPanel, job.job_id);
    const resultResponse = await fetch(form.dataset.resultBase + finalStatus.job_id);
    answerPanel.innerHTML = await resultResponse.text();
  } catch (error) {
    markStatusFailed(statusPanel, error.message || "Request failed.");
    answerPanel.innerHTML = errorHtml(error.message || "Request failed.");
  } finally {
    answerPanel.removeAttribute("aria-busy");
    setRunning(form, submitButton, false);
  }
});

async function pollJob(form, statusPanel, jobId) {
  while (true) {
    const response = await fetch(form.dataset.statusBase + jobId, {
      headers: { "Accept": "application/json" }
    });
    const status = await response.json();
    if (!response.ok) {
      throw new Error(status.error || "Could not read request status.");
    }

    renderStatus(statusPanel, status);
    if (status.done) {
      return status;
    }
    await delay(POLL_INTERVAL_MS);
  }
}

function resetStatus(statusPanel) {
  statusPanel.hidden = false;
  statusPanel.classList.remove("complete", "failed");
  statusPanel.querySelector(".status-current").textContent = "Preparing request";
  statusPanel.querySelector(".status-history").innerHTML = "";
}

function renderStatus(statusPanel, status) {
  statusPanel.hidden = false;
  statusPanel.classList.toggle("complete", Boolean(status.done && !status.error));
  statusPanel.classList.toggle("failed", Boolean(status.error));
  statusPanel.querySelector(".status-current").textContent = status.error
    ? "Failed"
    : status.message;

  const history = statusPanel.querySelector(".status-history");
  history.innerHTML = "";
  for (const entry of status.history || []) {
    const item = document.createElement("li");
    item.textContent = entry.message;
    item.dataset.stage = entry.stage;
    history.appendChild(item);
  }
}

function markStatusFailed(statusPanel, message) {
  statusPanel.hidden = false;
  statusPanel.classList.remove("complete");
  statusPanel.classList.add("failed");
  statusPanel.querySelector(".status-current").textContent = "Failed";
  const history = statusPanel.querySelector(".status-history");
  const item = document.createElement("li");
  item.textContent = `Failed: ${message}`;
  item.dataset.stage = "failed";
  history.appendChild(item);
}

function setRunning(form, submitButton, running) {
  form.setAttribute("aria-busy", running ? "true" : "false");
  if (submitButton) {
    submitButton.disabled = running;
    submitButton.textContent = running ? "Asking BHF..." : "Ask BHF";
  }
}

function errorHtml(message) {
  const escaped = escapeHtml(message);
  return `<div class="error" role="alert"><h2>Could not ask BHF</h2><p>${escaped}</p></div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
