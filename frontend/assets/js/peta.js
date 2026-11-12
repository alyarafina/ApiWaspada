/**
 * Logika Halaman Peta Laporan Publik (`peta.html`).
 * Memuat marker dari `/api/dashboard/map` (publik) dan daftar laporan dari `/api/reports`.
 */
document.addEventListener("DOMContentLoaded", function () {
  const { apiFetch, escapeHtml, formatDateTimeWIB, getStatusBadgeHtml, resolveMediaUrl } =
    window.ApiWaspadaUtils;
  const cfg = window.APIWASPADA_CONFIG;
  const icon = window.AWLayout ? window.AWLayout.icon : () => "";

  const listEl = document.getElementById("publicReportList");
  const infoEl = document.getElementById("mapListInfo");
  const chips = document.querySelectorAll("#mapFilterChips .chip");

  const map = L.map("publicDistributionMap").setView([cfg.DEFAULT_LAT, cfg.DEFAULT_LNG], cfg.DEFAULT_ZOOM);
  window.ApiWaspadaMap.initBaseTileLayers(map);
  const group = L.layerGroup().addTo(map);

  let currentStatus = "";

  function emptyState(title, text) {
    return `<div class="empty-state">${icon("map")}<strong>${title}</strong><span>${text}</span></div>`;
  }

  async function load() {
    const q = currentStatus ? `?status=${encodeURIComponent(currentStatus)}` : "";
    infoEl.textContent = "Memuat data…";

    try {
      const mapData = await apiFetch(`/api/dashboard/map${q}`);
      group.clearLayers();
      window.ApiWaspadaMap.renderReportsDistributionMap(map, group, mapData.markers, false);
    } catch (e) {
      console.error("Gagal memuat peta:", e);
    }

    try {
      const sep = q ? "&" : "?";
      const data = await apiFetch(`/api/reports${q}${sep}page_size=30`);
      const items = data.items || [];
      infoEl.textContent = items.length
        ? `Menampilkan ${items.length} dari ${data.total} laporan`
        : "Tidak ada laporan";

      if (items.length === 0) {
        listEl.innerHTML = emptyState("Belum ada laporan", "Tidak ada laporan untuk filter ini.");
        return;
      }

      listEl.innerHTML = items
        .map(
          (r) => `
          <article class="report-item" data-lat="${Number(r.latitude)}" data-lng="${Number(r.longitude)}">
            <img class="thumb" src="${escapeHtml(resolveMediaUrl(r.result_image_url || r.image_url))}" alt="" loading="lazy" onerror="this.style.visibility='hidden'" />
            <div class="meta">
              <div class="row"><span class="code">${escapeHtml(r.tracking_code)}</span>${getStatusBadgeHtml(r.status)}</div>
              <div class="excerpt">${escapeHtml(r.description)}</div>
              <div class="row">
                <span class="time">${icon("clock")} ${formatDateTimeWIB(r.created_at)}</span>
              </div>
              <div class="row" style="margin-top:.25rem">
                <button type="button" class="btn btn-secondary btn-sm" data-focus>${icon("pin")} Peta</button>
                <a class="btn btn-soft btn-sm" href="/tracking.html?code=${encodeURIComponent(r.tracking_code)}">Status ${icon("arrow-right")}</a>
              </div>
            </div>
          </article>`
        )
        .join("");

      listEl.querySelectorAll("[data-focus]").forEach((btn) => {
        btn.addEventListener("click", function () {
          const item = btn.closest(".report-item");
          const lat = parseFloat(item.dataset.lat);
          const lng = parseFloat(item.dataset.lng);
          if (isNaN(lat) || isNaN(lng)) return;
          map.setView([lat, lng], 16);
          group.eachLayer(function (layer) {
            const ll = layer.getLatLng && layer.getLatLng();
            if (ll && Math.abs(ll.lat - lat) < 1e-6 && Math.abs(ll.lng - lng) < 1e-6) layer.openPopup();
          });
          document.getElementById("publicDistributionMap").scrollIntoView({ behavior: "smooth", block: "center" });
        });
      });
    } catch (e) {
      infoEl.textContent = "Gagal memuat";
      listEl.innerHTML = emptyState("Data tidak dapat dimuat", "Periksa koneksi Anda lalu muat ulang halaman.");
      console.error("Gagal memuat daftar laporan:", e);
    }
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", function () {
      chips.forEach((c) => c.setAttribute("aria-pressed", "false"));
      chip.setAttribute("aria-pressed", "true");
      currentStatus = chip.dataset.status || "";
      load();
    });
  });

  load();
  setTimeout(() => map.invalidateSize(), 250);
});
