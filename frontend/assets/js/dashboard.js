/**
 * Logika Halaman Dashboard Petugas (`dashboard.html`):
 * - Autentikasi wajib petugas
 * - Statistik KPI real-time dari SQLite (`/api/dashboard/stats`)
 * - 3 Grafik Chart.js (Laporan per Tanggal, Distribusi Status, Distribusi Deteksi AI)
 * - Peta Interaktif Leaflet.js (`/api/dashboard/map`)
 * - Tabel Laporan dengan Search, Filter Status, Filter Tanggal, dan Pagination (`/api/dashboard/reports`)
 */

document.addEventListener("DOMContentLoaded", async function () {
  const {
    apiFetch,
    escapeHtml,
    formatDateTimeWIB,
    getStatusBadgeHtml,
    getDetectionBadgeHtml,
  } = window.ApiWaspadaUtils;
  const cfg = window.APIWASPADA_CONFIG;

  // 1. Pastikan petugas sudah login
  const officer = await window.ApiWaspadaAuth.verifyOfficerSessionOrRedirect();
  if (!officer) return;

  const officerNameBadge = document.getElementById("officerNameBadge");
  if (officerNameBadge) {
    officerNameBadge.textContent = `${officer.full_name} (@${officer.username})`;
  }

  const btnLogout = document.getElementById("btnOfficerLogout");
  if (btnLogout) {
    btnLogout.addEventListener("click", function () {
      window.ApiWaspadaAuth.performOfficerLogout();
    });
  }

  // Elemen KPI
  const kpiTotal = document.getElementById("kpiTotal");
  const kpiPending = document.getElementById("kpiPending");
  const kpiVerified = document.getElementById("kpiVerified");
  const kpiRejected = document.getElementById("kpiRejected");
  const kpiCompleted = document.getElementById("kpiCompleted");
  const aiStatusPill = document.getElementById("dashboardAiStatus");

  // Variabel instance Chart.js
  let chartByDate = null;
  let chartByStatus = null;
  let chartByDetection = null;

  // Inisialisasi Peta GIS Dashboard
  const dashMap = L.map("officerDashboardMap").setView(
    [cfg.DEFAULT_LAT, cfg.DEFAULT_LNG],
    cfg.DEFAULT_ZOOM
  );
  window.ApiWaspadaMap.initBaseTileLayers(dashMap);
  const dashMarkersGroup = L.layerGroup().addTo(dashMap);

  // Filter & Tabel
  const filterSearch = document.getElementById("filterSearch");
  const filterStatus = document.getElementById("filterStatus");
  const filterDateFrom = document.getElementById("filterDateFrom");
  const filterDateTo = document.getElementById("filterDateTo");
  const btnApplyFilter = document.getElementById("btnApplyFilter");
  const btnResetFilter = document.getElementById("btnResetFilter");
  const btnRefreshDashboard = document.getElementById("btnRefreshDashboard");
  const reportsTableBody = document.getElementById("dashboardReportsTableBody");
  const paginationInfo = document.getElementById("paginationInfo");
  const btnPrevPage = document.getElementById("btnPrevPage");
  const btnNextPage = document.getElementById("btnNextPage");

  let currentPage = 1;
  const pageSize = 8;
  let totalPages = 1;

  // 2. Muat Statistik & Render Chart.js
  async function loadDashboardStats() {
    const stats = await apiFetch("/api/dashboard/stats");

    kpiTotal.textContent = stats.total_reports;
    kpiPending.textContent = stats.pending_count;
    kpiVerified.textContent = stats.verified_count;
    kpiRejected.textContent = stats.rejected_count;
    kpiCompleted.textContent = stats.completed_count;

    if (aiStatusPill) {
      aiStatusPill.innerHTML = stats.ai_active
        ? `<span class="badge badge-completed"><span class="badge-dot"></span>Model YOLO Aktif</span>`
        : `<span class="badge badge-pending"><span class="badge-dot"></span>Mode AI Belum Aktif (Menunggu best.pt)</span>`;
    }

    if (typeof Chart === "undefined") return;

    // Chart 1: Laporan Berdasarkan Tanggal
    const dateLabels = (stats.reports_by_date || []).map((d) => d.date);
    const dateCounts = (stats.reports_by_date || []).map((d) => d.count);
    const ctxDate = document.getElementById("chartReportsByDate").getContext("2d");
    if (chartByDate) chartByDate.destroy();
    chartByDate = new Chart(ctxDate, {
      type: "line",
      data: {
        labels: dateLabels.length ? dateLabels : ["Belum Ada Data"],
        datasets: [
          {
            label: "Jumlah Laporan Masuk",
            data: dateCounts.length ? dateCounts : [0],
            borderColor: "#DC2626",
            backgroundColor: "rgba(220, 38, 38, 0.14)",
            borderWidth: 2.5,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: "#DC2626",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: true } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });

    // Chart 2: Distribusi Status Laporan
    const ctxStatus = document.getElementById("chartStatusDist").getContext("2d");
    if (chartByStatus) chartByStatus.destroy();
    chartByStatus = new Chart(ctxStatus, {
      type: "doughnut",
      data: {
        labels: ["Pending", "Verified", "Rejected", "Completed"],
        datasets: [
          {
            data: [
              stats.pending_count,
              stats.verified_count,
              stats.rejected_count,
              stats.completed_count,
            ],
            backgroundColor: ["#F59E0B", "#2563EB", "#64748B", "#16A34A"],
            borderWidth: 2,
            borderColor: "#FFFFFF",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });

    // Chart 3: Distribusi Hasil Deteksi AI
    const detDist = stats.detection_distribution || {};
    const detKeys = Object.keys(detDist);
    const detVals = Object.values(detDist);
    const ctxDet = document.getElementById("chartDetectionDist").getContext("2d");
    if (chartByDetection) chartByDetection.destroy();
    chartByDetection = new Chart(ctxDet, {
      type: "bar",
      data: {
        labels: detKeys,
        datasets: [
          {
            label: "Jumlah Laporan",
            data: detVals,
            backgroundColor: [
              "#DC2626",
              "#F97316",
              "#B91C1C",
              "#16A34A",
              "#64748B",
            ],
            borderRadius: 6,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  // 3. Muat Marker Peta GIS
  async function loadMapData() {
    const statusVal = filterStatus.value;
    const q = statusVal ? `?status=${encodeURIComponent(statusVal)}` : "";
    const mapData = await apiFetch(`/api/dashboard/map${q}`);
    window.ApiWaspadaMap.renderReportsDistributionMap(
      dashMap,
      dashMarkersGroup,
      mapData.markers,
      true
    );
  }

  // 4. Muat Tabel Laporan dengan Filter & Pagination
  async function loadReportsTable() {
    const params = new URLSearchParams();
    params.set("page", String(currentPage));
    params.set("page_size", String(pageSize));

    if (filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
    if (filterStatus.value) params.set("status", filterStatus.value);
    if (filterDateFrom.value) params.set("date_from", filterDateFrom.value);
    if (filterDateTo.value) params.set("date_to", filterDateTo.value);

    const data = await apiFetch(`/api/dashboard/reports?${params.toString()}`);
    totalPages = data.total_pages || 1;

    paginationInfo.textContent = `Halaman ${data.page} dari ${totalPages} (Total ${data.total} laporan)`;
    btnPrevPage.disabled = data.page <= 1;
    btnNextPage.disabled = data.page >= totalPages;

    if (!data.items || data.items.length === 0) {
      reportsTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center; padding:1.75rem; color:#64748B;">
            Tidak ada laporan yang cocok dengan kriteria pencarian/filter.
          </td>
        </tr>`;
      return;
    }

    reportsTableBody.innerHTML = data.items
      .map(
        (r) => `
        <tr>
          <td>
            <strong>#${r.id}</strong><br/>
            <small style="color:#64748B;">${escapeHtml(r.tracking_code)}</small>
          </td>
          <td>${formatDateTimeWIB(r.created_at)}</td>
          <td>
            <code>${r.latitude}, ${r.longitude}</code><br/>
            <small style="color:#64748B;">Pelapor: ${escapeHtml(r.reporter_name || "Masyarakat")}</small>
          </td>
          <td>${getDetectionBadgeHtml(r.detection_result)}</td>
          <td><strong>${(Number(r.detection_confidence || 0) * 100).toFixed(1)}%</strong></td>
          <td>${getStatusBadgeHtml(r.status)}</td>
          <td>
            <a href="/report-detail.html?id=${encodeURIComponent(r.id)}" class="btn btn-primary btn-sm">
              Periksa &amp; Verifikasi
            </a>
          </td>
        </tr>`
      )
      .join("");
  }

  async function refreshAllDashboardData() {
    try {
      await Promise.all([loadDashboardStats(), loadMapData(), loadReportsTable()]);
    } catch (err) {
      console.error("Gagal memuat data dashboard:", err);
    }
  }

  btnApplyFilter.addEventListener("click", function () {
    currentPage = 1;
    loadMapData();
    loadReportsTable();
  });

  btnResetFilter.addEventListener("click", function () {
    filterSearch.value = "";
    filterStatus.value = "";
    filterDateFrom.value = "";
    filterDateTo.value = "";
    currentPage = 1;
    loadMapData();
    loadReportsTable();
  });

  btnRefreshDashboard.addEventListener("click", refreshAllDashboardData);

  btnPrevPage.addEventListener("click", function () {
    if (currentPage > 1) {
      currentPage -= 1;
      loadReportsTable();
    }
  });

  btnNextPage.addEventListener("click", function () {
    if (currentPage < totalPages) {
      currentPage += 1;
      loadReportsTable();
    }
  });

  await refreshAllDashboardData();
});
