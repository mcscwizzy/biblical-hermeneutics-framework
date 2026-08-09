(() => {
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));
  const request = async (url) => {
    const response = await fetch(url, {headers: {Accept: "application/json"}});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load archaeology.");
    return payload;
  };
  const render = (results) => {
    const container = $("[data-archaeology-results]");
    if (!container) return;
    if (!results.length) { container.innerHTML = '<p class="empty">No archaeology evidence matches these filters.</p>'; return; }
    container.innerHTML = results.map((item) => {
      const media = item.primary_media || {};
      const image = media.thumbnail_url || media.image_url;
      return `<button class="archaeology-card" data-archaeology-id="${escapeHtml(item.id)}">${image ? `<img src="${escapeHtml(image)}" alt="" loading="lazy">` : '<div class="archaeology-card-image archaeology-card-image--empty">No reviewed image</div>'}<span class="canonical-browser-kicker">${escapeHtml(item.item_type)}</span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.period)}${item.site_name ? ` · ${escapeHtml(item.site_name)}` : ""}</small></button>`;
    }).join("");
    container.querySelectorAll("[data-archaeology-id]").forEach((button) => button.addEventListener("click", () => showDetail(button.dataset.archaeologyId)));
  };
  const showDetail = async (id) => {
    const dialog = $("[data-archaeology-detail]"); const body = $("[data-archaeology-detail-body]");
    if (!dialog || !body) return;
    body.innerHTML = '<p class="empty">Loading archaeology evidence…</p>'; dialog.showModal();
    try {
      const item = await request(`/api/archaeology/items/${encodeURIComponent(id)}`);
      const details = item.evidence_details || {}; const media = (item.media || [])[0] || {}; const image = media.image_url || media.thumbnail_url;
      const passages = (item.related_passages || item.scripture_links || []).map((link) => `${link.book} ${link.chapter}:${link.verse_start}${link.verse_end !== link.verse_start ? `-${link.verse_end}` : ""}`).join(", ") || "None recorded";
      const related = (item.related_ckl || []).map((link) => `<a href="/?canonical=${encodeURIComponent(link.ckl_object_id)}">${escapeHtml(link.ckl_object_id)}</a>`).join(", ") || "None recorded";
      body.innerHTML = `${image ? `<img class="archaeology-detail-image" src="${escapeHtml(image)}" alt="${escapeHtml(media.caption || item.name)}">` : ""}<p class="canonical-browser-kicker">Archaeology evidence</p><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(details.description || item.why_it_matters)}</p><dl class="archaeology-detail-grid"><dt>What it is</dt><dd>${escapeHtml(item.item_type)}</dd><dt>Period / date</dt><dd>${escapeHtml(details.date_display || item.period)}</dd><dt>Discovery</dt><dd>${escapeHtml(details.discovery_context || "Not recorded")}</dd><dt>Physical evidence</dt><dd>${escapeHtml(details.physical_description || "Not recorded")}</dd><dt>Biblical relevance</dt><dd>${escapeHtml(details.biblical_relevance || item.why_it_matters)}</dd><dt>Archaeological caution</dt><dd>${escapeHtml(details.interpretive_caution || item.bhf_caution || "None recorded")}</dd><dt>Related Scripture</dt><dd>${escapeHtml(passages)}</dd><dt>Related CKL knowledge</dt><dd>${related}</dd><dt>Image attribution</dt><dd>${escapeHtml(media.attribution_text || media.institution || "No image selected")}</dd><dt>Image license</dt><dd>${escapeHtml(media.license_id || "Not recorded")}</dd></dl>${item.site_id ? `<a class="secondary" href="/api/archaeology/sites/${encodeURIComponent(item.site_id)}">View site data / map coordinates</a>` : ""}`;
    } catch (error) { body.innerHTML = `<p class="empty">${escapeHtml(error.message)}</p>`; }
  };
  const load = async () => { const form = $("[data-archaeology-search]"); const summary = $("[data-archaeology-summary]"); const params = new URLSearchParams(new FormData(form)); for (const [key, value] of [...params]) if (!String(value).trim()) params.delete(key); const data = await request(`/api/archaeology?${params}`); summary.textContent = `${data.count} archaeology record${data.count === 1 ? "" : "s"} found.`; render(data.results || []); };
  document.addEventListener("DOMContentLoaded", () => { const form = $("[data-archaeology-search]"); form?.addEventListener("submit", (event) => { event.preventDefault(); load().catch((error) => { $("[data-archaeology-summary]").textContent = error.message; }); }); $("[data-archaeology-clear]")?.addEventListener("click", () => { form.reset(); load(); }); $("[data-archaeology-close]")?.addEventListener("click", () => $("[data-archaeology-detail]")?.close()); load().catch((error) => { $("[data-archaeology-results]").textContent = error.message; }); });
})();
