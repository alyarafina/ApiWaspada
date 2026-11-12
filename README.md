# ApiWaspada — Sistem Cerdas Deteksi Visual Api dan Asap serta Pelaporan Berbasis Lokasi untuk Mendukung Penanganan Kebakaran di Kota Jambi

## 1. Deskripsi ApiWaspada
**ApiWaspada** adalah *prototype* aplikasi berbasis web yang mengintegrasikan deteksi visual api (`Fire`) dan asap (`Smoke`) menggunakan **Ultralytics YOLO**, pelaporan masyarakat berbasis koordinat lokasi (**Browser Geolocation API** & **Leaflet.js OpenStreetMap**), serta **Dashboard Petugas** untuk membantu proses pemeriksaan, verifikasi, dan pemantauan laporan dugaan kebakaran di wilayah **Kota Jambi**.

> **Penting (Batasan Sistem & Disclaimer):**
> - Aplikasi ini ditujukan sebagai **prototype pendukung pelaporan dan verifikasi kebakaran**, bukan sebagai pengganti layanan darurat resmi atau sistem resmi instansi pemerintah.
> - Aplikasi ini **tidak terintegrasi secara otomatis** dengan JCOC 112, Dinas Pemadam Kebakaran dan Penyelamatan (Damkar), maupun instansi pemerintah lainnya.
> - *"Hasil deteksi AI merupakan indikasi awal berdasarkan gambar yang diunggah dan bukan konfirmasi resmi kejadian kebakaran. Setiap laporan tetap memerlukan verifikasi petugas."*

---

## 2. Fitur Aplikasi
1. **Portal Masyarakat (`frontend/index.html`, `report.html`, `tracking.html`)**:
   - Pengunggahan foto dugaan kebakaran (`JPG`, `JPEG`, `PNG`) melalui *drag-and-drop* atau pengambilan foto langsung dari kamera perangkat (*WebRTC*).
   - Pengambilan koordinat GPS otomatis melalui browser atau pemilihan titik lokasi secara interaktif pada peta Kota Jambi.
   - Analisis visual menggunakan model YOLO yang menampilkan gambar asli, gambar hasil visualisasi *bounding box*, nama kelas (`Fire` / `Smoke`), *confidence score*, waktu inferensi, dan status indikasi deteksi.
   - Pelacakan progres verifikasi laporan menggunakan **ID Laporan** atau **Kode Pelacakan Unik** (`AW-YYYYMMDD-XXXXXX`) tanpa menampilkan informasi pribadi pelapor di halaman publik.
2. **Dashboard Petugas Terproteksi (`frontend/login.html`, `dashboard.html`, `report-detail.html`)**:
   - Autentikasi petugas menggunakan *password hashing* `PBKDF2-HMAC-SHA256` dan token sesi bertanda tangan `JWT HS256`.
   - Kartu ringkasan statistik nyata dari database SQLite (Total Laporan, Menunggu Verifikasi, Terverifikasi, Ditolak, dan Selesai).
   - Tiga grafik analitik interaktif menggunakan **Chart.js** (Tren Laporan Berdasarkan Tanggal, Distribusi Status Laporan, dan Distribusi Hasil Deteksi AI).
   - Tabel manajemen laporan dengan fitur pencarian (*search*), filter status, filter rentang tanggal, dan *pagination*.
   - Halaman detail verifikasi laporan untuk memeriksa bukti foto, *bounding box*, titik koordinat peta, memperbarui status laporan (`pending`, `verified`, `rejected`, `completed`), dan menambahkan catatan verifikasi yang tercatat otomatis di tabel riwayat (`report_history`).
