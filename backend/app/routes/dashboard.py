"""
Router Dashboard Petugas dan Peta GIS (`/api/dashboard`).
Seluruh endpoint administrasi petugas dilindungi oleh autentikasi token (`get_current_officer`).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status

from backend.app.database import Session, get_db
from backend.app.dependencies import get_current_officer
from backend.app.models.user import Officer
from backend.app.schemas.dashboard import (
    DashboardReportsResponse,
    DashboardStatsResponse,
    MapDataResponse,
)
from backend.app.schemas.report import ReportOfficerResponse
from backend.app.services.dashboard_service import (
    get_dashboard_reports,
    get_dashboard_statistics,
    get_map_markers,
)
from backend.app.services.report_service import (
    find_report_by_id_or_code,
    to_officer_response,
)

router = APIRouter(prefix="/api/dashboard", tags=["Officer Dashboard & GIS"])


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil statistik laporan untuk kartu ringkasan dan grafik Chart.js (Petugas)",
)
def dashboard_stats_endpoint(
    current_officer: Officer = Depends(get_current_officer),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    """Mengembalikan statistik laporan nyata dari database SQLite untuk dashboard petugas."""
    return get_dashboard_statistics(db)


@router.get(
    "/reports",
    response_model=DashboardReportsResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil daftar laporan untuk tabel dashboard dengan search, filter, dan pagination (Petugas)",
)
def dashboard_reports_endpoint(
    search: Optional[str] = Query(default=None, description="Kata kunci pencarian"),
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Filter status laporan"
    ),
    detection_filter: Optional[str] = Query(
        default=None, alias="detection", description="Filter hasil deteksi AI"
    ),
    date_from: Optional[str] = Query(
        default=None, description="Filter tanggal mulai (YYYY-MM-DD)"
    ),
    date_to: Optional[str] = Query(
        default=None, description="Filter tanggal akhir (YYYY-MM-DD)"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_officer: Officer = Depends(get_current_officer),
    db: Session = Depends(get_db),
) -> DashboardReportsResponse:
    """Mengambil data laporan lengkap untuk tabel manajemen petugas."""
    return get_dashboard_reports(
        db=db,
        search=search,
        status_filter=status_filter,
        detection_filter=detection_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ReportOfficerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil detail lengkap satu laporan beserta nama pelapor dan riwayat (Petugas)",
)
def dashboard_report_detail_endpoint(
    report_id: str = Path(..., description="ID numerik atau kode pelacakan laporan"),
    current_officer: Officer = Depends(get_current_officer),
    db: Session = Depends(get_db),
) -> ReportOfficerResponse:
    """Mengembalikan detail lengkap laporan untuk halaman pemeriksaan petugas."""
    report = find_report_by_id_or_code(db, report_id)
    return to_officer_response(report, db=db)


@router.get(
    "/map",
    response_model=MapDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil titik koordinat persebaran laporan untuk peta digital Leaflet.js",
)
def dashboard_map_endpoint(
    status_filter: Optional[str] = Query(
        default=None, alias="status", description="Filter status marker peta"
    ),
    db: Session = Depends(get_db),
) -> MapDataResponse:
    """
    Mengembalikan daftar marker laporan berdasarkan koordinat di database
    (tanpa menampilkan informasi pribadi pelapor).
    """
    return get_map_markers(db=db, status_filter=status_filter)
