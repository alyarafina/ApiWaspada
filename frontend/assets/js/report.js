/**
 * Logika Halaman Form Pelaporan Kebakaran & Deteksi Visual AI (`report.html`).
 * Mengelola:
 * - Upload foto & kamera perangkat (WebRTC getUserMedia)
 * - Validasi ukuran dan tipe file gambar
 * - Pengambilan koordinat GPS Browser Geolocation API & pemilihan titik di peta Leaflet
 * - Pengujian deteksi cepat (`/api/detect`) & pengiriman laporan lengkap (`/api/reports`)
 * - Penampilan hasil deteksi visual (gambar asli, gambar bounding box, kelas, confidence, waktu proses)
 */

document.addEventListener("DOMContentLoaded", function () {
  const { apiFetch, escapeHtml, formatDateTimeWIB, getStatusBadgeHtml, getDetectionBadgeHtml, resolveMediaUrl } =
    window.ApiWaspadaUtils;
  const cfg = window.APIWASPADA_CONFIG;

  // Elemen DOM
  const aiStatusBanner = document.getElementById("aiStatusBanner");
  const reportForm = document.getElementById("reportForm");
  const imageInput = document.getElementById("imageInput");
  const uploadDropzone = document.getElementById("uploadDropzone");
  const imagePreviewWrapper = document.getElementById("imagePreviewWrapper");
  const imagePreviewEl = document.getElementById("imagePreview");
  const selectedFileInfo = document.getElementById("selectedFileInfo");

  // Kamera perangkat
  const btnOpenCamera = document.getElementById("btnOpenCamera");
  const btnCapturePhoto = document.getElementById("btnCapturePhoto");
  const btnCloseCamera = document.getElementById("btnCloseCamera");
  const cameraContainer = document.getElementById("cameraContainer");
  const cameraVideo = document.getElementById("cameraVideo");
  const cameraCanvas = document.getElementById("cameraCanvas");

  // Input form & Lokasi
  const reporterNameInput = document.getElementById("reporterName");
  const descriptionInput = document.getElementById("description");
  const descCharCount = document.getElementById("descCharCount");
  const latitudeInput = document.getElementById("latitude");
  const longitudeInput = document.getElementById("longitude");
  const btnGetGps = document.getElementById("btnGetGps");
  const btnSetJambiCenter = document.getElementById("btnSetJambiCenter");
  const gpsStatusMsg = document.getElementById("gpsStatusMsg");

  // Tombol aksi & feedback
  const btnPreviewAi = document.getElementById("btnPreviewAi");
  const btnSubmitReport = document.getElementById("btnSubmitReport");
  const formAlert = document.getElementById("formAlert");

  // Bagian Hasil Deteksi & Status Laporan
  const detectionResultSection = document.getElementById("detectionResultSection");
  const resOriginalImg = document.getElementById("resOriginalImg");
  const resAnnotatedImg = document.getElementById("resAnnotatedImg");
  const resStatusBadge = document.getElementById("resStatusBadge");
  const resConfidenceVal = document.getElementById("resConfidenceVal");
  const resInferenceTime = document.getElementById("resInferenceTime");
  const resBboxTableBody = document.getElementById("resBboxTableBody");

  const reportSuccessCard = document.getElementById("reportSuccessCard");
  const createdReportId = document.getElementById("createdReportId");
  const createdTrackingCode = document.getElementById("createdTrackingCode");
  const createdTime = document.getElementById("createdTime");
  const createdStatusBadge = document.getElementById("createdStatusBadge");
  const createdDetectionSummary = document.getElementById("createdDetectionSummary");
  const btnTrackCreatedReport = document.getElementById("btnTrackCreatedReport");

  let selectedImageFile = null;
  let mediaStream = null;

  function showAlert(message, type = "error") {
    formAlert.className = `alert alert-${type}`;
    formAlert.innerHTML = escapeHtml(message);
    formAlert.classList.remove("hidden");
    formAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function hideAlert() {
    formAlert.classList.add("hidden");
  }

  // 1. Periksa Status Model AI YOLO di Backend
  async function checkAiModelStatus() {
    try {
      const status = await apiFetch("/api/detect/status");
      if (status.ai_available) {
        aiStatusBanner.className = "alert alert-success";
        aiStatusBanner.innerHTML =
          `<span><strong>AI aktif</strong> &mdash; foto dicek otomatis.</span>`;
      } else {
        aiStatusBanner.className = "alert alert-info";
        aiStatusBanner.innerHTML =
          `<span><strong>AI sedang tidak aktif.</strong> Laporan tetap bisa dikirim.</span>`;
      }
      aiStatusBanner.classList.remove("hidden");
    } catch (e) {
      aiStatusBanner.className = "alert alert-info";
      aiStatusBanner.innerHTML =
        "<span>Laporan tetap bisa dikirim.</span>";
      aiStatusBanner.classList.remove("hidden");
    }
  }
  checkAiModelStatus();

  // 2. Inisialisasi Peta Pemilih Lokasi (Leaflet.js)
  const picker = window.ApiWaspadaMap.initReportPickerMap(
    "reportPickerMap",
    function (lat, lng) {
      latitudeInput.value = lat;
      longitudeInput.value = lng;
      gpsStatusMsg.textContent = "Lokasi dipilih ✓";
    }
  );

  latitudeInput.addEventListener("change", function () {
    const lat = parseFloat(latitudeInput.value);
    const lng = parseFloat(longitudeInput.value);
    if (!isNaN(lat) && !isNaN(lng)) {
      picker.setPickerCoordinate(lat, lng, true);
    }
  });

  longitudeInput.addEventListener("change", function () {
    const lat = parseFloat(latitudeInput.value);
    const lng = parseFloat(longitudeInput.value);
    if (!isNaN(lat) && !isNaN(lng)) {
      picker.setPickerCoordinate(lat, lng, true);
    }
  });

  btnSetJambiCenter.addEventListener("click", function () {
    picker.setPickerCoordinate(cfg.DEFAULT_LAT, cfg.DEFAULT_LNG, true);
    gpsStatusMsg.textContent =
      "Geser pin ke lokasi kejadian.";
  });

  // 3. Browser Geolocation API
  btnGetGps.addEventListener("click", function () {
    if (!navigator.geolocation) {
      showAlert(
        "Browser Anda tidak mendukung fitur Geolocation otomatis. Silakan klik langsung pada peta atau isi koordinat secara manual."
      );
      return;
    }
    gpsStatusMsg.textContent = "Mencari lokasi Anda…";
    btnGetGps.disabled = true;

    navigator.geolocation.getCurrentPosition(
      function (pos) {
        btnGetGps.disabled = false;
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lng = Number(pos.coords.longitude.toFixed(6));
        picker.setPickerCoordinate(lat, lng, true);
        gpsStatusMsg.textContent = `Lokasi ditemukan ✓ (±${Math.round(pos.coords.accuracy)} m)`;
      },
      function (err) {
        btnGetGps.disabled = false;
        gpsStatusMsg.textContent =
          "GPS gagal. Ketuk peta saja.";
        showAlert(
          `Tidak dapat mengambil GPS otomatis (${err.message}). Anda dapat memilih lokasi dengan mengklik peta Kota Jambi atau mengisi koordinat manual.`,
          "info"
        );
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  });

  // 4. Validasi & Preview Gambar
  function handleSelectedFile(file) {
    hideAlert();
    if (!file) return;

    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (!["jpg", "jpeg", "png"].includes(ext) || !cfg.ALLOWED_TYPES.includes(file.type)) {
      showAlert("Format gambar tidak valid. Gunakan file JPG, JPEG, atau PNG.");
      return;
    }

    const maxBytes = cfg.MAX_UPLOAD_SIZE_MB * 1024 * 1024;
    if (file.size > maxBytes) {
      showAlert(`Ukuran file terlalu besar (${(file.size / 1024 / 1024).toFixed(2)} MB). Maksimal ${cfg.MAX_UPLOAD_SIZE_MB} MB.`);
      return;
    }

    selectedImageFile = file;
    const reader = new FileReader();
    reader.onload = function (ev) {
      imagePreviewEl.src = ev.target.result;
      imagePreviewWrapper.classList.remove("hidden");
      selectedFileInfo.textContent = `File terpilih: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    };
    reader.readAsDataURL(file);
  }

  uploadDropzone.addEventListener("click", function () {
    imageInput.click();
  });

  imageInput.addEventListener("change", function (ev) {
    if (ev.target.files && ev.target.files[0]) {
      handleSelectedFile(ev.target.files[0]);
    }
  });

  uploadDropzone.addEventListener("dragover", function (ev) {
    ev.preventDefault();
    uploadDropzone.classList.add("dragover");
  });

  uploadDropzone.addEventListener("dragleave", function () {
    uploadDropzone.classList.remove("dragover");
  });

  uploadDropzone.addEventListener("drop", function (ev) {
    ev.preventDefault();
    uploadDropzone.classList.remove("dragover");
    if (ev.dataTransfer.files && ev.dataTransfer.files[0]) {
      handleSelectedFile(ev.dataTransfer.files[0]);
    }
  });

  // 5. Kamera Perangkat (WebRTC)
  function stopCameraStream() {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }
    cameraContainer.classList.add("hidden");
  }

  btnOpenCamera.addEventListener("click", async function () {
    hideAlert();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      imageInput.setAttribute("capture", "environment");
      imageInput.click();
      return;
    }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      cameraVideo.srcObject = mediaStream;
      cameraContainer.classList.remove("hidden");
    } catch (err) {
      showAlert(
        "Kamera langsung tidak dapat diakses oleh browser. Membuka pemilih file gambar perangkat...",
        "info"
      );
      imageInput.click();
    }
  });

  btnCapturePhoto.addEventListener("click", function () {
    if (!mediaStream) return;
    const vw = cameraVideo.videoWidth || 640;
    const vh = cameraVideo.videoHeight || 480;
    cameraCanvas.width = vw;
    cameraCanvas.height = vh;
    const ctx = cameraCanvas.getContext("2d");
    ctx.drawImage(cameraVideo, 0, 0, vw, vh);
    cameraCanvas.toBlob(
      function (blob) {
        if (blob) {
          const capturedFile = new File(
            [blob],
            `kamera_${Date.now()}.jpg`,
            { type: "image/jpeg" }
          );
          handleSelectedFile(capturedFile);
          stopCameraStream();
        }
      },
      "image/jpeg",
      0.92
    );
  });

  btnCloseCamera.addEventListener("click", stopCameraStream);

  // 6. Hitung karakter deskripsi
  descriptionInput.addEventListener("input", function () {
    descCharCount.textContent = `${descriptionInput.value.length} / 1000 karakter`;
  });

  // 7. Render Hasil Deteksi Visual ke UI
  function renderDetectionResultToUi(detData) {
    resOriginalImg.src = resolveMediaUrl(detData.original_image_url || detData.image_url);
    resAnnotatedImg.src = resolveMediaUrl(detData.result_image_url || detData.image_url);

    const statusStr = detData.detection_status || detData.detection_result;
    resStatusBadge.innerHTML = getDetectionBadgeHtml(statusStr);

    const confPct = (Number(detData.highest_confidence ?? detData.detection_confidence ?? 0) * 100).toFixed(1);
    resConfidenceVal.textContent = `${confPct}%`;
    resInferenceTime.textContent = `${Number(detData.inference_time_ms || 0).toFixed(1)} ms`;

    const boxes = detData.detections || [];
    if (boxes.length === 0) {
      resBboxTableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align:center; color:#64748B;">
            Tidak ada tanda api/asap yang jelas.
          </td>
        </tr>`;
    } else {
      resBboxTableBody.innerHTML = boxes
        .map(
          (b, idx) => `
          <tr>
            <td data-label="No">${idx + 1}</td>
            <td data-label="Objek"><strong>${escapeHtml(b.class_name)}</strong> (ID: ${b.class_id})</td>
            <td data-label="Keyakinan">${(Number(b.confidence) * 100).toFixed(1)}%</td>
            <td data-label="Posisi"><code>[${b.bbox_xyxy.join(", ")}]</code></td>
          </tr>`
        )
        .join("");
    }

    detectionResultSection.classList.remove("hidden");
    detectionResultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // 8. Tombol Uji Deteksi Visual Saja (`POST /api/detect`)
  btnPreviewAi.addEventListener("click", async function () {
    hideAlert();
    if (!selectedImageFile) {
      showAlert("Silakan pilih atau ambil foto dugaan kebakaran terlebih dahulu.");
      return;
    }

    const origText = btnPreviewAi.innerHTML;
    btnPreviewAi.disabled = true;
    btnPreviewAi.innerHTML = `<span class="loading-spinner"></span> AI sedang memeriksa foto...`;

    try {
      const formData = new FormData();
      formData.append("image", selectedImageFile);
      const res = await apiFetch("/api/detect", {
        method: "POST",
        body: formData,
      });
      renderDetectionResultToUi(res);
    } catch (err) {
      showAlert(err.message || "Gagal memproses deteksi gambar.");
    } finally {
      btnPreviewAi.disabled = false;
      btnPreviewAi.innerHTML = origText;
    }
  });

  // 9. Submit Laporan Lengkap (`POST /api/reports`)
  reportForm.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    hideAlert();

    if (!selectedImageFile) {
      showAlert("Foto kejadian wajib diunggah sebelum mengirim laporan.");
      return;
    }

    const desc = descriptionInput.value.trim();
    if (desc.length < 5) {
      showAlert("Deskripsi kejadian wajib diisi minimal 5 karakter.");
      return;
    }

    const lat = parseFloat(latitudeInput.value);
    const lng = parseFloat(longitudeInput.value);
    if (isNaN(lat) || isNaN(lng)) {
      showAlert(
        "Koordinat lokasi (Latitude dan Longitude) wajib diisi. Gunakan tombol Ambil Lokasi GPS atau klik pada peta."
      );
      return;
    }

    const origBtnHtml = btnSubmitReport.innerHTML;
    btnSubmitReport.disabled = true;
    btnSubmitReport.innerHTML = `<span class="loading-spinner"></span> Mengirim &amp; memeriksa foto...`;

    try {
      const formData = new FormData();
      formData.append("image", selectedImageFile);
      formData.append("description", desc);
      formData.append("latitude", String(lat));
      formData.append("longitude", String(lng));
      formData.append("reporter_name", reporterNameInput.value.trim() || "Masyarakat");

      const created = await apiFetch("/api/reports", {
        method: "POST",
        body: formData,
      });

      renderDetectionResultToUi(created);

      createdReportId.textContent = `#${created.id}`;
      createdTrackingCode.textContent = created.tracking_code;
      createdTime.textContent = formatDateTimeWIB(created.created_at);
      createdStatusBadge.innerHTML = getStatusBadgeHtml(created.status);
      createdDetectionSummary.innerHTML =
        `${getDetectionBadgeHtml(created.detection_result)} ` +
        `<span style="margin-left:6px; font-weight:600;">Keyakinan: ${(Number(created.detection_confidence) * 100).toFixed(1)}%</span>`;
      btnTrackCreatedReport.href = `/tracking.html?code=${encodeURIComponent(created.tracking_code)}`;

      reportSuccessCard.classList.remove("hidden");
      reportSuccessCard.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      showAlert(err.message || "Gagal mengirim laporan kebakaran.");
    } finally {
      btnSubmitReport.disabled = false;
      btnSubmitReport.innerHTML = origBtnHtml;
    }
  });
});
