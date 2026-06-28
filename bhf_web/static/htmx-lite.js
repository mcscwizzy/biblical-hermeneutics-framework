const POLL_INTERVAL_MS = 750;
const WAITING_MESSAGE_BASE_DELAY_MS = 3000;
const WAITING_MESSAGE_JITTER_MS = 900;
const WAITING_MESSAGES = [
  "Consulting the scrolls...",
  "Parting the data sea...",
  "Gathering manna packets...",
  "Counting the begats...",
  "Sharpening the sword...",
  "Lighting the lampstand...",
  "Dusting off the tablets...",
  "Wrestling the context angel...",
  "Summoning the Bereans...",
  "Checking the prophets...",
  "Cross-referencing the scrolls...",
  "Feeding the five queries...",
  "Multiplying the insights...",
  "Walking through the wilderness...",
  "Circling Jericho...",
  "Sounding the tiny trumpet...",
  "Building the ark cache...",
  "Sorting clean and unclean data...",
  "Calibrating the ephod...",
  "Tuning the psaltery...",
  "Plucking the harp strings...",
  "Reading the fine papyrus...",
  "Unrolling Isaiah...",
  "Decoding Daniel...",
  "Pondering in the heart...",
  "Seeking wisdom from Proverbs...",
  "Chasing Ecclesiastes vibes...",
  "Loading Lamentations responsibly...",
  "Avoiding Job’s friends...",
  "Checking the original audience...",
  "Hermeneuticizing the heavens...",
  "Exegeting the electrons...",
  "Sanctifying the syntax...",
  "Baptizing the breadcrumbs...",
  "Anointing the answer...",
  "Blessing the backend...",
  "Rebuking hallucinations...",
  "Casting out bad context...",
  "Binding loose assumptions...",
  "Loosing fresh insights...",
  "Rightly dividing the response...",
  "Testing every spirit...",
  "Weighing the witnesses...",
  "Marching around the thesis...",
  "Gathering twelve baskets...",
  "Waiting on the answer...",
  "Praying over the payload...",
  "Turning water into output...",
  "Ascending the context mountain...",
  "Calling the Schwartz of Solomon...",
];

let waitingTimerId = null;
let waitingMessageIndex = 0;
let latestStatus = null;

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
  startWaiting(statusPanel);
  answerPanel.innerHTML = "";
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

    if (finalStatus.error || !resultResponse.ok) {
      markStatusFailed(statusPanel, finalStatus.error || "Request failed.");
    } else {
      markStatusComplete(statusPanel, finalStatus);
    }
  } catch (error) {
    markStatusFailed(statusPanel, error.message || "Request failed.");
    answerPanel.innerHTML = errorHtml(error.message || "Request failed.");
  } finally {
    stopWaiting();
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
  latestStatus = null;
  waitingMessageIndex = 0;
  statusPanel.hidden = false;
  statusPanel.classList.remove("complete", "failed");
  statusPanel.querySelector(".status-active").hidden = false;
  statusPanel.querySelector(".status-summary").hidden = true;
  statusPanel.querySelector(".status-summary").textContent = "";
  statusPanel.querySelector(".status-current").textContent = "Preparing request";
}

function renderStatus(statusPanel, status) {
  latestStatus = status;
  statusPanel.hidden = false;
  statusPanel.classList.toggle("failed", Boolean(status.error || status.status === "error"));
  statusPanel.classList.toggle("complete", Boolean(status.done && !status.error));
  if (status.error || status.status === "error") {
    statusPanel.querySelector(".status-current").textContent = "Failed";
  } else if (status.done) {
    statusPanel.querySelector(".status-current").textContent = status.message;
  }
}

function startWaiting(statusPanel) {
  stopWaiting();
  setWaitingMessage(statusPanel);
  scheduleNextWaitingMessage(statusPanel);
}

function stopWaiting() {
  if (waitingTimerId !== null) {
    window.clearTimeout(waitingTimerId);
    waitingTimerId = null;
  }
}

function setWaitingMessage(statusPanel) {
  const current = statusPanel.querySelector(".status-current");
  if (!current) {
    return;
  }
  current.textContent = WAITING_MESSAGES[waitingMessageIndex % WAITING_MESSAGES.length];
  waitingMessageIndex += 1;
}

function scheduleNextWaitingMessage(statusPanel) {
  waitingTimerId = window.setTimeout(() => {
    setWaitingMessage(statusPanel);
    if (!latestStatus || !latestStatus.done) {
      scheduleNextWaitingMessage(statusPanel);
    }
  }, randomWaitingDelay());
}

function randomWaitingDelay() {
  const jitter = Math.floor((Math.random() * 2 - 1) * WAITING_MESSAGE_JITTER_MS);
  return WAITING_MESSAGE_BASE_DELAY_MS + jitter;
}

function markStatusComplete(statusPanel, status) {
  stopWaiting();
  const elapsed = Number(status.elapsed_total_seconds || 0);
  statusPanel.classList.remove("failed");
  statusPanel.classList.add("complete");
  statusPanel.querySelector(".status-active").hidden = true;
  const summary = statusPanel.querySelector(".status-summary");
  summary.hidden = false;
  summary.textContent = `Complete - finished in ${formatSeconds(elapsed)}`;
}

function markStatusFailed(statusPanel, message) {
  stopWaiting();
  statusPanel.hidden = false;
  statusPanel.classList.remove("complete");
  statusPanel.classList.add("failed");
  statusPanel.querySelector(".status-active").hidden = false;
  statusPanel.querySelector(".status-summary").hidden = true;
  statusPanel.querySelector(".status-current").textContent = "Failed";
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

function formatSeconds(value) {
  const seconds = Math.max(0, Number(value) || 0);
  return `${seconds.toFixed(1)}s`;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
