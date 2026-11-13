/**
 * UC-09: Petugas Damkar melihat laporan terverifikasi dan mencatat progres TKP (foto wajib saat padam).
 */
document.addEventListener("DOMContentLoaded", async function () {
  const profile = await window.ApiWaspadaAuth.verifyOfficerSessionOrRedirect(["damkar"]);
  if (!profile) return;

  const { apiFetch, escapeHtml, formatDateTimeWIB, getStatusBadgeHtml, getDetectionBadgeHtml, resolveMediaUrl } =
    window.ApiWaspadaUtils;
  const { renderProgressTimeline, nextStage } = window.AWProgress;
  const icon = window.AWLayout ? window.AWLayout.icon : () => "";
  const listEl = document.getElementById("taskList");
  const alertEl = document.getElementById("damkarAlert");
  const showDone = document.getElementById("showDone");

  const STAGE_TEXT = {
    berangkat: "Tim berangkat",
    tiba: "Tim tiba di lokasi",
    pemadaman: "Pemadaman berlangsung",
    padam: "Api padam (wajib foto)",
  };
  const STAGE_BUTTON = {
    berangkat: "Catat berangkat",
    tiba: "Catat tiba",
    pemadaman: "Catat pemadaman",
    padam: "Catat api padam",
  };

  function show(msg, type) {
    alertEl.className = `alert alert-${type}`;
    alertEl.textContent = msg;
    alertEl.classList.remove("hidden");
  }

  function taskCard(r) {
    const next = r.status === "completed" ? null : nextStage(r);
    const maps = `https://www.google.com/maps/dir/?api=1&destination=${r.latitude},${r.longitude}`;
    const pin = `https://www.google.com/maps?q=${r.latitude},${r.longitude}`;
    const desc = r.description.length > 90 ? escapeHtml(r.description.slice(0, 90)) + "&hellip;" : escapeHtml(r.description);
    const form = next
      ? `<form class="progress-form" data-code="${escapeHtml(r.tracking_code)}" data-stage="${next}">
          <div class="form-group" style="margin:0">
            <label class="form-label" for="note-${r.id}">Catatan tahap: ${escapeHtml(STAGE_TEXT[next])}</label>
            <textarea id="note-${r.id}" class="form-control" rows="2" maxlength="1000" placeholder="Contoh: dua unit, akses dari jalan utama."></textarea>
          </div>
          <div class="form-group" style="margin:.6rem 0 0">
            <label class="form-label" for="photo-${r.id}">Foto lokasi ${next === "padam" ? '<span class="required">*</span>' : '<span class="opt">(opsional)</span>'}</label>
            <input id="photo-${r.id}" type="file" accept="image/jpeg,image/png" capture="environment" class="form-control" ${next === "padam" ? "required" : ""} />
          </div>
          <button type="submit" class="btn btn-primary btn-lg btn-block" style="margin-top:.8rem">${icon("check")} ${escapeHtml(STAGE_BUTTON[next])}</button>
        </form>`
      : "";
    return `<article class="card task-card" id="task-${r.id}">
      <div class="task-head">
        <div>
          <span class="code">${escapeHtml(r.tracking_code)}</span>
          <h2>${desc}</h2>
          <p class="card-sub">Dilaporkan ${formatDateTimeWIB(r.created_at)}</p>
        </div>
        ${getStatusBadgeHtml(r.status)}
      </div>
      <div class="task-body">
        <img src="${escapeHtml(resolveMediaUrl(r.result_image_url || r.image_url))}" alt="Foto laporan warga dengan penanda AI" width="400" height="300" loading="lazy" />
        <div class="task-meta">
          <div>${getDetectionBadgeHtml(r.detection_result)}</div>
          <p class="coord">${Number(r.latitude).toFixed(5)}, ${Number(r.longitude).toFixed(5)}</p>
          <div class="share-row">
            <a class="btn btn-dark" href="${maps}" target="_blank" rel="noopener">${icon("map")} Buka rute</a>
            <button type="button" class="btn btn-secondary" data-share="${escapeHtml(pin)}" data-code="${escapeHtml(r.tracking_code)}">${icon("send")} Bagikan lokasi</button>
          </div>
        </div>
      </div>
      <h3 class="task-sub">Progres</h3>
      <div class="timeline" data-timeline></div>
      ${form}
    </article>`;
  }

  async function load() {
    try {
      const tasks = await apiFetch(`/api/damkar/tasks${showDone.checked ? "?include_done=true" : ""}`);
      if (!tasks.length) {
        listEl.innerHTML = `<div class="empty-state">${icon("check-circle")}<strong>Tidak ada tugas aktif</strong><span>Laporan yang ditugaskan Operator JCOC 112 kepada Anda akan muncul di sini.</span></div>`;
        return;
      }
      listEl.innerHTML = tasks.map(taskCard).join("");
      tasks.forEach((r) => renderProgressTimeline(document.querySelector(`#task-${r.id} [data-timeline]`), r));
      listEl.querySelectorAll(".progress-form").forEach(bindForm);
      listEl.querySelectorAll("[data-share]").forEach(bindShare);
    } catch (err) {
      listEl.innerHTML = "";
      show(err.message || "Gagal memuat tugas.", "error");
    }
  }

  // Bagikan lokasi kejadian ke rekan (WhatsApp, dll.) lewat menu bagikan HP; cadangan: salin tautan
  function bindShare(btn) {
    btn.addEventListener("click", async function () {
      const url = btn.dataset.share;
      const text = `Lokasi kebakaran ${btn.dataset.code} (ApiWaspada)`;
      try {
        if (navigator.share) {
          await navigator.share({ title: "Lokasi kebakaran", text, url });
          return;
        }
      } catch (e) {
        if (e && e.name === "AbortError") return;
      }
      if (window.AWLayout && (await window.AWLayout.copyText(`${text}: ${url}`))) return;
      window.open(`https://wa.me/?text=${encodeURIComponent(text + ": " + url)}`, "_blank", "noopener");
    });
  }

  function bindForm(form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const btn = form.querySelector("button[type=submit]");
      const fileInput = form.querySelector('input[type="file"]');
      if (form.dataset.stage === "padam" && !fileInput.files[0]) {
        show("Lampirkan foto lokasi setelah api padam.", "error");
        return;
      }
      const fd = new FormData();
      fd.append("stage", form.dataset.stage);
      fd.append("note", form.querySelector("textarea").value.trim());
      if (fileInput.files[0]) fd.append("photo", fileInput.files[0]);
      btn.disabled = true;
      try {
        await apiFetch(`/api/damkar/tasks/${encodeURIComponent(form.dataset.code)}/progress`, { method: "POST", body: fd });
        show(form.dataset.stage === "padam" ? "Tugas selesai. Terima kasih." : "Progres tercatat.", "success");
        await load();
      } catch (err) {
        show(err.message || "Gagal mencatat progres.", "error");
        btn.disabled = false;
      }
    });
  }

  showDone.addEventListener("change", load);
  document.getElementById("btnRefreshTasks").addEventListener("click", load);
  await load();
  // Laporan baru yang diverifikasi muncul tanpa muat ulang manual
  setInterval(() => {
    const busy = document.activeElement && document.activeElement.closest(".progress-form");
    if (!document.hidden && !busy) load();
  }, 30000);
});
