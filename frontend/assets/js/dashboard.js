/**
 * Logika Dashboard Petugas — dipakai oleh tiga halaman terpisah:
 * - `dashboard.html`          : KPI, 3 grafik Chart.js, daftar "perlu diperiksa"
 * - `dashboard-laporan.html`  : tabel laporan + pencarian, filter, pagination
 * - `dashboard-peta.html`     : peta Leaflet sebaran laporan
 * Setiap bagian hanya dijalankan jika elemennya ada pada halaman.
 */
document.addEventListener("DOMContentLoaded", async function () {
  const { apiFetch, escapeHtml, formatDateTimeWIB, getStatusBadgeHtml, getDetectionBadgeHtml } =
    window.ApiWaspadaUtils;
  const cfg = window.APIWASPADA_CONFIG;
  const $ = (id) => document.getElementById(id);
  const icon = window.AWLayout ? window.AWLayout.icon : () => "";

  // 1. Wajib login petugas
  const officer = await window.ApiWaspadaAuth.verifyOfficerSessionOrRedirect();
  if (!officer) return;

  const nameBadge = $("officerNameBadge");
  if (nameBadge) nameBadge.textContent = officer.full_name || officer.username;
  const avatar = $("officerAvatar");
  if (avatar) avatar.textContent = String(officer.full_name || officer.username || "P").trim().charAt(0).toUpperCase();
  const greeting = $("dashGreeting");
  if (greeting) {
    const h = Number(new Date().toLocaleString("en-US", { hour: "numeric", hour12: false, timeZone: "Asia/Jakarta" }));
    const sapa = h < 11 ? "Selamat pagi" : h < 15 ? "Selamat siang" : h < 18 ? "Selamat sore" : "Selamat malam";
    const first = String(officer.full_name || officer.username || "").split(" ")[0];
    greeting.textContent = `${sapa}${first ? ", " + first : ""}`;
  }

  const tasks = [];

  // ---------------------------------------------------------------------------
  // 2. Ringkasan: KPI + grafik
  // ---------------------------------------------------------------------------
  const hasSummary = !!$("kpiTotal");
  let chartByDate = null;
  let chartByStatus = null;
  let chartByDetection = null;

  async function loadDashboardStats() {
    const stats = await apiFetch("/api/dashboard/stats");

    $("kpiTotal").textContent = stats.total_reports;
    $("kpiPending").textContent = stats.pending_count;
    $("kpiVerified").textContent = stats.verified_count;
    $("kpiRejected").textContent = stats.rejected_count;
    $("kpiCompleted").textContent = stats.completed_count;

    const aiPill = $("dashboardAiStatus");
    if (aiPill) {
      aiPill.innerHTML = stats.ai_active
        ? `<span class="badge badge-completed"><span class="badge-dot"></span>Model AI aktif</span>`
        : `<span class="badge badge-pending"><span class="badge-dot"></span>AI belum aktif (menunggu best.pt)</span>`;
    }

    if (typeof Chart === "undefined") return;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = "#64748B";

    const byDate = stats.reports_by_date || [];
    const dateCtx = $("chartReportsByDate");
    if (dateCtx) {
      if (chartByDate) chartByDate.destroy();
      const g = dateCtx.getContext("2d").createLinearGradient(0, 0, 0, 240);
      g.addColorStop(0, "rgba(220, 38, 38, .28)");
      g.addColorStop(1, "rgba(220, 38, 38, 0)");
      chartByDate = new Chart(dateCtx, {
        type: "line",
        data: {
          labels: byDate.length ? byDate.map((d) => d.date) : ["Belum ada data"],
          datasets: [{
            label: "Laporan masuk",
            data: byDate.length ? byDate.map((d) => d.count) : [0],
            borderColor: "#DC2626",
            backgroundColor: g,
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: "#DC2626",
            pointRadius: 3,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#F1F5F9" } },
            x: { grid: { display: false } },
          },
        },
      });
    }

    const statusCtx = $("chartStatusDist");
    if (statusCtx) {
      if (chartByStatus) chartByStatus.destroy();
      chartByStatus = new Chart(statusCtx, {
        type: "doughnut",
        data: {
          labels: ["Menunggu", "Terverifikasi", "Ditolak", "Selesai"],
          datasets: [{
            data: [stats.pending_count, stats.verified_count, stats.rejected_count, stats.completed_count],
            backgroundColor: ["#F59E0B", "#2563EB", "#94A3B8", "#16A34A"],
            borderWidth: 3,
            borderColor: "#FFFFFF",
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "62%",
          plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, padding: 14 } } },
        },
      });
    }

    const detCtx = $("chartDetectionDist");
    if (detCtx) {
      const detDist = stats.detection_distribution || {};
      if (chartByDetection) chartByDetection.destroy();
      chartByDetection = new Chart(detCtx, {
        type: "bar",
        data: {
          labels: Object.keys(detDist),
          datasets: [{
            label: "Jumlah laporan",
            data: Object.values(detDist),
            backgroundColor: ["#DC2626", "#F97316", "#B91C1C", "#16A34A", "#94A3B8"],
            borderRadius: 8,
            maxBarThickness: 26,
          }],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#F1F5F9" } },
            y: { grid: { display: false }, ticks: { callback: function (v) { const l = this.getLabelForValue(v); return l.length > 22 ? l.slice(0, 21) + "…" : l; } } },
          },
        },
      });
    }
  }

  async function loadPendingQuickList() {
    const box = $("pendingQuickList");
    if (!box) return;
    const data = await apiFetch("/api/dashboard/reports?status=pending&page=1&page_size=5");
    const items = data.items || [];
    if (items.length === 0) {
      box.innerHTML = `<div class="empty-state" style="padding:1rem">${icon("check-circle")}<strong>Semua beres</strong><span>Tidak ada laporan yang menunggu.</span></div>`;
      return;
    }
    box.innerHTML = items
      .map(
        (r) => `
        <a class="pending-row" href="/report-detail.html?id=${encodeURIComponent(r.id)}">
          <span class="legend-marker" style="background:#F59E0B"></span>
          <span class="meta"><strong>#${r.id} &middot; ${escapeHtml(r.tracking_code)}</strong><span>${escapeHtml(r.description)}</span></span>
          ${icon("chevron-right")}
        </a>`
      )
      .join("");
  }

  if (hasSummary) {
    tasks.push(loadDashboardStats, loadPendingQuickList);
  }

  // ---------------------------------------------------------------------------
  // 3. Peta sebaran
  // ---------------------------------------------------------------------------
  const filterStatus = $("filterStatus");
  let dashMap = null;
  let dashMarkersGroup = null;

  async function loadMapData() {
    if (!dashMap) return;
    const statusVal = filterStatus ? filterStatus.value : "";
    const q = statusVal ? `?status=${encodeURIComponent(statusVal)}` : "";
    const mapData = await apiFetch(`/api/dashboard/map${q}`);
    window.ApiWaspadaMap.renderReportsDistributionMap(dashMap, dashMarkersGroup, mapData.markers, true);
    const count = $("mapMarkerCount");
    if (count) count.textContent = `${(mapData.markers || []).length} titik ditampilkan`;
  }

  if ($("officerDashboardMap") && window.L) {
    dashMap = L.map("officerDashboardMap").setView([cfg.DEFAULT_LAT, cfg.DEFAULT_LNG], cfg.DEFAULT_ZOOM);
    window.ApiWaspadaMap.initBaseTileLayers(dashMap);
    dashMarkersGroup = L.layerGroup().addTo(dashMap);
    tasks.push(loadMapData);
    setTimeout(() => dashMap.invalidateSize(), 250);
  }

  // ---------------------------------------------------------------------------
  // 4. Tabel laporan
  // ---------------------------------------------------------------------------
  const reportsTableBody = $("dashboardReportsTableBody");
  const filterSearch = $("filterSearch");
  const filterDateFrom = $("filterDateFrom");
  const filterDateTo = $("filterDateTo");
  const paginationInfo = $("paginationInfo");
  const btnPrevPage = $("btnPrevPage");
  const btnNextPage = $("btnNextPage");

  let currentPage = 1;
  const pageSize = 8;
  let totalPages = 1;

  async function loadReportsTable() {
    if (!reportsTableBody) return;
    const params = new URLSearchParams();
    params.set("page", String(currentPage));
    params.set("page_size", String(pageSize));
    if (filterSearch && filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
    if (filterStatus && filterStatus.value) params.set("status", filterStatus.value);
    if (filterDateFrom && filterDateFrom.value) params.set("date_from", filterDateFrom.value);
    if (filterDateTo && filterDateTo.value) params.set("date_to", filterDateTo.value);

    const data = await apiFetch(`/api/dashboard/reports?${params.toString()}`);
    totalPages = data.total_pages || 1;

    paginationInfo.textContent = `Halaman ${data.page} dari ${totalPages} · ${data.total} laporan`;
    btnPrevPage.disabled = data.page <= 1;
    btnNextPage.disabled = data.page >= totalPages;

    if (!data.items || data.items.length === 0) {
      reportsTableBody.innerHTML = `
        <tr><td colspan="7"><div class="empty-state">${icon("search")}<strong>Tidak ada laporan</strong><span>Coba ubah kata kunci atau filter.</span></div></td></tr>`;
      return;
    }

    reportsTableBody.innerHTML = data.items
      .map(
        (r) => `
        <tr>
          <td data-label="ID"><strong>#${r.id}</strong><br/><small class="mono text-muted">${escapeHtml(r.tracking_code)}</small></td>
          <td data-label="Waktu">${formatDateTimeWIB(r.created_at)}</td>
          <td data-label="Lokasi"><code>${r.latitude}, ${r.longitude}</code><br/><small class="text-muted">Pelapor: ${escapeHtml(r.reporter_name || "Masyarakat")}</small></td>
          <td data-label="Hasil AI">${getDetectionBadgeHtml(r.detection_result)}</td>
          <td data-label="Keyakinan"><strong>${(Number(r.detection_confidence || 0) * 100).toFixed(1)}%</strong></td>
          <td data-label="Status">${getStatusBadgeHtml(r.status)}</td>
          <td data-label="Aksi" class="td-action"><a href="/report-detail.html?id=${encodeURIComponent(r.id)}" class="btn btn-primary btn-sm">Periksa ${icon("arrow-right")}</a></td>
        </tr>`
      )
      .join("");
  }

  if (reportsTableBody) {
    // Prefill dari URL (mis. dari kartu KPI: ?status=pending)
    const urlParams = new URLSearchParams(window.location.search);
    const preStatus = urlParams.get("status");
    if (preStatus && filterStatus && filterStatus.querySelector(`option[value="${CSS.escape(preStatus)}"]`)) {
      filterStatus.value = preStatus;
    }
    tasks.push(loadReportsTable);

    function applyFilter() {
      currentPage = 1;
      const url = new URL(window.location.href);
      if (filterStatus.value) url.searchParams.set("status", filterStatus.value);
      else url.searchParams.delete("status");
      window.history.replaceState(null, "", url.toString());
      loadReportsTable().catch(handleErr);
    }

    $("btnApplyFilter").addEventListener("click", applyFilter);
    if (filterStatus) filterStatus.addEventListener("change", applyFilter);
    if (filterSearch) {
      filterSearch.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); applyFilter(); }
      });
    }
    $("btnResetFilter").addEventListener("click", function () {
      filterSearch.value = "";
      filterStatus.value = "";
      filterDateFrom.value = "";
      filterDateTo.value = "";
      applyFilter();
    });
    btnPrevPage.addEventListener("click", function () {
      if (currentPage > 1) { currentPage -= 1; loadReportsTable().catch(handleErr); }
    });
    btnNextPage.addEventListener("click", function () {
      if (currentPage < totalPages) { currentPage += 1; loadReportsTable().catch(handleErr); }
    });
  } else if (filterStatus && dashMap) {
    filterStatus.addEventListener("change", () => loadMapData().catch(handleErr));
  }

  function handleErr(err) {
    console.error("Gagal memuat data dashboard:", err);
  }

  async function refreshAll() {
    const btn = $("btnRefreshDashboard");
    const orig = btn ? btn.innerHTML : "";
    if (btn) { btn.disabled = true; btn.innerHTML = `<span class="loading-spinner"></span> Memuat`; }
    try {
      await Promise.all(tasks.map((fn) => fn().catch(handleErr)));
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = orig; }
    }
  }

  const btnRefresh = $("btnRefreshDashboard");
  if (btnRefresh) btnRefresh.addEventListener("click", refreshAll);

  await refreshAll();
});
