/**
 * Logika Autentikasi Petugas Dashboard (`login.html` dan proteksi halaman petugas).
 */

async function verifyOfficerSessionOrRedirect() {
  const { apiFetch, getOfficerToken, clearOfficerSession } = window.ApiWaspadaUtils;
  const token = getOfficerToken();
  if (!token) {
    window.location.href = "/login.html?reason=unauthorized";
    return null;
  }
  try {
    const profile = await apiFetch("/api/auth/me");
    return profile;
  } catch (err) {
    clearOfficerSession();
    window.location.href = "/login.html?reason=session_expired";
    return null;
  }
}

async function performOfficerLogout() {
  const { apiFetch, clearOfficerSession } = window.ApiWaspadaUtils;
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } catch (e) {
    // Abaikan jika token sudah expired
  }
  clearOfficerSession();
  window.location.href = "/login.html";
}

window.ApiWaspadaAuth = {
  verifyOfficerSessionOrRedirect,
  performOfficerLogout,
};

document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("officerLoginForm");
  if (!loginForm) return;

  const { apiFetch, setOfficerSession, escapeHtml } = window.ApiWaspadaUtils;
  const usernameInput = document.getElementById("usernameInput");
  const passwordInput = document.getElementById("passwordInput");
  const loginAlert = document.getElementById("loginAlert");
  const btnLoginSubmit = document.getElementById("btnLoginSubmit");

  const params = new URLSearchParams(window.location.search);
  if (params.get("reason") === "unauthorized") {
    loginAlert.className = "alert alert-info";
    loginAlert.textContent = "Silakan login menggunakan akun petugas untuk mengakses Dashboard Verifikasi.";
    loginAlert.classList.remove("hidden");
  } else if (params.get("reason") === "session_expired") {
    loginAlert.className = "alert alert-error";
    loginAlert.textContent = "Sesi petugas telah berakhir. Silakan login kembali.";
    loginAlert.classList.remove("hidden");
  }

  loginForm.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    loginAlert.classList.add("hidden");

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
      loginAlert.className = "alert alert-error";
      loginAlert.textContent = "Username dan password wajib diisi.";
      loginAlert.classList.remove("hidden");
      return;
    }

    const origText = btnLoginSubmit.innerHTML;
    btnLoginSubmit.disabled = true;
    btnLoginSubmit.innerHTML = `<span class="loading-spinner"></span> Memverifikasi Kredensial...`;

    try {
      const res = await apiFetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      setOfficerSession(res.access_token, res.officer);
      window.location.href = "/dashboard.html";
    } catch (err) {
      loginAlert.className = "alert alert-error";
      loginAlert.innerHTML = escapeHtml(err.message || "Gagal login. Periksa kembali username dan password Anda.");
      loginAlert.classList.remove("hidden");
    } finally {
      btnLoginSubmit.disabled = false;
      btnLoginSubmit.innerHTML = origText;
    }
  });
});
