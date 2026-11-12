# Referensi Endpoint REST API — ApiWaspada

Dokumentasi interaktif OpenAPI (Swagger UI) dapat diakses secara langsung saat backend berjalan di:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## Daftar Endpoint Utama

| Kategori | Metode | Endpoint | Autentikasi | Deskripsi |
| :--- | :--- | :--- | :--- | :--- |
| **General** | `GET` | `/` | Publik | Menyajikan `frontend/index.html` atau JSON info (`?format=json`). |
| **General** | `GET` | `/api/health` | Publik | Pemeriksaan status kesehatan server, database SQLite, dan modul AI YOLO. |
| **Auth** | `POST` | `/api/auth/login` | Publik | Login petugas dengan username & password untuk mendapatkan token Bearer JWT. |
| **Auth** | `GET` | `/api/auth/me` | Petugas (Bearer) | Mengambil profil petugas yang sedang aktif login. |
| **Auth** | `POST` | `/api/auth/logout` | Petugas | Menghapus cookie sesi petugas. |
| **AI Detection** | `GET` | `/api/detect/status` | Publik | Memeriksa apakah `ml/weights/best.pt` tersedia beserta konfigurasi device & kelas. |
| **AI Detection** | `POST` | `/api/detect` | Publik | Mengunggah gambar untuk dianalisis oleh YOLO dan menghasilkan citra visualisasi *bounding box*. |
| **Reports** | `POST` | `/api/reports` | Publik | Mengirim laporan baru (foto, deskripsi, latitude, longitude), memproses AI, dan menyimpan ke DB. |
| **Reports** | `GET` | `/api/reports` | Publik | Mengambil daftar laporan publik dengan pagination dan filter status. |
| **Reports** | `GET` | `/api/reports/{report_id}` | Publik | Mengambil detail laporan berdasarkan ID numerik atau Kode Pelacakan (`AW-...`). |
| **Reports** | `PATCH` | `/api/reports/{report_id}/status` | Petugas (Bearer) | Memperbarui status laporan (`pending`, `verified`, `rejected`, `completed`) dan mencatat riwayat. |
| **Reports** | `GET` | `/api/reports/{report_id}/history` | Publik | Mengambil daftar riwayat perubahan status laporan secara kronologis. |
| **Dashboard** | `GET` | `/api/dashboard/stats` | Petugas (Bearer) | Mengambil total laporan per status, distribusi hasil deteksi AI, dan agregasi harian untuk `Chart.js`. |
| **Dashboard** | `GET` | `/api/dashboard/reports` | Petugas (Bearer) | Mengambil daftar laporan lengkap untuk tabel petugas dengan fitur search, filter status, filter tanggal, dan pagination. |
| **Dashboard** | `GET` | `/api/dashboard/reports/{report_id}` | Petugas (Bearer) | Mengambil detail lengkap satu laporan (termasuk nama pelapor dan riwayat verifikasi). |
| **Dashboard / GIS** | `GET` | `/api/dashboard/map` | Publik / Petugas | Mengambil daftar koordinat marker laporan untuk peta interaktif Leaflet.js. |
