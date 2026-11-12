@echo off
SETLOCAL EnableDelayedExpansion
TITLE ApiWaspada - Sistem Cerdas Deteksi Visual Api dan Asap Kota Jambi

echo ============================================================================
echo   APIWASPADA - PROTOTYPE DETEKSI API ^& ASAP DAN PELAPORAN KOTA JAMBI
echo ============================================================================
echo.

REM Pastikan berada di direktori root project
cd /d "%~dp0"

REM 1. Periksa ketersediaan virtual environment
REM    Python venv dipanggil langsung lewat path lengkap agar tetap benar
REM    walaupun folder proyek dipindah/diganti nama (activate.bat menyimpan path lama).
set "PY=%~dp0venv\Scripts\python.exe"
if exist "%PY%" (
    echo [INFO] Menggunakan Python dari virtual environment ^(venv^)...
) else (
    echo [WARN] Folder venv belum ditemukan.
    echo [INFO] Membuat virtual environment baru menggunakan Python...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat virtual environment. Pastikan Python 3.10 sudah terinstal dan ada di PATH.
        pause
        exit /b 1
    )
    echo [INFO] Menginstal dependency dari requirements.txt...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements.txt
)

REM Pastikan modul AI YOLO (ultralytics) tersedia di venv
"%PY%" -c "import ultralytics" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Modul ultralytics belum terpasang di venv. Menginstal dependency...
    "%PY%" -m pip install -r requirements.txt
)

REM 2. Siapkan file .env jika belum ada
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Menyalin .env.example menjadi .env...
        copy /Y ".env.example" ".env" >nul
    )
)

REM 3. Pastikan direktori storage tersedia
if not exist "storage\uploads" mkdir "storage\uploads"
if not exist "storage\results" mkdir "storage\results"
if not exist "storage\database" mkdir "storage\database"
if not exist "ml\weights" mkdir "ml\weights"

REM 4. Inisialisasi akun petugas default dan data contoh jika database masih kosong
echo [INFO] Memeriksa inisialisasi database dan akun petugas...
"%PY%" scripts\init_admin.py

REM 5. Periksa status model YOLO
if exist "ml\weights\best.pt" (
    echo [INFO] Model YOLO ditemukan di ml\weights\best.pt ^(Status AI: AKTIF^).
) else (
    echo [WARN] Model ml\weights\best.pt belum tersedia.
    echo [INFO] Aplikasi tetap berjalan dalam Mode AI Belum Aktif ^(Graceful Fallback^).
    echo [INFO] Silakan latih model melalui ml\ApiWaspada_Training_YOLO.ipynb atau ml\train.py.
)

echo.
echo ============================================================================
echo   Menjalankan Server FastAPI + Frontend Terintegrasi...
echo   - Halaman Masyarakat : http://127.0.0.1:8000/
echo   - Form Pelaporan     : http://127.0.0.1:8000/report.html
echo   - Lacak Laporan      : http://127.0.0.1:8000/tracking.html
echo   - Login Petugas      : http://127.0.0.1:8000/login.html
echo   - Dashboard Petugas  : http://127.0.0.1:8000/dashboard.html
echo   - Dokumentasi OpenAPI: http://127.0.0.1:8000/docs
echo ============================================================================
echo.

"%PY%" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
