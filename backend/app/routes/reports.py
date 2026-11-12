"""
Router Pengelolaan Laporan Kebakaran (`/api/reports`).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile, status

from backend.app.database import Session, get_db
from backend.app.dependencies import get_current_officer
from backend.app.models.user import Officer
from backend.app.schemas.report import (
    ReportHistoryItem,
    ReportListResponse,
    ReportOfficerResponse,
    ReportPublicResponse,
    ReportStatusUpdateRequest,
)
from backend.app.services.report_service import (
    create_new_report,
    find_report_by_id_or_code,
    get_report_histories,
    list_public_reports,
    to_public_response,
    update_report_status,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat laporan dugaan kebakaran baru beserta deteksi visual AI YOLO",
)
def create_report_endpoint(
    image: UploadFile = File(..., description="Foto dugaan kebakaran (JPG/JPEG/PNG)"),
    description: str = Form(
        ...,
        min_length=5,
        max_length=1000,
        description="Deskripsi kondisi kejadian dan patokan lokasi",
    ),
    latitude: float = Form(..., description="Koordinat Latitude lokasi kejadian"),
    longitude: float = Form(..., description="Koordinat Longitude lokasi kejadian"),
    reporter_name: Optional[str] = Form(
        default="Masyarakat",
        max_length=120,
        description="Nama pelapor (opsional, hanya ditampilkan untuk petugas)",
    ),
    db: Session = Depends(get_db),
) -> ReportPublicResponse:
    """
    Menerima laporan masyarakat, memvalidasi foto dan koordinat GPS,
    menjalankan deteksi YOLO, dan menyimpan laporan ke database SQLite.
    """
    return create_new_report(
        db=db,
        image=image,
        description=description,
        latitude=latitude,
        longitude=longitude,
        reporter_name=reporter_name,
    )


@router.get(
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil daftar laporan kebakaran (publik, dengan filter status & pagination)",
)
def get_reports_endpoint(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter berdasarkan status: pending, verified, rejected, completed",
    ),
    page: int = Query(default=1, ge=1, description="Nomor halaman"),
    page_size: int = Query(default=20, ge=1, le=100, description="Jumlah item per halaman"),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """Mengembalikan daftar laporan masyarakat tanpa menampilkan data pribadi pelapor."""
    return list_public_reports(
        db=db,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{report_id}",
    response_model=ReportPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Ambil detail laporan berdasarkan ID laporan atau kode pelacakan (AW-...)",
)
def get_single_report_endpoint(
    report_id: str = Path(..., description="ID numerik laporan atau kode pelacakan AW-..."),
    db: Session = Depends(get_db),
) -> ReportPublicResponse:
    """Mengambil informasi detail dan status laporan untuk pelacakan masyarakat."""
    report = find_report_by_id_or_code(db, report_id)
    return to_public_response(report)


@router.patch(
    "/{report_id}/status",
    response_model=ReportOfficerResponse,
    status_code=status.HTTP_200_OK,
    summary="Perbarui status verifikasi laporan (Khusus Petugas Terautentikasi)",
)
def patch_report_status_endpoint(
    payload: ReportStatusUpdateRequest,
    report_id: str = Path(..., description="ID numerik laporan atau kode pelacakan"),
    current_officer: Officer = Depends(get_current_officer),
    db: Session = Depends(get_db),
) -> ReportOfficerResponse:
    """
    Memperbarui status laporan (`pending`, `verified`, `rejected`, `completed`)
    dan menyimpan catatan verifikasi ke dalam tabel `report_history`.
    Endpoint ini wajib menggunakan token autentikasi petugas.
    """
    return update_report_status(
        db=db,
        identifier=report_id,
        payload=payload,
        officer_username=current_officer.username,
    )


@router.get(
    "/{report_id}/history",
    response_model=List[ReportHistoryItem],
    status_code=status.HTTP_200_OK,
    summary="Ambil riwayat perubahan status laporan",
)
def get_report_history_endpoint(
    report_id: str = Path(..., description="ID numerik laporan atau kode pelacakan"),
    db: Session = Depends(get_db),
) -> List[ReportHistoryItem]:
    """Mengembalikan daftar kronologis riwayat perubahan status laporan."""
    return get_report_histories(db=db, identifier=report_id)
