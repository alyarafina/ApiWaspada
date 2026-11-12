/**
 * Logika Halaman Beranda (`beranda.html`):
 * - Status layanan & modul AI dari `/api/health`
 * - Peta ringkas persebaran laporan dari `/api/dashboard/map` (publik)
 */
document.addEventListener("DOMContentLoaded", async function () {
  const { apiFetch } = window.ApiWaspadaUtils;
  const cfg = window.APIWASPADA_CONFIG;

  const sysText = document.getElementById("homeSystemStatus");
  const sysDot = document.getElementById("homeSystemDot");
  const aiText = document.getElementById("homeAiStatus");
  const aiDot = document.getElementById("homeAiDot");
  const totalEl = document.getElementById("homeTotalReports");
  const mapCountEl = document.getElementById("homeMapCount");
  const liveDot = document.getElementById("homeLiveDot");

  function setDot(el, state) {
    if (!el) return;
    el.classList.remove("ok", "warn", "off");
    el.classList.add(state);
  }
  function setText(el, value) {
    if (el) el.textContent = value;
  }

  // Status sistem hanya dimuat bila elemennya ada di halaman
  if (sysText || aiText || totalEl) {
    try {
      const health = await apiFetch("/api/health");
      const healthy = health.status === "healthy";
      setText(sysText, healthy ? "Online" : "Terbatas");
      setDot(sysDot, healthy ? "ok" : "warn");

      const aiOn = !!(health.ai_status && health.ai_status.ai_available);
      setText(aiText, aiOn ? "Aktif" : "Belum aktif");
      setDot(aiDot, aiOn ? "ok" : "warn");

      setText(totalEl, Number(health.total_reports || 0).toLocaleString("id-ID"));
    } catch (err) {
      setText(sysText, "Offline");
      setDot(sysDot, "off");
      setText(aiText, "Tidak diketahui");
      setDot(aiDot, "off");
      setDot(liveDot, "off");
      console.warn("Gagal memeriksa status sistem:", err);
    }
  }

  // Feed laporan terbaru di hero
  const feed = document.getElementById("heroFeed");
  if (feed) {
    const { escapeHtml, formatDateTimeWIB, getStatusBadgeHtml, resolveMediaUrl } = window.ApiWaspadaUtils;
    const icon = window.AWLayout ? window.AWLayout.icon : () => "";
    try {
      const data = await apiFetch("/api/reports?page=1&page_size=3");
      const items = data.items || [];
      if (items.length === 0) {
        feed.innerHTML = `<li class="live-empty">Belum ada laporan. Jadilah yang pertama membantu!</li>`;
      } else {
        feed.innerHTML = items
          .map(
            (r) => `
            <li class="live-item">
              <a href="/tracking.html?code=${encodeURIComponent(r.tracking_code)}">
                <img src="${escapeHtml(resolveMediaUrl(r.image_url))}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ph'}))" />
                <span class="meta">
                  <span class="top"><span class="code">${escapeHtml(r.tracking_code)}</span>${getStatusBadgeHtml(r.status)}</span>
                  <span class="desc">${escapeHtml(r.description)}</span>
                  <span class="time">${icon("clock")} ${formatDateTimeWIB(r.created_at)}</span>
                </span>
              </a>
            </li>`
          )
          .join("");
      }
    } catch (err) {
      feed.innerHTML = `<li class="live-empty">Data laporan belum dapat dimuat.</li>`;
      console.warn("Gagal memuat laporan terbaru:", err);
    }
  }

  const mapEl = document.getElementById("landingMap");
  if (!mapEl || !window.L) return;

  const map = L.map("landingMap", { scrollWheelZoom: false }).setView(
    [cfg.DEFAULT_LAT, cfg.DEFAULT_LNG],
    cfg.DEFAULT_ZOOM
  );
  window.ApiWaspadaMap.initBaseTileLayers(map);
  const group = L.layerGroup().addTo(map);
  map.on("focus click", function () {
    map.scrollWheelZoom.enable();
  });

  try {
    const data = await apiFetch("/api/dashboard/map");
    const markers = data.markers || [];
    const countBy = (st) => markers.filter((m) => String(m.status).toLowerCase() === st).length;
    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    setText("heroCountPending", countBy("pending"));
    setText("heroCountActive", countBy("verified"));
    setText("heroCountDone", countBy("completed"));
    if (mapCountEl) mapCountEl.textContent = markers.length.toLocaleString("id-ID");
    window.ApiWaspadaMap.renderReportsDistributionMap(map, group, markers, false);
  } catch (err) {
    if (mapCountEl) mapCountEl.textContent = "0";
    console.warn("Gagal memuat titik laporan:", err);
  }

  setTimeout(() => map.invalidateSize(), 250);
});
