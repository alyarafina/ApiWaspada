/**
 * Logika Halaman Lacak Laporan (`tracking.html`).
 * Mencari laporan berdasarkan kode pelacakan / ID melalui `/api/reports/{id}` dan riwayatnya.
 */
document.addEventListener("DOMContentLoaded", function () {
  const {
    apiFetch,
    escapeHtml,
    formatDateTimeWIB,
    getStatusBadgeHtml,
    getDetectionBadgeHtml,
    resolveMediaUrl,
  } = window.ApiWaspadaUtils;
  const $ = (id) => document.getElementById(id);

  const form = $("trackingSearchForm");
  const input = $("trackingInput");
  const btnSearch = $("btnTrackSearch");
  const alertBox = $("trackingAlert");
  const resultBox = $("trackingResultBox");
  const helpBox = $("trackingHelp");
  const recentBox = $("recentCodes");

  const STATUS_TEXT = {
    pending: { icon: "hourglass", text: "<strong>Menunggu dicek petugas.</strong> Cek lagi nanti." },
    verified: { icon: "shield", text: "<strong>Sedang ditangani petugas.</strong>" },
    completed: { icon: "check-circle", text: "<strong>Selesai ditangani.</strong> Terima kasih!" },
    rejected: { icon: "ban", text: "<strong>Laporan ditolak.</strong> Lihat catatan di riwayat." },
  };

  let miniMap = null;
  let miniMarker = null;

  function showAlert(msg, type) {
    alertBox.className = `alert alert-${type || "error"}`;
    alertBox.textContent = msg;
    alertBox.classList.remove("hidden");
  }

  function renderRecent() {
    const list = window.AWLayout ? window.AWLayout.getMyReports() : [];
    if (!recentBox || list.length === 0) return;
    recentBox.innerHTML =
      `<span class="lbl">Laporan Anda:</span>` +
      list.map((c) => `<button type="button" data-code="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join("");
    recentBox.classList.remove("hidden");
    recentBox.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => {
        input.value = b.dataset.code;
        lookupReport(b.dataset.code);
      })
    );
  }

  function renderTracker(status) {
    const s = String(status || "pending").toLowerCase();
    const steps = document.querySelectorAll("#trkTracker .tracker-step");
    const fill = $("trkTrackerFill");
    steps.forEach((el) => el.classList.remove("done", "current", "rejected"));
    steps[1].querySelector("strong").textContent = s === "rejected" ? "Ditolak" : "Diverifikasi";

    // Status per langkah: [Diterima, Diverifikasi, Selesai]
    const states = {
      pending: [["done"], ["current"], []],
      verified: [["done"], ["done"], ["current"]],
      completed: [["done"], ["done"], ["done"]],
      rejected: [["done"], ["rejected"], []],
    }[s] || [["done"], ["current"], []];
    states.forEach((cls, i) => cls.forEach((c) => steps[i].classList.add(c)));
    fill.style.width = s === "verified" ? "33.33%" : s === "completed" ? "66.66%" : "0%";

    const info = STATUS_TEXT[s] || STATUS_TEXT.pending;
    const explain = $("trkStatusExplain");
    explain.className = `status-explain ${STATUS_TEXT[s] ? s : "pending"}`;
    explain.innerHTML = `${window.AWLayout ? window.AWLayout.icon(info.icon) : ""}<span>${info.text}</span>`;
  }

  function renderMiniMap(lat, lng, status) {
    if (!window.L) return;
    if (!miniMap) {
      miniMap = L.map("trkMap", { scrollWheelZoom: false }).setView([lat, lng], 15);
      window.ApiWaspadaMap.initBaseTileLayers(miniMap);
    }
    const color = window.ApiWaspadaMap.STATUS_MARKER_COLORS[status] || "#DC2626";
    if (miniMarker) miniMap.removeLayer(miniMarker);
    miniMarker = L.marker([lat, lng], { icon: window.ApiWaspadaMap.createColoredPinIcon(color) }).addTo(miniMap);
    miniMap.setView([lat, lng], 15);
    setTimeout(() => miniMap.invalidateSize(), 200);
  }

  async function lookupReport(identifier) {
    const cleanId = String(identifier || "").trim().replace(/^#/, "");
    if (!cleanId) {
      showAlert("Masukkan kode pelacakan (contoh: AW-20261111-XXXXXX) atau ID laporan.");
      return;
    }
    alertBox.classList.add("hidden");

    const orig = btnSearch.innerHTML;
    btnSearch.disabled = true;
    btnSearch.innerHTML = `<span class="loading-spinner"></span> Mencari...`;

    try {
      const report = await apiFetch(`/api/reports/${encodeURIComponent(cleanId)}`);
      let histories = [];
      try {
        histories = await apiFetch(`/api/reports/${encodeURIComponent(cleanId)}/history`);
      } catch (e) {
        histories = [];
      }

      $("trkId").textContent = `#${report.id}`;
      $("trkCode").textContent = report.tracking_code;
      $("trkCreatedAt").textContent = formatDateTimeWIB(report.created_at);
      $("trkUpdatedAt").textContent = formatDateTimeWIB(report.updated_at);
      $("trkStatusBadge").innerHTML = getStatusBadgeHtml(report.status);
      $("trkDetectionBadge").innerHTML = getDetectionBadgeHtml(report.detection_result);
      $("trkConfidence").textContent = `${(Number(report.detection_confidence || 0) * 100).toFixed(1)}%`;
      $("trkCoords").textContent = `${report.latitude}, ${report.longitude}`;
      $("trkDescription").textContent = report.description;
      $("trkOrigImg").src = resolveMediaUrl(report.image_url);
      $("trkResultImg").src = resolveMediaUrl(report.result_image_url || report.image_url);

      renderTracker(report.status);

      const list = $("trkHistoryList");
      if (!histories || histories.length === 0) {
        list.innerHTML = `<p class="text-muted">Belum ada riwayat perubahan status.</p>`;
      } else {
        list.innerHTML = histories
          .map(
            (h) => `
            <div class="timeline-item">
              <div class="timeline-time">${formatDateTimeWIB(h.changed_at)}</div>
              <div style="margin:.35rem 0">${getStatusBadgeHtml(h.new_status)}</div>
              <div class="timeline-note">${escapeHtml(h.note)}</div>
            </div>`
          )
          .join("");
      }

      resultBox.classList.remove("hidden");
      if (helpBox) helpBox.classList.add("hidden");
      renderMiniMap(report.latitude, report.longitude, report.status);

      const url = new URL(window.location.href);
      url.searchParams.set("code", report.tracking_code);
      url.searchParams.delete("id");
      window.history.replaceState(null, "", url.toString());

      resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      resultBox.classList.add("hidden");
      if (helpBox) helpBox.classList.remove("hidden");
      const msg = err && err.status === 404
        ? "Kode tidak ditemukan. Coba periksa lagi."
        : (err && err.message) || "Laporan tidak ditemukan.";
      showAlert(msg);
    } finally {
      btnSearch.disabled = false;
      btnSearch.innerHTML = orig;
    }
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    lookupReport(input.value);
  });

  renderRecent();

  const params = new URLSearchParams(window.location.search);
  const initial = params.get("code") || params.get("id");
  if (initial) {
    input.value = initial;
    lookupReport(initial);
  }

});
