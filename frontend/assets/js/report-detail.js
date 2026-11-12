/**
 * Logika Halaman Pemeriksaan & Verifikasi Detail Laporan Petugas (`report-detail.html`).
 */

document.addEventListener("DOMContentLoaded", async function () {
  const {
    apiFetch,
    escapeHtml,
    formatDateTimeWIB,
    getStatusBadgeHtml,
    getDetectionBadgeHtml,
    resolveMediaUrl,
  } = window.ApiWaspadaUtils;
  const cfg = window.APIWASPADA_CONFIG;

  // Pastikan petugas sudah login
  const officer = await window.ApiWaspadaAuth.verifyOfficerSessionOrRedirect();
  if (!officer) return;

  const officerBadge = document.getElementById("officerNameBadge");
  if (officerBadge) {
    officerBadge.textContent = officer.full_name || officer.username;
  }
  const officerAvatar = document.getElementById("officerAvatar");
  if (officerAvatar) {
    officerAvatar.textContent = String(officer.full_name || officer.username || "P").trim().charAt(0).toUpperCase();
  }

  const params = new URLSearchParams(window.location.search);
  const reportId = params.get("id") || params.get("code");
  const detailAlert = document.getElementById("detailAlert");

  if (!reportId) {
    detailAlert.className = "alert alert-error";
    detailAlert.textContent = "ID Laporan tidak ditemukan pada URL. Silakan kembali ke Dashboard.";
    detailAlert.classList.remove("hidden");
    return;
  }

  // Elemen DOM Detail
  const detReportTitle = document.getElementById("detReportTitle");
  const detTrackingCode = document.getElementById("detTrackingCode");
  const detStatusBadge = document.getElementById("detStatusBadge");
  const detReporterName = document.getElementById("detReporterName");
  const detCreatedAt = document.getElementById("detCreatedAt");
  const detUpdatedAt = document.getElementById("detUpdatedAt");
  const detCoordinates = document.getElementById("detCoordinates");
  const detRegionNote = document.getElementById("detRegionNote");
  const detDescription = document.getElementById("detDescription");
  const detAiBadge = document.getElementById("detAiBadge");
  const detAiConfidence = document.getElementById("detAiConfidence");
  const detAiTime = document.getElementById("detAiTime");
  const detAiModel = document.getElementById("detAiModel");
  const detOrigImage = document.getElementById("detOrigImage");
  const detResultImage = document.getElementById("detResultImage");
  const detBboxTableBody = document.getElementById("detBboxTableBody");
  const detHistoryTimeline = document.getElementById("detHistoryTimeline");

  // Form Update Status
  const statusUpdateForm = document.getElementById("statusUpdateForm");
  const newStatusSelect = document.getElementById("newStatusSelect");
  const verificationNote = document.getElementById("verificationNote");
  const btnSaveStatus = document.getElementById("btnSaveStatus");

  // Inisialisasi Peta Lokasi Kejadian
  const detailMap = L.map("detailLocationMap").setView(
    [cfg.DEFAULT_LAT, cfg.DEFAULT_LNG],
    14
  );
  window.ApiWaspadaMap.initBaseTileLayers(detailMap);
  let locationMarker = null;

  // Tombol pilihan status (sinkron dengan <select> yang dipakai untuk pengiriman)
  const statusButtons = document.querySelectorAll("#statusOptions .status-option");
  function syncStatusButtons() {
    statusButtons.forEach((b) => {
      b.setAttribute("aria-pressed", b.dataset.value === newStatusSelect.value ? "true" : "false");
    });
  }
  statusButtons.forEach((b) => {
    b.addEventListener("click", function () {
      newStatusSelect.value = b.dataset.value;
      syncStatusButtons();
    });
  });
  syncStatusButtons();

  function showDetailAlert(msg, type = "info") {
    detailAlert.className = `alert alert-${type}`;
    detailAlert.textContent = msg;
    detailAlert.classList.remove("hidden");
  }

  function renderReportDetail(report) {
    detReportTitle.textContent = `Detail Laporan #${report.id}`;
    detTrackingCode.textContent = report.tracking_code;
    detStatusBadge.innerHTML = getStatusBadgeHtml(report.status);
    detReporterName.textContent = report.reporter_name || "Masyarakat";
    detCreatedAt.textContent = formatDateTimeWIB(report.created_at);
    detUpdatedAt.textContent = formatDateTimeWIB(report.updated_at);
    detCoordinates.textContent = `${report.latitude}, ${report.longitude}`;
    detRegionNote.textContent =
      (report.region_info && report.region_info.region_note) || "";
    detDescription.textContent = report.description;

    detAiBadge.innerHTML = getDetectionBadgeHtml(report.detection_result);
    detAiConfidence.textContent = `${(Number(report.detection_confidence || 0) * 100).toFixed(1)}%`;
    detAiTime.textContent = `${Number(report.inference_time_ms || 0).toFixed(1)} ms`;
    detAiModel.textContent = report.ai_model_used || "-";

    detOrigImage.src = resolveMediaUrl(report.image_url);
    detResultImage.src = resolveMediaUrl(report.result_image_url || report.image_url);

    newStatusSelect.value = report.status;
    syncStatusButtons();

    const boxes = report.detections || [];
    if (boxes.length === 0) {
      detBboxTableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align:center; color:#64748B;">
            Tidak ada objek bounding box yang terdeteksi pada gambar ini.
          </td>
        </tr>`;
    } else {
      detBboxTableBody.innerHTML = boxes
        .map(
          (b, idx) => `
          <tr>
            <td data-label="No">${idx + 1}</td>
            <td data-label="Kelas"><strong>${escapeHtml(b.class_name)}</strong> (ID: ${b.class_id})</td>
            <td data-label="Keyakinan">${(Number(b.confidence) * 100).toFixed(1)}%</td>
            <td data-label="Kotak"><code>[${b.bbox_xyxy.join(", ")}]</code></td>
          </tr>`
        )
        .join("");
    }

    // Update marker peta
    const color =
      window.ApiWaspadaMap.STATUS_MARKER_COLORS[report.status] || "#DC2626";
    if (locationMarker) {
      detailMap.removeLayer(locationMarker);
    }
    locationMarker = L.marker([report.latitude, report.longitude], {
      icon: window.ApiWaspadaMap.createColoredPinIcon(color),
    }).addTo(detailMap);
    locationMarker
      .bindPopup(
        `<strong>Laporan #${report.id}</strong><br>${escapeHtml(report.detection_result)}<br>Koordinat: ${report.latitude}, ${report.longitude}`
      )
      .openPopup();
    detailMap.setView([report.latitude, report.longitude], 15);

    // Render riwayat perubahan status
    const histories = report.histories || [];
    if (histories.length === 0) {
      detHistoryTimeline.innerHTML = `<p style="color:#64748B;">Belum ada riwayat perubahan status.</p>`;
    } else {
      detHistoryTimeline.innerHTML = histories
        .map(
          (h) => `
          <div class="timeline-item">
            <div class="timeline-time">
              ${formatDateTimeWIB(h.changed_at)} &bull; Oleh: <strong>${escapeHtml(h.changed_by || "system")}</strong>
            </div>
            <div style="margin:0.3rem 0;">
              ${h.previous_status ? `<span style="font-size:0.82rem; color:#64748B;">${escapeHtml(h.previous_status)} &rarr; </span>` : ""}
              ${getStatusBadgeHtml(h.new_status)}
            </div>
            <div class="timeline-note">
              ${escapeHtml(h.note)}
            </div>
          </div>`
        )
        .join("");
    }
  }

  async function fetchReportDetail() {
    try {
      const data = await apiFetch(`/api/dashboard/reports/${encodeURIComponent(reportId)}`);
      renderReportDetail(data);
    } catch (err) {
      showDetailAlert(err.message || "Gagal memuat detail laporan.", "error");
    }
  }

  statusUpdateForm.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    detailAlert.classList.add("hidden");

    const newStatus = newStatusSelect.value;
    const noteText = verificationNote.value.trim();

    if (noteText.length < 3) {
      showDetailAlert("Catatan verifikasi wajib diisi minimal 3 karakter.", "error");
      return;
    }

    const origText = btnSaveStatus.innerHTML;
    btnSaveStatus.disabled = true;
    btnSaveStatus.innerHTML = `<span class="loading-spinner"></span> Menyimpan Perubahan...`;

    try {
      const updated = await apiFetch(
        `/api/reports/${encodeURIComponent(reportId)}/status`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus, note: noteText }),
        }
      );
      verificationNote.value = "";
      renderReportDetail(updated);
      showDetailAlert(
        `Status laporan #${updated.id} berhasil diperbarui menjadi '${updated.status.toUpperCase()}' dan tercatat dalam riwayat.`,
        "success"
      );
      detailAlert.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
      showDetailAlert(err.message || "Gagal memperbarui status laporan.", "error");
    } finally {
      btnSaveStatus.disabled = false;
      btnSaveStatus.innerHTML = origText;
    }
  });

  await fetchReportDetail();
});
