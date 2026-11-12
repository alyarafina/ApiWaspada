"""
Layanan Pengelolaan Laporan Kebakaran (`reports`) dan Riwayat Status (`report_history`).
"""
import json
import math
import secrets
from datetime import datetime
from typing import List, Optional, Union

from fastapi import HTTPException, UploadFile, status

from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.core.security import sanitize_text
from backend.app.database import Session, or_
from backend.app.models.report import Report
from backend.app.models.report_history import ReportHistory
from backend.app.schemas.detection import AI_DISCLAIMER_TEXT, BoundingBoxItem
from backend.app.schemas.report import (
    VALID_REPORT_STATUSES,
    ReportHistoryItem,
    ReportListResponse,
    ReportOfficerResponse,
    ReportPublicResponse,
    ReportStatusUpdateRequest,
)
from backend.app.services.ai_service import ai_service
from backend.app.utils.file_handler import save_uploaded_image, validate_and_read_image
from backend.app.utils.geo_validator import check_jambi_bounds, validate_coordinates

STATUS_LABELS_ID = {
    "pending": "Menunggu Verifikasi Petugas",
    "verified": "Terverifikasi (Ditindaklanjuti)",
    "rejected": "Ditolak / Tidak Valid",
    "completed": "Penanganan Selesai",
}


def generate_tracking_code() -> str:
    """Membuat kode pelacakan unik berformat `AW-YYYYMMDD-XXXXXX`."""
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand_part = secrets.token_hex(3).upper()
    return f"AW-{date_part}-{rand_part}"


def _parse_detections_json(raw_json: Optional[str]) -> List[BoundingBoxItem]:
    if not raw_json:
        return []
    try:
        items = json.loads(raw_json)
        if not isinstance(items, list):
            return []
        return [BoundingBoxItem(**item) for item in items]
    except Exception:
        return []


def to_public_response(report: Report) -> ReportPublicResponse:
    """Mengonversi model `Report` menjadi `ReportPublicResponse` (tanpa data pribadi pelapor)."""
    return ReportPublicResponse(
        id=report.id,
        tracking_code=report.tracking_code,
        description=report.description,
        latitude=report.latitude,
        longitude=report.longitude,
        image_url=report.image_path,
        result_image_url=report.result_image_path,
        detection_result=report.detection_result,
        detection_confidence=round(float(report.detection_confidence or 0.0), 4),
        detections=_parse_detections_json(report.detections_json),
        inference_time_ms=round(float(report.inference_time_ms or 0.0), 2),
        status=report.status,
        status_label_id=STATUS_LABELS_ID.get(report.status, report.status),
        created_at=report.created_at,
        updated_at=report.updated_at,
        region_info=check_jambi_bounds(report.latitude, report.longitude),
        disclaimer=AI_DISCLAIMER_TEXT,
    )


def to_officer_response(report: Report, db: Optional[Session] = None) -> ReportOfficerResponse:
    """Mengonversi model `Report` menjadi `ReportOfficerResponse` lengkap beserta riwayat status."""
    pub = to_public_response(report)
    raw_histories = getattr(report, "histories", None)
    if raw_histories is None and db is not None:
        raw_histories = (
            db.query(ReportHistory)
            .filter(ReportHistory.report_id == report.id)
            .order_by(ReportHistory.changed_at.desc())
            .all()
        )
    history_items = [
        ReportHistoryItem(
            id=h.id,
            report_id=h.report_id,
            previous_status=h.previous_status,
            new_status=h.new_status,
            note=h.note,
            changed_by=h.changed_by or "system",
            changed_at=h.changed_at,
        )
        for h in (raw_histories or [])
    ]
    return ReportOfficerResponse(
        **pub.dict(),
        reporter_name=report.reporter_name or "Masyarakat",
        ai_model_used=report.ai_model_used or "none",
        histories=history_items,
    )


