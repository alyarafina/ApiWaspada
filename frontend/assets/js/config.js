/**
 * Konfigurasi Global Frontend ApiWaspada Kota Jambi.
 * Secara otomatis menyesuaikan base URL API apabila dibuka melalui FastAPI (:8000)
 * maupun melalui Live Server (:5500).
 */
const APIWASPADA_CONFIG = {
  API_BASE_URL:
    window.location.port === "5500"
      ? "http://127.0.0.1:8000"
      : window.location.origin,
  DEFAULT_LAT: -1.6101,
  DEFAULT_LNG: 103.6131,
  DEFAULT_ZOOM: 12,
  MAX_UPLOAD_SIZE_MB: 10,
  ALLOWED_TYPES: ["image/jpeg", "image/jpg", "image/png"],
  TOKEN_STORAGE_KEY: "apiwaspada_officer_token",
  OFFICER_STORAGE_KEY: "apiwaspada_officer_profile",
  DISCLAIMER_TEXT:
    "Hasil deteksi AI merupakan indikasi awal berdasarkan gambar yang diunggah dan bukan konfirmasi resmi kejadian kebakaran. Setiap laporan tetap memerlukan verifikasi petugas.",
};

window.APIWASPADA_CONFIG = APIWASPADA_CONFIG;
