/**
 * Operator: tugaskan laporan terverifikasi ke petugas Damkar tertentu atau ke semua petugas.
 * Dipanggil ulang setiap kali detail laporan dirender (event `aw:report-loaded`).
 */
(function () {
  let officersCache = null;

  async function render(report) {
    const { apiFetch, escapeHtml } = window.ApiWaspadaUtils;
    const card = document.getElementById("assignCard");
    if (!card) return;
    const info = document.getElementById("assignInfo");
    const listEl = document.getElementById("assignList");
    const form = document.getElementById("assignForm");
    const alertEl = document.getElementById("assignAlert");
    const btnAll = document.getElementById("btnAssignAll");
    const btnSelectAll = document.getElementById("btnSelectAllOfficers");
    const btnSend = document.getElementById("btnAssignSelected");

    const show = (msg, type) => {
      alertEl.className = `alert alert-${type}`;
      alertEl.textContent = msg;
    };
    const assigned = new Set((report.assigned_officers || []).map((o) => o.id));
    const current = (report.assigned_officers || []).map((o) => escapeHtml(o.full_name)).join(", ");

    if (!["verified", "handling"].includes(report.status)) {
      form.classList.add("hidden");
      info.innerHTML =
        report.status === "completed"
          ? "Laporan sudah selesai ditangani."
          : report.status === "rejected"
            ? "Laporan ditolak, tidak perlu menugaskan Tim Damkar."
            : "<strong>Verifikasi laporan dulu.</strong> Setelah statusnya Terverifikasi, petugas Damkar bisa ditugaskan di sini.";
      return;
    }
    form.classList.remove("hidden");
    info.innerHTML = current
      ? `Ditugaskan ke <strong>${current}</strong>. Ubah pilihan lalu kirim ulang untuk mengganti.`
      : "Pilih petugas yang dikirim ke lokasi. Mereka melihat laporan, rute, dan lokasinya di HP.";

    try {
      if (!officersCache) officersCache = await apiFetch("/api/damkar/officers");
    } catch (err) {
      listEl.innerHTML = `<p class="form-hint">Daftar petugas gagal dimuat: ${escapeHtml(err.message)}</p>`;
      return;
    }
    if (!officersCache.length) {
      listEl.innerHTML =
        '<p class="form-hint">Belum ada akun Petugas Damkar yang aktif. Admin bisa membuatnya di halaman Kelola dan rekap.</p>';
      btnAll.disabled = btnSend.disabled = btnSelectAll.disabled = true;
      return;
    }
    listEl.innerHTML = officersCache
      .map(
        (o) => `<label class="pick-option">
          <input type="checkbox" name="officerId" value="${o.id}" ${assigned.has(o.id) ? "checked" : ""} />
          <span class="pick-main"><strong>${escapeHtml(o.full_name)}</strong><span class="code">${escapeHtml(o.username)}</span></span>
        </label>`
      )
      .join("");
    btnAll.textContent = `Kirim ke semua petugas (${officersCache.length})`;

    async function send(body) {
      btnAll.disabled = btnSend.disabled = true;
      try {
        await apiFetch(`/api/damkar/assign/${encodeURIComponent(report.tracking_code)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(Object.assign({ note: document.getElementById("assignNote").value.trim() }, body)),
        });
        show("Tugas terkirim. Petugas melihatnya di halaman Tugas Damkar di HP mereka.", "success");
        setTimeout(() => window.location.reload(), 900);
      } catch (err) {
        show(err.message || "Gagal menugaskan petugas.", "error");
        btnAll.disabled = btnSend.disabled = false;
      }
    }

    if (form.dataset.bound) return;
    form.dataset.bound = "1";
    btnSelectAll.addEventListener("click", function () {
      const boxes = listEl.querySelectorAll('input[name="officerId"]');
      const allOn = Array.from(boxes).every((b) => b.checked);
      boxes.forEach((b) => (b.checked = !allOn));
      btnSelectAll.textContent = allOn ? "Pilih semua petugas" : "Batalkan semua";
    });
    btnAll.addEventListener("click", () => send({ all: true }));
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const ids = Array.from(listEl.querySelectorAll('input[name="officerId"]:checked')).map((b) => Number(b.value));
      if (!ids.length) return show("Pilih minimal satu petugas, atau gunakan tombol kirim ke semua petugas.", "error");
      send({ officer_ids: ids });
    });
  }

  document.addEventListener("aw:report-loaded", (ev) => render(ev.detail));
})();