3. **Sistem Computer Vision YOLO & Pipeline Machine Learning (`ml/`)**:
   - Dirancang untuk **D-Fire Dataset** ([GitHub - gaia-solutions-on-demand/DFireDataset](https://github.com/gaia-solutions-on-demand/DFireDataset) & [Dokumentasi Resmi D-Fire](https://gaia-solutions-on-demand.github.io/DFireDataset/)).
   - Menyediakan Jupyter Notebook 22 bagian (`ml/ApiWaspada_Training_YOLO.ipynb`) dan skrip modular (`check_dataset.py`, `train.py`, `evaluate.py`, `predict.py`, `data.yaml`).
   - Mendukung **Mode Graceful Fallback**: apabila file model `ml/weights/best.pt` belum tersedia, aplikasi tetap dapat dijalankan sepenuhnya dan menampilkan status `"Deteksi gagal atau model belum tersedia"` secara jelas tanpa menggunakan file model palsu.

---

## 3. Arsitektur Aplikasi
Aplikasi menerapkan arsitektur modular 8 komponen:
1. **Frontend Masyarakat** (`frontend/index.html`, `report.html`, `tracking.html`)
2. **Frontend Dashboard Petugas** (`frontend/login.html`, `dashboard.html`, `report-detail.html`)
3. **Backend API** (`backend/app/main.py`, `routes/`, `services/`, `schemas/`, `core/`)
4. **Database SQLite** (`backend/app/database.py`, `models/`, `storage/database/apiwaspada.db`)
5. **AI Inference Service** (`backend/app/services/ai_service.py`)
6. **Machine Learning Training Pipeline** (`ml/`)
7. **GIS dan Pemetaan** (`frontend/assets/js/map.js`, `backend/app/utils/geo_validator.py`)
8. **File Storage** (`storage/uploads/`, `storage/results/`)

Lihat diagram arsitektur dan alur proses selengkapnya pada [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) dan [`docs/PROCESS_FLOW.md`](docs/PROCESS_FLOW.md).

---

## 4. Struktur Folder Project

```text
ApiWaspada/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # Entry point FastAPI & static file serving
│   │   ├── config.py                # Konfigurasi environment & konstanta sistem
│   │   ├── database.py              # Koneksi SQLite & SQLAlchemy Session
│   │   ├── dependencies.py          # Dependency injection & otorisasi token petugas
│   │   ├── models/                  # Model tabel SQLite (Report, ReportHistory, Officer)
│   │   ├── schemas/                 # Schema validasi Pydantic (report, detection, dashboard, auth)
│   │   ├── routes/                  # Endpoint API modular (health, auth, detect, reports, dashboard)
│   │   ├── services/                # Business logic (ai_service, report_service, dashboard_service, auth_service)
│   │   ├── core/                    # Keamanan (PBKDF2, JWT HS256, XSS Sanitizer) & custom exceptions
│   │   └── utils/                   # Validasi file gambar (Pillow), validasi koordinat GIS, ORM adapter
│   └── requirements.txt             # Daftar dependency khusus backend
│
├── frontend/
│   ├── index.html                   # Landing page masyarakat
│   ├── report.html                  # Halaman form pelaporan & deteksi visual AI
│   ├── tracking.html                # Halaman pelacakan status laporan & peta publik
│   ├── login.html                   # Halaman login petugas verifikasi
│   ├── dashboard.html               # Dashboard utama petugas (KPI, Chart.js, Peta, Tabel)
│   ├── report-detail.html           # Halaman pemeriksaan detail & verifikasi laporan petugas
│   └── assets/
│       ├── css/style.css            # Stylesheet modern & responsif ApiWaspada
│       ├── js/                      # Modul JS (config, utils, map, report, tracking, auth, dashboard, report-detail)
│       └── images/                  # Logo & favicon SVG ApiWaspada
│
├── ml/
│   ├── ApiWaspada_Training_YOLO.ipynb # Notebook pelatihan & evaluasi YOLO (22 bagian lengkap)
│   ├── train.py                     # Script CLI pelatihan model YOLO
│   ├── evaluate.py                  # Script CLI evaluasi model (val/test, PR curve, confusion matrix, loss)
│   ├── predict.py                   # Script CLI prediksi satu atau banyak gambar
│   ├── check_dataset.py             # Script pemeriksa struktur & anotasi D-Fire Dataset
│   ├── data.yaml                    # Konfigurasi path & kelas dataset YOLO
│   ├── configs/                     # Profil hyperparameter (train_lightweight.yaml & train_experiment.yaml)
│   └── weights/                     # Lokasi penyimpanan model terbaik (best.pt)
│
├── storage/
│   ├── uploads/                     # Penyimpanan foto asli yang diunggah
│   ├── results/                     # Penyimpanan gambar hasil visualisasi bounding box YOLO
│   └── database/                    # Lokasi file database SQLite (apiwaspada.db)
│
├── tests/                           # Suite pengujian otomatis (Backend, Frontend, AI, Integrasi)
├── scripts/                         # Script utilitas (init_admin.py, seed_demo_data.py, verify_setup.py)
├── docs/                            # Dokumentasi arsitektur, alur proses, & referensi API
├── .env.example                     # Template konfigurasi environment variable
├── .gitignore                       # Aturan pengecualian Git
├── requirements.txt                 # Daftar dependency lengkap Python 3.10
├── README.md                        # Dokumentasi utama proyek
└── run.bat                          # Peluncur cepat satu klik untuk Windows 10/11
```

---

## 5. Persyaratan Sistem
- **Sistem Operasi**: Windows 10 atau Windows 11 (64-bit) — juga kompatibel dengan Linux/macOS.
- **Python**: Python **3.10.x** (disarankan 3.10.11).
- **Code Editor**: Visual Studio Code dengan ekstensi *Python* dan *Jupyter*.
- **RAM**: Minimal 8 GB (disarankan 16 GB untuk pelatihan model YOLO).
- **Penyimpanan**: Minimal 5 GB ruang kosong untuk aplikasi dan *virtual environment* (+ ~3–5 GB tambahan jika mengunduh D-Fire Dataset penuh).
- **GPU (Opsional)**: NVIDIA GPU yang mendukung CUDA 11.8 / 12.1 untuk mempercepat pelatihan model YOLO. Jika tidak tersedia, sistem berjalan menggunakan CPU.

---

## 6. Instalasi Python 3.10 di Windows
1. Unduh installer resmi **Python 3.10 (64-bit)** dari [python.org/downloads/release/python-31011/](https://www.python.org/downloads/release/python-31011/).
2. Jalankan installer dan **wajib mencentang opsi `"Add python.exe to PATH"`** pada layar pertama sebelum menekan *Install Now*.
3. Buka **PowerShell** atau **Command Prompt (CMD)** di VS Code, lalu verifikasi instalasi:
   ```powershell
   python --version
   ```

---

## 7. Pembuatan Virtual Environment (`venv`)
Buka terminal pada direktori root folder `ApiWaspada/`, kemudian jalankan:

```powershell
# Buat virtual environment bernama venv
python -m venv venv

# Aktifkan virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Atau jika menggunakan Command Prompt (CMD):
venv\Scripts\activate.bat
```
> **Tips PowerShell**: Jika muncul pesan *execution policy*, jalankan perintah berikut terlebih dahulu di PowerShell:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## 8. Instalasi Dependency (CPU maupun GPU NVIDIA)
Setelah `(venv)` aktif, perbarui `pip` terlebih dahulu:

```powershell
python -m pip install --upgrade pip
```

### Opsi A: Perangkat dengan GPU NVIDIA (CUDA)
Jika komputer Anda memiliki GPU NVIDIA dan ingin melatih model dengan akselerasi CUDA, instal PyTorch versi CUDA terlebih dahulu sebelum menginstal `requirements.txt`:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### Opsi B: Perangkat Tanpa GPU NVIDIA (CPU Only)
Jika menggunakan CPU standar, langsung jalankan:

```powershell
pip install -r requirements.txt
```

---

## 9. Persiapan Dataset D-Fire
Sistem deteksi visual ApiWaspada dirancang menggunakan **D-Fire Dataset**:
- **Repositori Resmi**: [https://github.com/gaia-solutions-on-demand/DFireDataset](https://github.com/gaia-solutions-on-demand/DFireDataset)
- **Dokumentasi Resmi**: [https://gaia-solutions-on-demand.github.io/DFireDataset/](https://gaia-solutions-on-demand.github.io/DFireDataset/)

### Karakteristik & Komposisi Resmi D-Fire Dataset
Berdasarkan dokumentasi resmi GAIA (*Venâncio et al., Neural Computing and Applications, 2022*), D-Fire Dataset memiliki lebih dari **21.000 gambar** (21.527 citra) dengan rincian:
- **Only fire**: 1.164 gambar
- **Only smoke**: 5.867 gambar
- **Fire and smoke**: 4.658 gambar
- **None (Citra negatif tanpa api/asap, file label `.txt` kosong)**: 9.838 gambar
- **Jumlah Bounding Box**: 14.692 *bounding box* `Fire` dan 11.865 *bounding box* `Smoke` dalam format YOLO ternormalisasi `[0, 1]` dengan konvensi kelas `0: smoke` dan `1: fire`.

### Langkah Penempatan & Pemeriksaan Dataset
1. Unduh arsip D-Fire Dataset melalui tautan yang tertera pada [GitHub DFireDataset](https://github.com/gaia-solutions-on-demand/DFireDataset).
2. Ekstrak dataset ke dalam folder `ml/dataset/DFireDataset/` sehingga strukturnya menjadi:
   ```text
   ApiWaspada/ml/dataset/DFireDataset/
   ├── train/
   │   ├── images/
   │   └── labels/
   ├── val/          (Dapat dibuat otomatis dari train/ jika unduhan hanya berisi train/ & test/)
   │   ├── images/
   │   └── labels/
   └── test/
       ├── images/
       └── labels/
   ```
3. Jalankan script pemeriksa dataset untuk memvalidasi struktur folder, memeriksa format anotasi YOLO, membuat split `val/` otomatis (10% dari `train/`) apabila belum ada, dan memperbarui `ml/data.yaml`:
   ```powershell
   python ml/check_dataset.py --dataset-dir ml/dataset/DFireDataset --update-yaml ml/data.yaml --create-val-split
   ```

---

## 10. Training Model YOLO
Anda dapat melatih model YOLO melalui **Jupyter Notebook** maupun melalui **Script CLI**:

### Cara 1: Menggunakan Jupyter Notebook (Interaktif di VS Code)
1. Buka file `ml/ApiWaspada_Training_YOLO.ipynb` di Visual Studio Code.
2. Pilih kernel Python dari `venv` Anda.
3. Jalankan sel secara berurutan dari Bagian 1 hingga Bagian 22.

### Cara 2: Menggunakan Script `ml/train.py`
```powershell
# Konfigurasi Ringan (untuk pengujian cepat / CPU, yolov8n.pt, imgsz=416, 10 epoch):
python ml/train.py --config ml/configs/train_lightweight.yaml

# Konfigurasi Eksperimen Penuh (untuk GPU NVIDIA, yolov8s.pt, imgsz=640, 50 epoch):
python ml/train.py --config ml/configs/train_experiment.yaml

# Atau kustomisasi parameter langsung melalui CLI:
python ml/train.py --model yolov8n.pt --epochs 25 --batch 16 --imgsz 640 --device auto
```

---

## 11. Evaluasi Model
Setelah model selesai dilatih, jalankan evaluasi untuk menghasilkan metrik nyata (**Precision**, **Recall**, **mAP@0.5**, **mAP@0.5:0.95**, **Confusion Matrix**, **Precision-Recall Curve**, serta grafik **Training & Validation Loss**):

```powershell
# Evaluasi pada Validation Set + Plot Kurva Loss
python ml/evaluate.py --weights ml/weights/best.pt --data ml/data.yaml --split val --results-csv ml/runs/detect/apiwaspada_dfire_light/results.csv

# Evaluasi Final pada Test Set
python ml/evaluate.py --weights ml/weights/best.pt --data ml/data.yaml --split test
```

Untuk menjalankan prediksi mandiri pada satu gambar atau satu folder gambar:
```powershell
python ml/predict.py --source storage/uploads --weights ml/weights/best.pt --conf 0.25
```

---

## 12. Penempatan `best.pt`
- Script `ml/train.py` dan notebook `ApiWaspada_Training_YOLO.ipynb` secara otomatis menyalin model terbaik hasil pelatihan ke:
  ```text
  ml/weights/best.pt
  ```
- Jika Anda melatih model di komputer lain atau Google Colab, cukup salin file `best.pt` hasil pelatihan ke `ApiWaspada/ml/weights/best.pt`.
- Begitu file `ml/weights/best.pt` tersedia, endpoint `/api/detect/status` otomatis berubah menjadi **AI Aktif** tanpa perlu me-restart atau mengubah kode program.

---

## 13. Konfigurasi Environment (`.env`)
Salin file `.env.example` menjadi `.env` pada root folder `ApiWaspada/`:

```powershell
copy .env.example .env
```

Anda dapat menyesuaikan nilai konfigurasi di dalam `.env`, seperti:
- `SECRET_KEY`: Kunci rahasia penandatanganan token JWT petugas.
- `DEFAULT_ADMIN_USERNAME` & `DEFAULT_ADMIN_PASSWORD`: Kredensial awal petugas verifikasi.
- `MAX_UPLOAD_SIZE_MB`: Batas ukuran unggahan foto (default `10` MB).
- `YOLO_CONFIDENCE_THRESHOLD`: Ambang batas *confidence* deteksi (default `0.25`).

---

## 14. Menjalankan Backend FastAPI
Sebelum menjalankan server untuk pertama kali, inisialisasi database SQLite dan akun petugas default:

```powershell
python scripts/init_admin.py

# (Opsional) Tambahkan 4 sampel laporan simulasi pengembangan Kota Jambi agar peta & grafik langsung terisi:
python scripts/seed_demo_data.py
```

Jalankan server backend FastAPI menggunakan Uvicorn:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Atau cukup klik ganda / jalankan **`run.bat`** pada Windows:
```powershell
.\run.bat
```

---

## 15. Menjalankan Frontend Masyarakat
Frontend masyarakat disajikan secara terintegrasi oleh server FastAPI (sehingga bebas masalah path dan CORS). Buka browser dan akses:
- **Landing Page Masyarakat**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Form Pelaporan & Deteksi AI**: [http://127.0.0.1:8000/report.html](http://127.0.0.1:8000/report.html)
- **Pelacakan Status & Peta Publik**: [http://127.0.0.1:8000/tracking.html](http://127.0.0.1:8000/tracking.html)

---

## 16. Menjalankan Dashboard Petugas
1. Buka halaman login petugas di: [http://127.0.0.1:8000/login.html](http://127.0.0.1:8000/login.html)
2. Masuk menggunakan kredensial petugas yang dikonfigurasi pada `.env` (default pengembangan: Username **`petugas_jambi`**, Password **`ApiWaspadaJambi2026!`**).
3. Setelah berhasil login, Anda akan diarahkan ke:
   - **Dashboard Pemantauan Petugas**: [http://127.0.0.1:8000/dashboard.html](http://127.0.0.1:8000/dashboard.html)
   - Klik tombol **"Periksa & Verifikasi"** pada baris laporan mana pun untuk membuka halaman detail pemeriksaan (`report-detail.html`), memperbarui status laporan, dan menambahkan catatan verifikasi.

---

## 17. Menjalankan Pengujian Otomatis (QA)
Proyek ini dilengkapi dengan suite pengujian otomatis di folder `tests/` yang menguji Backend, Frontend, AI Service (baik mode aktif maupun mode fallback), validasi gambar, autentikasi, serta pipeline ML.

Jalankan pengujian melalui `pytest` atau `unittest` bawaan Python:

```powershell
# Menggunakan unittest standar Python:
python -m unittest discover -s tests -v

# Atau menggunakan pytest:
pytest -v

# Memverifikasi kelengkapan struktur proyek:
python scripts/verify_setup.py
```

---

## 18. Troubleshooting (Pemecahan Masalah)
1. **Pesan `"Mode AI Belum Aktif (Menunggu Model best.pt)"` pada aplikasi**:
   - Hal ini normal apabila Anda belum melatih atau menempatkan file `ml/weights/best.pt`. Aplikasi tetap dapat menerima laporan masyarakat, menyimpan ke database, dan menampilkan laporan di dashboard petugas. Setelah Anda menjalankan `ml/train.py` atau menempatkan `best.pt` di `ml/weights/best.pt`, deteksi objek YOLO akan langsung aktif.
2. **Tombol `"Ambil Lokasi GPS Saat Ini"` ditolak oleh browser**:
   - Pastikan Anda memberikan izin akses lokasi (*Allow Location*) pada browser dan mengakses melalui `http://127.0.0.1:8000` atau `http://localhost:8000`. Jika perangkat PC Anda tidak memiliki modul GPS, cukup klik langsung titik lokasi pada peta interaktif Kota Jambi atau geser pin merah pada peta.
3. **Error `ImportError: DLL load failed` saat mengimpor OpenCV atau PyTorch di Windows**:
   - Instal *Microsoft Visual C++ Redistributable (x64)* terbaru dari situs resmi Microsoft, atau pastikan Anda menggunakan Python 3.10 64-bit.
4. **Kehabisan memori (`CUDA out of memory`) saat training YOLO**:
   - Gunakan konfigurasi ringan (`python ml/train.py --config ml/configs/train_lightweight.yaml`) atau kecilkan nilai `--batch 4 --imgsz 416`.
