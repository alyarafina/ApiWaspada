/**
 * Logika Halaman Pelacakan Status Laporan & Peta Persebaran Publik (`tracking.html`).
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
  const cfg = window.APIWaspadaConfig || window.APIWASPADA_CONFIG;

  const trackingSearchForm = document.getElementById("trackingSearchForm");
  const trackingInput = document.getElementById("trackingInput");
  const trackingAlert = document.getElementById("trackingAlert");
  const trackingResultBox = document.getElementById("trackingResultBox");

  // Elemen Detail Laporan
  const trkId = document.getElementById("trkId");
  const trkCode = document.getElementById("trkCode");
  const trkCreatedAt = document.getElementById("trkCreatedAt");
  const trkUpdatedAt = document.getElementById("trkUpdatedAt");
  const trkStatusBadge = document.getElementById("trkStatusBadge");
  const trkDetectionBadge = document.getElementById("trkDetectionBadge");
  const trkConfidence = document.getElementById("trkConfidence");
  const trkCoords = document.getElementById("trkCoords");
  const trkDescription = document.getElementById("trkDescription");
  const trkOrigImg = document.getElementById("trkOrigImg");
  const trkResultImg = document.getElementById("trkResultImg");
  const trkHistoryList = document.getElementById("trkHistoryList");

  // Peta Persebaran Publik
  const publicMapFilter = document.getElementById("publicMapFilter");
  const publicReportsTableBody = document.getElementById("publicReportsTableBody");

  const publicMap = L.map("publicDistributionMap").setView(
    [cfg.DEFAULT_LAT, cfg.DEFAULT_LNG],
    cfg.DEFAULT_ZOOM
  );
  window.ApiWaspadaMap.initBaseTileLayers(publicMap);
  const publicMarkersGroup = L.layerGroup().addTo(publicMap);

  function showTrackingAlert(msg, type = "error") {
    trackingAlert.className = `alert alert-${type}`;
    trackingAlert.textContent = msg;
    trackingAlert.classList.remove("hidden");
  }

  function hideTrackingAlert() {
    trackingAlert.classList.add("hidden");
  }

  async function lookupReport(identifier) {
    const cleanId = String(identifier || "").trim().replace(/^#/, "");
    if (!cleanId) {
      showTrackingAlert("Masukkan ID Laporan atau Kode Pelacakan (contoh: AW-20261111-XXXXXX).");
      return;
    }
    hideTrackingAlert();

    try {
      const report = await apiFetch(`/api/reports/${encodeURIComponent(cleanId)}`);
      const histories = await apiFetch(`/api/reports/${encodeURIComponent(cleanId)}/history`);

      trkId.textContent = `#${report.id}`;
      trkCode.textContent = report.tracking_code;
      trkCreatedAt.textContent = formatDateTimeWIB(report.created_at);
      trkUpdatedAt.textContent = formatDateTimeWIB(report.updated_at);
      trkStatusBadge.innerHTML = getStatusBadgeHtml(report.status);
      trkDetectionBadge.innerHTML = getDetectionBadgeHtml(report.detection_result);
      trkConfidence.textContent = `${(Number(report.detection_confidence || 0) * 100).toFixed(1)}%`;
      trkCoords.textContent = `${report.latitude}, ${report.longitude}`;
      trkDescription.textContent = report.description;
      trkOrigImg.src = resolveMediaUrl(report.image_url);
      trkResultImg.src = resolveMediaUrl(report.result_image_url || report.image_url);

      if (!histories || histories.length === 0) {
        trkHistoryList.innerHTML = `<p style="color:#64748B;">Belum ada riwayat perubahan status.</p>`;
      } else {
        trkHistoryList.innerHTML = histories
          .map(
            (h) => `
            <div class="timeline-item">
              <div style="font-size:0.82rem; color:#64748B;">
                ${formatDateTimeWIB(h.changed_at)}
              </div>
              <div style="margin:0.25rem 0;">
                ${getStatusBadgeHtml(h.new_status)}
              </div>
              <div style="font-size:0.92rem; color:#1E293B;">
                ${escapeHtml(h.note)}
              </div>
            </div>`
          )
          .join("");
      }

      trackingResultBox.classList.remove("hidden");
      publicMap.setView([report.latitude, report.longitude], 15);
    } catch (err) {
      trackingResultBox.classList.add("hidden");
      showTrackingAlert(err.message || "Laporan tidak ditemukan.");
    }
  }

  trackingSearchForm.addEventListener("submit", function (ev) {
    ev.preventDefault();
    lookupReport(trackingInput.value);
  });

  async function loadPublicMapAndRecentReports() {
    try {
      const statusVal = publicMapFilter.value;
      const q = statusVal ? `?status=${encodeURIComponent(statusVal)}` : "";
      const mapData = await apiFetch(`/api/dashboard/map${q}`);
      window.ApiWaspadaMap.renderReportsDistributionMap(
        publicMap,
        publicMarkersGroup,
        mapData.markers,
        false
      );

      const listData = await apiFetch(`/api/reports${q}`);
      if (!listData.items || listData.items.length === 0) {
        publicReportsTableBody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align:center; color:#64748B;">
              Belum ada data laporan kebakaran untuk filter ini.
            </td>
          </tr>`;
      } else {
        publicReportsTableBody.innerHTML = listData.items
          .map(
            (r) => `
            <tr>
              <td><strong>#${r.id}</strong><br/><small style="color:#64748B;">${escapeHtml(r.tracking_code)}</small></td>
              <td>${formatDateTimeWIB(r.created_at)}</td>
              <td><code>${r.latitude}, ${r.longitude}</code></td>
              <td>${getDetectionBadgeHtml(r.detection_result)}</td>
              <td>${getStatusBadgeHtml(r.status)}</td>
              <td>
                <button type="button" class="btn btn-secondary btn-sm btn-track-row" data-code="${escapeHtml(r.tracking_code)}">
                  Periksa Status
                </button>
              </td>
            </tr>`
          )
          .join("");

        document.querySelectorAll(".btn-track-row").forEach((btn) => {
          btn.addEventListener("click", function () {
            const code = this.getAttribute("data-code");
            trackingInput.value = code;
            lookupReport(code);
            trackingSearchForm.scrollIntoView({ behavior: "smooth" });
          });
        });
      }
    } catch (e) {
      console.error("Gagal memuat peta publik:", e);
    }
  }

  publicMapFilter.addEventListener("change", loadPublicMapAndRecentReports);
  loadPublicMapAndRecentReports();

  // Periksa parameter URL (?code=... atau ?id=...)
  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get("code") || params.get("id");
  if (initialQuery) {
    trackingInput.value = initialQuery;
    lookupReport(initialQuery);
  }
});
