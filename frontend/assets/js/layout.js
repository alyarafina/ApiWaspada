/**
 * Layout bersama ApiWaspada: ikon, header, tab bar bawah (HP), footer, dan toast.
 * Dimuat secara sinkron tepat setelah <body> agar navigasi langsung tampil tanpa kedip.
 *
 * Atribut pada <body>:
 *   data-area = "public" | "officer"
 *   data-page = kunci halaman aktif (home, report, tracking, map, guide, login,
 *               dash-summary, dash-map, dash-reports, dash-detail)
 */
(function () {
  "use strict";

  const P = {
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z"/>',
    flame: '<path d="M12 2c1 3.5 5 5.5 5 10.5A5 5 0 0 1 7 13c0-2.2 1-3.6 2-4.5.2 1.6 1 2.6 2 3 0-3.5-.5-6.5 1-9.5Z"/><path d="M12 22a3 3 0 0 1-3-3c0-1.7 1.5-2.8 3-4.5 1.5 1.7 3 2.8 3 4.5a3 3 0 0 1-3 3Z"/>',
    camera: '<path d="M14.5 4h-5L7.5 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3.5Z"/><circle cx="12" cy="13" r="3.5"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
    pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    map: '<path d="m9 4-6 2.5v14L9 18l6 2.5 6-2.5V4l-6 2.5Z"/><path d="M9 4v14M15 6.5v14"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    book: '<path d="M4 19.5V5a2 2 0 0 1 2-2h14v15H6.5A2.5 2.5 0 0 0 4 20.5 2.5 2.5 0 0 0 6.5 23H20v-5"/><path d="M8 7h8M8 11h6"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    "check-circle": '<circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "arrow-right": '<path d="M5 12h14M13 5l7 7-7 7"/>',
    "arrow-left": '<path d="M19 12H5M11 19l-7-7 7-7"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    crosshair: '<circle cx="12" cy="12" r="8"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="2"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    refresh: '<path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 12A9 9 0 0 1 18.5 5.8L21 8"/><path d="M21 3v5h-5M3 21v-5h5"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    chart: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M9.9 4.2A10 10 0 0 1 12 4c6.5 0 10 8 10 8a17 17 0 0 1-2.2 3.2M6.6 6.6A17 17 0 0 0 2 12s3.5 8 10 8a9.7 9.7 0 0 0 5.4-1.6"/><path d="M14.1 14.1a3 3 0 1 1-4.2-4.2M2 2l20 20"/>',
    copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    sparkles: '<path d="M12 3 10.1 8.1 5 10l5.1 1.9L12 17l1.9-5.1L19 10l-5.1-1.9Z"/><path d="M19 15v4M17 17h4M5 3v3M3.5 4.5h3"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    users: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M16 3.1a4 4 0 0 1 0 7.8M22 21a7 7 0 0 0-4-6.3"/>',
    layers: '<path d="m12 2 10 5-10 5L2 7Z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
    send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    help: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
    siren: '<path d="M7 18v-6a5 5 0 0 1 10 0v6"/><path d="M5 21h14v-3H5ZM12 2v2M4.2 5.2l1.4 1.4M19.8 5.2l-1.4 1.4"/>',
    wind: '<path d="M17.7 7.7A2.5 2.5 0 1 1 19.5 12H2M9.6 4.6A2 2 0 1 1 11 8H2M12.6 19.4A2 2 0 1 0 14 16H2"/>',
    building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/>',
    hourglass: '<path d="M5 22h14M5 2h14M17 22v-4.2a2 2 0 0 0-.6-1.4L12 12l-4.4 4.4a2 2 0 0 0-.6 1.4V22M7 2v4.2a2 2 0 0 0 .6 1.4L12 12l4.4-4.4a2 2 0 0 0 .6-1.4V2"/>',
    ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  };

  function icon(name, cls) {
    const body = P[name] || P.info;
    return `<svg class="ic ${cls || ""}" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }

  const BRAND_MARK = `
    <svg class="brand-mark" width="38" height="38" viewBox="0 0 48 48" aria-hidden="true">
      <defs><linearGradient id="awg" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#B91C1C"/><stop offset=".55" stop-color="#DC2626"/><stop offset="1" stop-color="#F97316"/></linearGradient>
      <linearGradient id="awi" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#F97316"/><stop offset="1" stop-color="#FACC15"/></linearGradient></defs>
      <rect x="2" y="2" width="44" height="44" rx="13" fill="url(#awg)"/>
      <path d="M24 8c-4.5 6.5-11 11-11 19.2C13 33.4 17.9 38.5 24 38.5S35 33.4 35 27.2c0-4.9-2.8-9.1-5.6-12-.3 3.1-2.2 5-3.9 5.9C26.8 16.8 26.2 11.8 24 8Z" fill="#fff"/>
      <path d="M24 20.5c-2.5 3.3-4.8 5.7-4.8 9 0 2.7 2.1 5 4.8 5s4.8-2.3 4.8-5c0-3-2.3-5.4-4.8-9Z" fill="url(#awi)"/>
    </svg>`;

  function brand(href, tag) {
    return `
      <a href="${href}" class="brand" aria-label="ApiWaspada — ke halaman utama">
        ${BRAND_MARK}
        <span class="brand-text">
          <span class="brand-name">Api<span>Waspada</span>${tag ? `<span class="brand-tag">${tag}</span>` : ""}</span>
          <span class="brand-sub">Kota Jambi</span>
        </span>
      </a>`;
  }

  const PUBLIC_NAV = [
    { key: "home", href: "/beranda.html", label: "Beranda", icon: "home" },
    { key: "report", href: "/report.html", label: "Lapor", long: "Lapor Kebakaran", icon: "flame", cta: true },
    { key: "tracking", href: "/tracking.html", label: "Lacak", long: "Lacak Laporan", icon: "search" },
    { key: "map", href: "/peta.html", label: "Peta", long: "Peta Laporan", icon: "map" },
    { key: "guide", href: "/panduan.html", label: "Panduan", icon: "book" },
  ];

  const OFFICER_NAV = [
    { key: "dash-summary", href: "/dashboard.html", label: "Ringkasan", icon: "grid" },
    { key: "dash-reports", href: "/dashboard-laporan.html", label: "Laporan", long: "Kelola Laporan", icon: "list" },
    { key: "dash-map", href: "/dashboard-peta.html", label: "Peta", long: "Peta Sebaran", icon: "map" },
  ];

  const body = document.body;
  const area = body.dataset.area || "public";
  let page = body.dataset.page || "";
  if (page === "dash-detail") page = "dash-reports";

  function navLinks(items) {
    return items
      .map(
        (n) =>
          `<a href="${n.href}"${n.key === page ? ' aria-current="page"' : ""}>${icon(n.icon)}${n.long ? `<span class="l-short">${n.label}</span><span class="l-long">${n.long}</span>` : `<span>${n.label}</span>`}</a>`
      )
      .join("");
  }

  function tabLinks(items) {
    return items
      .map((n) => {
        const cur = n.key === page ? ' aria-current="page"' : "";
        if (n.cta) {
          return `<a href="${n.href}" class="tab-cta"${cur}><span class="bubble">${icon(n.icon)}</span><span>${n.label}</span></a>`;
        }
        return `<a href="${n.href}"${cur}>${icon(n.icon)}<span>${n.label}</span></a>`;
      })
      .join("");
  }

  let headerHtml = "";
  let tabbarHtml = "";

  if (area === "gate") {
    headerHtml = "";
  } else if (area === "officer") {
    headerHtml = `
      <header class="site-header">
        <div class="container">
          ${brand("/dashboard.html", "Petugas")}
          <nav class="main-nav" aria-label="Navigasi petugas">${navLinks(OFFICER_NAV)}</nav>
          <div class="header-actions">
            <span class="officer-chip"><span class="avatar" id="officerAvatar">P</span><span class="name" id="officerNameBadge">Petugas</span></span>
            <button type="button" class="btn btn-secondary btn-sm" data-logout>${icon("logout")}<span>Keluar</span></button>
          </div>
        </div>
      </header>`;
    tabbarHtml = `<nav class="tabbar" aria-label="Navigasi petugas">${tabLinks(OFFICER_NAV)}<a href="/beranda.html">${icon("users")}<span>Publik</span></a></nav>`;
  } else if (page === "login") {
    headerHtml = `
      <header class="site-header">
        <div class="container">
          ${brand("/index.html")}
          <div class="header-actions">
            <a href="/index.html" class="btn btn-secondary btn-sm">${icon("arrow-left")}<span>Kembali</span></a>
          </div>
        </div>
      </header>`;
  } else {
    headerHtml = `
      <header class="site-header">
        <div class="container">
          ${brand("/beranda.html")}
          <nav class="main-nav" aria-label="Navigasi utama">${navLinks(PUBLIC_NAV)}</nav>
          <div class="header-actions">
            <a href="/login.html" class="officer-link" aria-label="Masuk sebagai petugas" title="Masuk sebagai petugas">
              ${icon("shield")}<span>Petugas</span>
            </a>
            <a href="tel:113" class="emergency-pill" aria-label="Telepon Pemadam Kebakaran 113">
              <span class="dot">${icon("phone")}</span><span><span class="label-long">Darurat </span>113</span>
            </a>
          </div>
        </div>
      </header>`;
    tabbarHtml = `<nav class="tabbar" aria-label="Navigasi utama">${tabLinks(PUBLIC_NAV)}</nav>`;
  }

  // Sisipkan header segera (skrip ini berada tepat setelah <body>)
  const self = document.currentScript;
  if (self && self.parentNode === body) {
    self.insertAdjacentHTML("afterend", headerHtml);
  } else {
    body.insertAdjacentHTML("afterbegin", headerHtml);
  }

  function footerHtml() {
    if (area === "gate") return "";
    if (area === "officer" || page === "login") {
      return `
        <footer class="site-footer" style="margin-top:2rem">
          <div class="container" style="padding-top:1.25rem;padding-bottom:1.25rem">
            <div class="footer-bottom" style="border:0;margin:0;padding:0">
              <span>&copy; 2026 ApiWaspada Kota Jambi &middot; Portal Verifikasi Petugas</span>
              <span>Hasil AI adalah indikasi awal &mdash; keputusan akhir di tangan petugas.</span>
            </div>
          </div>
        </footer>`;
    }
    return `
      <footer class="site-footer">
        <div class="container">
          <div class="footer-grid">
            <div>
              ${brand("/beranda.html")}
              <p class="footer-about">Lapor kebakaran di Kota Jambi, cepat &amp; mudah.</p>
            </div>
            <div>
              <h4>Menu</h4>
              <ul>
                <li><a href="/report.html">Lapor Kebakaran</a></li>
                <li><a href="/tracking.html">Lacak Laporan</a></li>
                <li><a href="/peta.html">Peta Laporan</a></li>
                <li><a href="/panduan.html">Panduan &amp; FAQ</a></li>
                <li><a href="/login.html">Masuk Petugas</a></li>
                <li><a href="/index.html">Ganti peran</a></li>
              </ul>
            </div>
            <div>
              <h4>Nomor Darurat</h4>
              <div class="footer-emergency">
                <a href="tel:113"><span>Pemadam Kebakaran</span><strong>113</strong></a>
                <a href="tel:112"><span>Panggilan Darurat</span><strong>112</strong></a>
                <a href="tel:110"><span>Polisi</span><strong>110</strong></a>
              </div>
            </div>
          </div>
          <div class="footer-bottom">
            <span>&copy; 2026 ApiWaspada Kota Jambi</span>
            <span>Darurat? Telepon 113.</span>
          </div>
        </div>
      </footer>`;
  }

  function hydrateIcons(root) {
    (root || document).querySelectorAll("[data-icon]").forEach((el) => {
      if (el.dataset.iconDone) return;
      el.outerHTML = icon(el.dataset.icon, el.className);
    });
  }

  function toast(message) {
    let wrap = document.querySelector(".toast-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "toast-wrap";
      wrap.setAttribute("role", "status");
      wrap.setAttribute("aria-live", "polite");
      document.body.appendChild(wrap);
    }
    const t = document.createElement("div");
    t.className = "toast";
    t.innerHTML = `${icon("check-circle")}<span></span>`;
    t.querySelector("span").textContent = message;
    wrap.appendChild(t);
    setTimeout(() => {
      t.style.transition = "opacity .3s";
      t.style.opacity = "0";
      setTimeout(() => t.remove(), 320);
    }, 2400);
  }

  async function copyText(text) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      toast("Disalin ke papan klip");
      return true;
    } catch (e) {
      return false;
    }
  }

  /** Penyimpanan kode laporan milik perangkat ini (hanya kenyamanan, aman bila gagal). */
  const MY_KEY = "apiwaspada_my_reports";
  function getMyReports() {
    try {
      const raw = localStorage.getItem(MY_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }
  function saveMyReport(code) {
    if (!code || code === "-") return;
    try {
      const list = getMyReports().filter((c) => c !== code);
      list.unshift(code);
      localStorage.setItem(MY_KEY, JSON.stringify(list.slice(0, 6)));
    } catch (e) {
      /* abaikan */
    }
  }

  window.AWLayout = { icon, hydrateIcons, toast, copyText, getMyReports, saveMyReport };

  document.addEventListener("DOMContentLoaded", function () {
    if (tabbarHtml) {
      body.insertAdjacentHTML("beforeend", tabbarHtml);
      body.classList.add("has-tabbar");
    }
    const main = document.querySelector("main");
    if (main) main.insertAdjacentHTML("afterend", footerHtml());
    else body.insertAdjacentHTML("beforeend", footerHtml());

    hydrateIcons();

    document.querySelectorAll("[data-logout]").forEach((btn) => {
      btn.addEventListener("click", function () {
        if (window.ApiWaspadaAuth) window.ApiWaspadaAuth.performOfficerLogout();
      });
    });

    document.querySelectorAll("[data-copy-from]").forEach((btn) => {
      btn.addEventListener("click", function () {
        const src = document.getElementById(btn.dataset.copyFrom);
        const val = src ? src.textContent.trim() : "";
        if (val && val !== "-") copyText(val);
      });
    });
  });
})();
