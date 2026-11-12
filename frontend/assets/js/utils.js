/**
 * Utilitas Umum Frontend ApiWaspada:
 * - Pemformatan tanggal & waktu WIB
 * - Pembuatan badge status laporan & hasil deteksi AI
 * - Sanitasi HTML (anti-XSS)
 * - Helper pemanggilan API dengan dukungan token autentikasi petugas
 */

function escapeHtml(unsafeText) {
  if (unsafeText === null || unsafeText === undefined) return "";
  return String(unsafeText)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDateTimeWIB(isoString) {
  if (!isoString) return "-";
  try {
    const dt = new Date(isoString.endsWith("Z") ? isoString : isoString + "Z");
    if (isNaN(dt.getTime())) return String(isoString);
    return dt.toLocaleString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Jakarta",
    }) + " WIB";
  } catch (e) {
    return String(isoString);
  }
}

function getStatusBadgeHtml(status) {
  const s = String(status || "pending").toLowerCase();
  const map = {
    pending: { cls: "badge-pending", label: "Menunggu Verifikasi" },
    verified: { cls: "badge-verified", label: "Terverifikasi" },
    rejected: { cls: "badge-rejected", label: "Ditolak" },
    completed: { cls: "badge-completed", label: "Selesai Ditangani" },
  };
  const info = map[s] || { cls: "badge-pending", label: escapeHtml(status) };
  return `<span class="badge ${info.cls}"><span class="badge-dot"></span>${info.label}</span>`;
}

function getDetectionBadgeHtml(detectionResult) {
  const text = String(detectionResult || "");
  const lower = text.toLowerCase();
  let cls = "badge-ai-unavailable";
  if (lower.includes("api dan asap") || lower.includes("indikasi api")) {
    cls = "badge-ai-fire";
  } else if (lower.includes("indikasi asap")) {
    cls = "badge-ai-smoke";
  } else if (lower.includes("tidak ditemukan")) {
    cls = "badge-ai-none";
  }
  return `<span class="badge ${cls}">${escapeHtml(text)}</span>`;
}

function resolveMediaUrl(relativePath) {
  if (!relativePath) return "";
  if (relativePath.startsWith("http://") || relativePath.startsWith("https://")) {
    return relativePath;
  }
  return `${window.APIWASPADA_CONFIG.API_BASE_URL}${relativePath}`;
}

function getOfficerToken() {
  return localStorage.getItem(window.APIWASPADA_CONFIG.TOKEN_STORAGE_KEY) || "";
}

function setOfficerSession(token, officerProfile) {
  localStorage.setItem(window.APIWASPADA_CONFIG.TOKEN_STORAGE_KEY, token);
  if (officerProfile) {
    localStorage.setItem(
      window.APIWASPADA_CONFIG.OFFICER_STORAGE_KEY,
      JSON.stringify(officerProfile)
    );
  }
}

function clearOfficerSession() {
  localStorage.removeItem(window.APIWASPADA_CONFIG.TOKEN_STORAGE_KEY);
  localStorage.removeItem(window.APIWASPADA_CONFIG.OFFICER_STORAGE_KEY);
}

async function apiFetch(endpoint, options = {}) {
  const url = `${window.APIWASPADA_CONFIG.API_BASE_URL}${endpoint}`;
  const headers = Object.assign({}, options.headers || {});
  const token = getOfficerToken();
  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(url, Object.assign({}, options, { headers }));
  let data = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const rawText = await response.text();
    data = { detail: rawText };
  }
  if (!response.ok) {
    const errMsg =
      (data && (data.detail || data.message)) ||
      `Terjadi kesalahan HTTP ${response.status}`;
    const err = new Error(typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg));
    err.status = response.status;
    throw err;
  }
  return data;
}

window.ApiWaspadaUtils = {
  escapeHtml,
  formatDateTimeWIB,
  getStatusBadgeHtml,
  getDetectionBadgeHtml,
  resolveMediaUrl,
  getOfficerToken,
  setOfficerSession,
  clearOfficerSession,
  apiFetch,
};
