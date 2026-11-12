/**
 * Peningkatan tampilan halaman Lapor (`report.html`) — tidak mengubah alur deteksi di report.js.
 * - Indikator kemajuan (Foto, Keterangan, Lokasi)
 * - Dropzone dapat dibuka dengan keyboard
 * - Menyimpan kode laporan ke perangkat setelah laporan berhasil dikirim
 * - Tombol "Buat laporan baru"
 */
document.addEventListener("DOMContentLoaded", function () {
  const $ = (id) => document.getElementById(id);

  const steps = {
    photo: document.querySelector('.progress-step[data-step="photo"]'),
    desc: document.querySelector('.progress-step[data-step="desc"]'),
    loc: document.querySelector('.progress-step[data-step="loc"]'),
  };

  const previewWrap = $("imagePreviewWrapper");
  const desc = $("description");
  const lat = $("latitude");
  const lng = $("longitude");

  function refreshProgress() {
    const hasPhoto = previewWrap && !previewWrap.classList.contains("hidden");
    const hasDesc = desc && desc.value.trim().length >= 5;
    const hasLoc = lat && lng && lat.value !== "" && lng.value !== "" && !isNaN(parseFloat(lat.value)) && !isNaN(parseFloat(lng.value));
    if (steps.photo) steps.photo.classList.toggle("done", !!hasPhoto);
    if (steps.desc) steps.desc.classList.toggle("done", !!hasDesc);
    if (steps.loc) steps.loc.classList.toggle("done", !!hasLoc);
  }

  ["input", "change"].forEach((ev) => {
    [desc, lat, lng].forEach((el) => el && el.addEventListener(ev, refreshProgress));
  });

  // report.js mengisi koordinat & pratinjau secara langsung (tanpa event), jadi pantau perubahannya.
  if (previewWrap) new MutationObserver(refreshProgress).observe(previewWrap, { attributes: true, attributeFilter: ["class"] });
  const gpsMsg = $("gpsStatusMsg");
  if (gpsMsg) new MutationObserver(refreshProgress).observe(gpsMsg, { childList: true, characterData: true, subtree: true });
  refreshProgress();

  // Dropzone: Enter / Spasi membuka pemilih file
  const dz = $("uploadDropzone");
  const input = $("imageInput");
  if (dz && input) {
    dz.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
  }

  // Setelah laporan berhasil: simpan kode & ringkas tampilan formulir
  const successCard = $("reportSuccessCard");
  const form = $("reportForm");
  const progress = $("reportProgress");
  if (successCard) {
    new MutationObserver(function () {
      if (successCard.classList.contains("hidden")) return;
      const code = ($("createdTrackingCode") || {}).textContent;
      if (window.AWLayout && code) window.AWLayout.saveMyReport(code.trim());
      if (form) form.classList.add("hidden");
      if (progress) progress.classList.add("hidden");
    }).observe(successCard, { attributes: true, attributeFilter: ["class"] });
  }

  const btnNew = $("btnNewReport");
  if (btnNew) {
    btnNew.addEventListener("click", function () {
      window.location.href = "/report.html";
    });
  }
});
