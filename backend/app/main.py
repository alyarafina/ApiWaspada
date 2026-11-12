"""
Entry point utama aplikasi Backend FastAPI ApiWaspada.
Mengintegrasikan:
- Seluruh router API (`/api/health`, `/api/auth`, `/api/detect`, `/api/reports`, `/api/dashboard`)
- Middleware keamanan CORS terbatas
- Penyajian static files untuk penyimpanan gambar (`storage/uploads`, `storage/results`)
- Penyajian halaman Frontend Masyarakat & Dashboard Petugas (`frontend/`)
"""
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import SessionLocal, init_db
from backend.app.routes import auth, dashboard, detect, health, reports
from backend.app.services.auth_service import ensure_default_officer

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Prototype Sistem Cerdas Deteksi Visual Api dan Asap menggunakan YOLO "
        "serta Pelaporan Berbasis Lokasi untuk Mendukung Penanganan Kebakaran di Kota Jambi. "
        "Catatan: Sistem ini adalah prototype pendukung pelaporan dan verifikasi petugas, "
        "bukan pengganti layanan darurat resmi pemerintah."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Konfigurasi CORS yang dibatasi sesuai daftar ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Officer-Token"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Inisialisasi tabel database SQLite dan akun petugas default saat server mulai berjalan."""
    init_db()
    db = SessionLocal()
    try:
        ensure_default_officer(db)
    finally:
        db.close()


# Registrasi Router API Modular
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(detect.router)
app.include_router(reports.router)
app.include_router(dashboard.router)

# Mount folder penyimpanan gambar (uploads & results)
app.mount(
    "/storage/uploads",
    StaticFiles(directory=str(settings.UPLOAD_DIR)),
    name="uploads",
)
app.mount(
    "/storage/results",
    StaticFiles(directory=str(settings.RESULT_DIR)),
    name="results",
)

# Mount static assets frontend jika direktori tersedia
frontend_assets_dir = settings.FRONTEND_DIR / "assets"
frontend_assets_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/assets",
    StaticFiles(directory=str(frontend_assets_dir)),
    name="assets",
)

ALLOWED_HTML_PAGES = {
    "index.html",
    "beranda.html",
    "report.html",
    "tracking.html",
    "login.html",
    "dashboard.html",
    "report-detail.html",
    "peta.html",
    "panduan.html",
    "dashboard-peta.html",
    "dashboard-laporan.html",
}


@app.get("/", include_in_schema=True, summary="Halaman utama ApiWaspada atau informasi API")
def root_endpoint(request: Request) -> Any:
    """
    Menyajikan halaman utama `frontend/index.html` ketika diakses melalui browser,
    atau mengembalikan JSON metadata API jika diminta dengan `?format=json` / header JSON.
    """
    wants_json = (
        request.query_params.get("format") == "json"
        or "application/json" in (request.headers.get("accept") or "").lower()
        and "text/html" not in (request.headers.get("accept") or "").lower()
    )
    index_file = settings.FRONTEND_DIR / "index.html"
    if not wants_json and index_file.exists():
        return FileResponse(str(index_file), media_type="text/html", headers={"Cache-Control": "no-cache"})

    return JSONResponse(
        content={
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/api/health",
            "pages": {
                "landing": "/index.html",
                "public_home": "/beranda.html",
                "report_form": "/report.html",
                "tracking": "/tracking.html",
                "officer_login": "/login.html",
                "officer_dashboard": "/dashboard.html",
                "officer_report_detail": "/report-detail.html",
            },
            "disclaimer": (
                "Prototype sistem pendukung pelaporan dan verifikasi kebakaran Kota Jambi. "
                "Bukan pengganti layanan darurat resmi pemerintah."
            ),
        }
    )


@app.get("/{page_name}", include_in_schema=False)
def serve_frontend_page(page_name: str) -> Any:
    """Menyajikan file halaman HTML frontend secara aman (tanpa risiko path traversal)."""
    clean_name = Path(page_name).name
    if clean_name in ALLOWED_HTML_PAGES:
        target = (settings.FRONTEND_DIR / clean_name).resolve()
        if target.exists() and settings.FRONTEND_DIR in target.parents:
            return FileResponse(str(target), media_type="text/html", headers={"Cache-Control": "no-cache"})
    return JSONResponse(
        status_code=404,
        content={"detail": f"Halaman '{clean_name}' tidak ditemukan."},
    )