def create_new_report(
    db: Session,
    image: UploadFile,
    description: str,
    latitude: float,
    longitude: float,
    reporter_name: Optional[str] = None,
) -> ReportPublicResponse:
    """
    Memvalidasi input, menyimpan foto, menjalankan deteksi YOLO, menyimpan laporan
    dan riwayat status awal ke database SQLite.
    """
    clean_desc = sanitize_text(description, max_length=1000)
    if len(clean_desc) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deskripsi kejadian wajib diisi minimal 5 karakter.",
        )

    clean_reporter = sanitize_text(reporter_name or "Masyarakat", max_length=120)
    if not clean_reporter:
        clean_reporter = "Masyarakat"

    lat, lng = validate_coordinates(latitude, longitude)

    # Validasi dan simpan file gambar asli
    file_bytes, ext, _ = validate_and_read_image(image)
    saved_path, relative_image_url = save_uploaded_image(file_bytes, ext, prefix="rep")

    # Jalankan deteksi AI YOLO
    detection_res = ai_service.run_detection(
        image_path=saved_path,
        original_image_url=relative_image_url,
    )

    detections_serialized = json.dumps([d.dict() for d in detection_res.detections])
    now = datetime.utcnow()
    tracking_code = generate_tracking_code()

    report = Report(
        tracking_code=tracking_code,
        reporter_name=clean_reporter,
        description=clean_desc,
        latitude=lat,
        longitude=lng,
        image_path=relative_image_url,
        result_image_path=detection_res.result_image_url,
        detection_result=detection_res.detection_status,
        detection_confidence=detection_res.highest_confidence,
        detections_json=detections_serialized,
        inference_time_ms=detection_res.inference_time_ms,
        ai_model_used=detection_res.model_info,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Buat catatan riwayat awal
    initial_history = ReportHistory(
        report_id=report.id,
        previous_status=None,
        new_status="pending",
        note=f"Laporan dibuat oleh masyarakat. Status indikasi AI: {detection_res.detection_status}.",
        changed_by="system",
        changed_at=now,
    )
    db.add(initial_history)
    db.commit()

    return to_public_response(report)


def find_report_by_id_or_code(db: Session, identifier: Union[int, str]) -> Report:
    """Mencari laporan berdasarkan ID numerik atau kode pelacakan (`AW-YYYYMMDD-XXXXXX`)."""
    ident_str = str(identifier).strip()
    report: Optional[Report] = None
    if ident_str.isdigit():
        report = db.query(Report).filter(Report.id == int(ident_str)).first()
    if report is None:
        report = (
            db.query(Report)
            .filter(Report.tracking_code == ident_str.upper())
            .first()
        )
    if report is None:
        raise ResourceNotFoundError(
            f"Laporan dengan ID atau kode '{ident_str}' tidak ditemukan."
        )
    return report


def list_public_reports(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> ReportListResponse:
    """Mengambil daftar laporan untuk publik dengan filter status dan pagination."""
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    query = db.query(Report)
    if status_filter and status_filter.strip().lower() in VALID_REPORT_STATUSES:
        query = query.filter(Report.status == status_filter.strip().lower())

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size

    rows = (
        query.order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    items = [to_public_response(r) for r in rows]
    return ReportListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


def update_report_status(
    db: Session,
    identifier: Union[int, str],
    payload: ReportStatusUpdateRequest,
    officer_username: str = "petugas",
) -> ReportOfficerResponse:
    """
    Memperbarui status laporan oleh petugas dan mencatat perubahan pada tabel `report_history`.
    """
    new_status = payload.status.strip().lower()
    if new_status not in VALID_REPORT_STATUSES:
        valid_str = ", ".join(VALID_REPORT_STATUSES)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status '{payload.status}' tidak valid. Pilih salah satu dari: {valid_str}.",
        )

    clean_note = sanitize_text(payload.note, max_length=1000)
    if len(clean_note) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Catatan verifikasi wajib diisi minimal 3 karakter.",
        )

    report = find_report_by_id_or_code(db, identifier)
    prev_status = report.status
    now = datetime.utcnow()

    report.status = new_status
    report.updated_at = now
    db.add(report)

    history = ReportHistory(
        report_id=report.id,
        previous_status=prev_status,
        new_status=new_status,
        note=clean_note,
        changed_by=officer_username,
        changed_at=now,
    )
    db.add(history)
    db.commit()
    db.refresh(report)

    return to_officer_response(report, db=db)


def get_report_histories(
    db: Session, identifier: Union[int, str]
) -> List[ReportHistoryItem]:
    """Mengambil daftar riwayat perubahan status untuk satu laporan."""
    report = find_report_by_id_or_code(db, identifier)
    rows = (
        db.query(ReportHistory)
        .filter(ReportHistory.report_id == report.id)
        .order_by(ReportHistory.changed_at.desc())
        .all()
    )
    return [
        ReportHistoryItem(
            id=h.id,
            report_id=h.report_id,
            previous_status=h.previous_status,
            new_status=h.new_status,
            note=h.note,
            changed_by=h.changed_by or "system",
            changed_at=h.changed_at,
        )
        for h in rows
    ]
