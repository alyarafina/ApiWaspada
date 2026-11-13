/**
 * UC-10: Admin Sistem mengelola akun petugas dan melihat rekapitulasi laporan.
 */
document.addEventListener("DOMContentLoaded", async function () {
  const profile = await window.ApiWaspadaAuth.verifyOfficerSessionOrRedirect(["admin"]);
  if (!profile) return;

  const { apiFetch, escapeHtml, getOfficerToken } = window.ApiWaspadaUtils;
  const alertEl = document.getElementById("adminAlert");
  const ROLE_LABEL = { admin: "Admin sistem", operator: "Operator JCOC 112", damkar: "Petugas Damkar" };

  function show(msg, type) {
    alertEl.className = `alert alert-${type}`;
    alertEl.textContent = msg;
    alertEl.classList.remove("hidden");
    alertEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ---------- Rekap ----------
  async function loadRecap() {
    const r = await apiFetch("/api/admin/recap");
    const s = r.by_status || {};
    const kpis = [
      ["Total laporan", r.total_reports, ""],
      ["Menunggu verifikasi", s.pending || 0, "kpi-pending"],
      ["Sedang ditangani", (s.verified || 0) + (s.handling || 0), "kpi-verified"],
      ["Selesai", s.completed || 0, "kpi-completed"],
      ["Ditolak / hoaks", `${s.rejected || 0} <small>(${Math.round((r.rejected_ratio || 0) * 100)}%)</small>`, "kpi-rejected"],
    ];
    const kpiEl = document.getElementById("recapKpi");
    kpiEl.innerHTML = kpis
      .map(([l, v, c]) => `<div class="kpi-card ${c}"><div class="kpi-label">${l}</div><div class="kpi-value">${v}</div></div>`)
      .join("");
    if (r.avg_minutes_to_decision != null) {
      kpiEl.insertAdjacentHTML(
        "beforeend",
        `<div class="kpi-card"><div class="kpi-label">Rata-rata lapor sampai diputuskan</div><div class="kpi-value">${r.avg_minutes_to_decision.toFixed(1)} <small>menit</small></div></div>`
      );
    }
    const months = Object.entries(r.by_month || {});
    const max = Math.max(1, ...months.map(([, n]) => n));
    document.getElementById("recapMonths").innerHTML = months.length
      ? months
          .map(([m, n]) => {
            const label = new Date(m + "-01T00:00:00").toLocaleDateString("id-ID", { month: "short", year: "numeric" });
            return `<li><span class="m">${label}</span><span class="bar"><span style="width:${(n / max) * 100}%"></span></span><span class="n">${n}</span></li>`;
          })
          .join("")
      : `<li class="form-hint">Belum ada laporan.</li>`;
  }

  document.getElementById("btnCsv").addEventListener("click", async function () {
    try {
      const res = await fetch(`${window.APIWASPADA_CONFIG.API_BASE_URL}/api/admin/recap.csv`, {
        headers: { Authorization: `Bearer ${getOfficerToken()}` },
      });
      if (!res.ok) throw new Error(`Gagal mengunduh (HTTP ${res.status})`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `rekap-apiwaspada-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) {
      show(err.message, "error");
    }
  });

  // ---------- Akun ----------
  async function loadOfficers() {
    const items = await apiFetch("/api/admin/officers");
    const list = document.getElementById("officerList");
    list.innerHTML = items
      .map(
        (o) => `<li>
          <div><strong>${escapeHtml(o.full_name)}</strong>${o.is_active ? "" : ' <span class="badge badge-rejected">Nonaktif</span>'}
            <span><span class="code">${escapeHtml(o.username)}</span> &middot; ${ROLE_LABEL[o.role] || escapeHtml(o.role)}</span></div>
          ${o.id === profile.id ? '<span class="form-hint">Akun Anda</span>' : `<button type="button" class="btn btn-secondary btn-sm" data-toggle-officer="${o.id}" data-active="${o.is_active}">${o.is_active ? "Nonaktifkan" : "Aktifkan"}</button>`}
        </li>`
      )
      .join("");
    list.querySelectorAll("[data-toggle-officer]").forEach((b) =>
      b.addEventListener("click", async function () {
        try {
          await apiFetch(`/api/admin/officers/${b.dataset.toggleOfficer}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_active: b.dataset.active !== "true" }),
          });
          await loadOfficers();
        } catch (err) {
          show(err.message, "error");
        }
      })
    );
  }

  document.getElementById("officerForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {
      full_name: document.getElementById("ofName").value.trim(),
      username: document.getElementById("ofUser").value.trim(),
      password: document.getElementById("ofPass").value,
      role: document.getElementById("ofRole").value,
    };
    if (body.password.length < 8) return show("Password minimal 8 karakter.", "error");
    try {
      await apiFetch("/api/admin/officers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      show(`Akun ${body.username} dibuat.`, "success");
      e.target.reset();
      await loadOfficers();
    } catch (err) {
      show(err.message, "error");
    }
  });

  try {
    await Promise.all([loadRecap(), loadOfficers()]);
  } catch (err) {
    show(err.message || "Gagal memuat data admin.", "error");
  }
});
