/**
 * Timeline progres penanganan Tim Damkar (dipakai halaman Damkar, detail Operator, dan Lacak warga).
 */
(function () {
  const STAGE_ORDER = ["berangkat", "tiba", "pemadaman", "padam"];

  function renderProgressTimeline(el, report) {
    if (!el) return;
    const { escapeHtml, formatDateTimeWIB, resolveMediaUrl } = window.ApiWaspadaUtils;
    const items = (report && report.progress) || [];
    if (!items.length) {
      el.innerHTML = '<p class="form-hint">Belum ada kabar dari Tim Damkar.</p>';
      return;
    }
    el.innerHTML = items
      .map((p) => {
        const src = p.photo_url ? escapeHtml(resolveMediaUrl(p.photo_url)) : "";
        const photo = src
          ? `<a class="progress-photo" href="${src}" target="_blank" rel="noopener"><img src="${src}" alt="Foto lokasi: ${escapeHtml(p.stage_label)}" width="320" height="240" loading="lazy" /></a>`
          : "";
        return `<div class="timeline-item stage-${escapeHtml(p.stage)}">
          <div class="timeline-time">${formatDateTimeWIB(p.created_at)}</div>
          <div class="timeline-note"><strong>${escapeHtml(p.stage_label)}</strong>${p.note ? "<br/>" + escapeHtml(p.note) : ""}</div>
          ${photo}
        </div>`;
      })
      .join("");
  }

  function nextStage(report) {
    const done = new Set(((report && report.progress) || []).map((p) => p.stage));
    return STAGE_ORDER.find((s) => !done.has(s)) || null;
  }

  window.AWProgress = { renderProgressTimeline, nextStage, STAGE_ORDER };
})();
