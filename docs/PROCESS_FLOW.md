# Diagram Alur Proses Sistem ApiWaspada Kota Jambi

Dokumen ini menjelaskan alur proses operasional aplikasi **ApiWaspada** mulai dari pelaporan masyarakat, pemrosesan Computer Vision YOLO, penyimpanan database, hingga verifikasi oleh petugas dan pemetaan geospasial.

---

## 1. Alur Utama Pelaporan Masyarakat & Verifikasi Petugas

```mermaid
sequenceDiagram
    autonumber
    actor Warga as Masyarakat (Pelapor)
    participant WebUI as Frontend Masyarakat (report.html)
    participant GeoAPI as Browser Geolocation / Leaflet Map
    participant FastAPI as Backend FastAPI (/api/reports)
    participant YOLO as AI Service (Ultralytics YOLO)
    participant DB as SQLite Database & File Storage
    actor Petugas as Petugas Verifikasi
    participant DashUI as Dashboard Petugas (dashboard.html)

    Warga->>WebUI: Buka halaman pelaporan & unggah/ambil foto
    Warga->>GeoAPI: Klik "Ambil Lokasi GPS" atau pilih titik di Peta Kota Jambi
    GeoAPI-->>WebUI: Kembalikan koordinat (Latitude, Longitude)
    Warga->>WebUI: Isi deskripsi kejadian & klik "Kirim Laporan"
    WebUI->>FastAPI: POST /api/reports (Multipart: image, description, lat, lng)
    FastAPI->>FastAPI: Validasi MIME, ukuran file, integritas Pillow, & koordinat
    FastAPI->>DB: Simpan foto asli ke storage/uploads/
    FastAPI->>YOLO: Jalankan deteksi objek (Fire & Smoke)
    alt Model ml/weights/best.pt Tersedia
        YOLO-->>FastAPI: Bounding box, kelas (Fire/Smoke), confidence, & citra anotasi
    else Model best.pt Belum Tersedia (Mode Fallback)
        YOLO-->>FastAPI: Status "Deteksi gagal atau model belum tersedia" & citra banner info
    end
    FastAPI->>DB: Simpan record ke tabel `reports` (status='pending') & `report_history`
    FastAPI-->>WebUI: Response 201 Created (ID Laporan, Kode Pelacakan AW-..., Hasil AI)
    WebUI-->>Warga: Tampilkan gambar asli vs deteksi AI, confidence, & Kode Pelacakan

    Note over Petugas,DashUI: Proses Pemeriksaan & Verifikasi Petugas
    Petugas->>DashUI: Login di /login.html (POST /api/auth/login)
    DashUI->>FastAPI: GET /api/dashboard/stats, /api/dashboard/reports, /api/dashboard/map
    FastAPI-->>DashUI: Data KPI, grafik Chart.js, tabel laporan, & marker peta
    Petugas->>DashUI: Buka detail laporan (/report-detail.html?id=...)
    Petugas->>DashUI: Periksa foto asli, bounding box AI, koordinat peta, & deskripsi
    Petugas->>FastAPI: PATCH /api/reports/{id}/status (status='verified'/'rejected'/'completed', note)
    FastAPI->>DB: Update `reports.status` & tambah log ke `report_history`
    FastAPI-->>DashUI: Status berhasil diperbarui & tampil pada Peta GIS
```

---

## 2. Alur Keputusan Status Indikasi Deteksi AI YOLO

```mermaid
flowchart TD
    Start(["Gambar Diunggah (JPG / JPEG / PNG)"]) --> Validate["Validasi Ekstensi, MIME Type, Ukuran (<=10MB), & Integritas Pillow"]
    Validate -- "Tidak Valid" --> Reject["HTTP 400 Bad Request\n(Pesan Error Informatif)"]
    Validate -- "Valid" --> CheckModel{"Apakah ml/weights/best.pt\nTersedia & Valid?"}

    CheckModel -- "Belum Tersedia / Gagal Muat" --> Fallback["Status: 'Deteksi gagal atau model belum tersedia'\n(ai_available = false, confidence = 0.0)"]
    CheckModel -- "Tersedia & Siap" --> RunInference["Inferensi Ultralytics YOLO\n(conf >= 0.25, iou = 0.45)"]

    RunInference --> CheckClasses{"Kelas Objek yang Terdeteksi?"}
    CheckClasses -- "Fire DAN Smoke" --> Both["Status: 'Api dan asap terindikasi'"]
    CheckClasses -- "Hanya Fire" --> FireOnly["Status: 'Terdeteksi indikasi api'"]
    CheckClasses -- "Hanya Smoke" --> SmokeOnly["Status: 'Terdeteksi indikasi asap'"]
    CheckClasses -- "Tidak Ada Box" --> NoneFound["Status: 'Tidak ditemukan indikasi api atau asap'"]

    Fallback --> RenderImg["Simpan Visualisasi ke storage/results/\n+ Sertakan Disclaimer Wajib AI"]
    Both --> RenderImg
    FireOnly --> RenderImg
    SmokeOnly --> RenderImg
    NoneFound --> RenderImg
```

---

## 3. Siklus Hidup Status Laporan (`Report Status Lifecycle`)

```text
                       [ Laporan Baru Dikirim Masyarakat ]
                                        |
                                        v
                                 +-------------+
                                 |   PENDING   | (Status awal otomatis)
                                 +------+------+
                                        |
                   +--------------------+--------------------+
                   | (Verifikasi Petugas + Catatan Wajib)    |
                   v                                         v
            +--------------+                         +--------------+
            |   VERIFIED   |                         |   REJECTED   |
            | (Ditindak-   |                         | (Tidak Valid |
            |  lanjuti)    |                         |  / Bukan Api)|
            +------+-------+                         +--------------+
                   |
                   | (Penanganan Selesai + Catatan Wajib)
                   v
            +--------------+
            |  COMPLETED   |
            +--------------+

  * Setiap transisi status wajib menyertakan catatan petugas dan dicatat secara
    permanen di dalam tabel `report_history` tanpa menghapus riwayat sebelumnya.
```
