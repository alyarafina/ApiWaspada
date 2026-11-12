"""
Layanan Dashboard Petugas dan Pemetaan GIS untuk ApiWaspada.
Menghitung statistik dari database SQLite secara nyata (tanpa angka statistik palsu).
"""
import math
from collections import Counter
from datetime import datetime
from typing import List, Optional

from backend.app.config import settings
from backend.app.database import Session, or_
from backend.app.models.report import Report
from backend.app.schemas.dashboard import (
    DailyReportCount,
    DashboardReportsResponse,
    DashboardStatsResponse,
    MapDataResponse,
    MapMarkerItem,
)
from backend.app.schemas.report import VALID_REPORT_STATUSES
from backend.app.services.ai_service import (
    STATUS_FIRE_AND_SMOKE,
    STATUS_FIRE_ONLY,
    STATUS_MODEL_UNAVAILABLE,
    STATUS_NO_DETECTION,
    STATUS_SMOKE_ONLY,
    ai_service,
)
from backend.app.services.report_service import STATUS_LABELS_ID, to_officer_response


def get_dashboard_statistics(db: Session) -> DashboardStatsResponse:
    """
    Menghitung ringkasan statistik laporan, distribusi status, distribusi hasil deteksi AI,
    dan agregasi jumlah laporan per tanggal langsung dari database SQLite.
    """
    all_reports: List[Report] = (
        db.query(Report).order_by(Report.created_at.asc()).all()
    )

    total = len(all_reports)
    status_counts = Counter(r.status for r in all_reports)
    pending_count = status_counts.get("pending", 0)
    verified_count = status_counts.get("verified", 0)
    rejected_count = status_counts.get("rejected", 0)
    completed_count = status_counts.get("completed", 0)

    status_distribution = {
        "pending": pending_count,
        "verified": verified_count,
        "rejected": rejected_count,
        "completed": completed_count,
    }

    det_counts = Counter(r.detection_result for r in all_reports)
    detection_distribution = {
        STATUS_FIRE_ONLY: det_counts.get(STATUS_FIRE_ONLY, 0),
        STATUS_SMOKE_ONLY: det_counts.get(STATUS_SMOKE_ONLY, 0),
        STATUS_FIRE_AND_SMOKE: det_counts.get(STATUS_FIRE_AND_SMOKE, 0),
        STATUS_NO_DETECTION: det_counts.get(STATUS_NO_DETECTION, 0),
        STATUS_MODEL_UNAVAILABLE: det_counts.get(STATUS_MODEL_UNAVAILABLE, 0),
    }

    date_counter: Counter = Counter()
    for r in all_reports:
        dt_val = r.created_at
        if isinstance(dt_val, datetime):
            date_str = dt_val.strftime("%Y-%m-%d")
        else:
            date_str = str(dt_val)[:10]
        date_counter[date_str] += 1

    reports_by_date = [
        DailyReportCount(date=d_key, count=date_counter[d_key])
        for d_key in sorted(date_counter.keys())
    ]

    ai_status = ai_service.get_status()

    return DashboardStatsResponse(
        total_reports=total,
        pending_count=pending_count,
        verified_count=verified_count,
        rejected_count=rejected_count,
        completed_count=completed_count,
        status_distribution=status_distribution,
        detection_distribution=detection_distribution,
        reports_by_date=reports_by_date,
        ai_active=ai_status.ai_available,
        last_updated=datetime.utcnow(),
    )


def get_dashboard_reports(
    db: Session,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    detection_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> DashboardReportsResponse:
    """
    Mengambil daftar laporan untuk tabel Dashboard Petugas dengan fitur:
    - Search (ID, kode pelacakan, deskripsi, nama pelapor, hasil deteksi)
    - Filter status (pending, verified, rejected, completed)
    - Filter hasil deteksi
    - Filter rentang tanggal (YYYY-MM-DD)
    - Pagination
    """
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    all_rows: List[Report] = (
        db.query(Report).order_by(Report.created_at.desc()).all()
    )

    filtered: List[Report] = []
    search_q = (search or "").strip().lower()
    status_q = (status_filter or "").strip().lower()
    det_q = (detection_filter or "").strip().lower()
    d_from = (date_from or "").strip()
    d_to = (date_to or "").strip()

    for r in all_rows:
        if status_q and status_q in VALID_REPORT_STATUSES and r.status.lower() != status_q:
            continue
        if det_q and det_q != "all" and det_q not in (r.detection_result or "").lower():
            continue

        r_date = (
            r.created_at.strftime("%Y-%m-%d")
            if isinstance(r.created_at, datetime)
            else str(r.created_at)[:10]
        )
        if d_from and r_date < d_from:
            continue
        if d_to and r_date > d_to:
            continue

        if search_q:
            searchable_blob = " ".join(
                [
                    str(r.id),
                    str(r.tracking_code or ""),
                    str(r.description or ""),
                    str(r.reporter_name or ""),
                    str(r.detection_result or ""),
                    f"{r.latitude},{r.longitude}",
                ]
            ).lower()
            if search_q not in searchable_blob:
                continue

        filtered.append(r)

    total = len(filtered)
    total_pages = max(1, math.ceil(total / page_size))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_rows = filtered[start_idx:end_idx]

    items = [to_officer_response(r, db=db) for r in paged_rows]
    return DashboardReportsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


def get_map_markers(
    db: Session,
    status_filter: Optional[str] = None,
) -> MapDataResponse:
    """
    Mengambil data marker koordinat laporan dari database untuk ditampilkan
    pada peta interaktif Leaflet.js.
    """
    query = db.query(Report)
    if status_filter and status_filter.strip().lower() in VALID_REPORT_STATUSES:
        query = query.filter(Report.status == status_filter.strip().lower())

    rows = query.order_by(Report.created_at.desc()).all()
    markers: List[MapMarkerItem] = []

    for r in rows:
        desc_text = r.description or ""
        excerpt = desc_text[:110] + ("..." if len(desc_text) > 110 else "")
        markers.append(
            MapMarkerItem(
                id=r.id,
                tracking_code=r.tracking_code,
                latitude=r.latitude,
                longitude=r.longitude,
                detection_result=r.detection_result,
                detection_confidence=round(float(r.detection_confidence or 0.0), 4),
                status=r.status,
                status_label_id=STATUS_LABELS_ID.get(r.status, r.status),
                description_excerpt=excerpt,
                image_url=r.image_path,
                result_image_url=r.result_image_path,
                created_at=r.created_at,
            )
        )

    return MapDataResponse(
        total_markers=len(markers),
        center_lat=settings.DEFAULT_MAP_LAT,
        center_lng=settings.DEFAULT_MAP_LNG,
        default_zoom=settings.DEFAULT_MAP_ZOOM,
        markers=markers,
    )
