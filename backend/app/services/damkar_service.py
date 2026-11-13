"""
Layanan Petugas Damkar:
- Operator menugaskan laporan terverifikasi ke petugas Damkar tertentu atau ke semua petugas.
- Petugas Damkar melihat laporan yang ditugaskan kepadanya dan mencatat progres TKP (UC-09).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from backend.app.core.security import sanitize_text
from backend.app.database import Session
from backend.app.models.assignment import ReportAssignment
from backend.app.models.progress import PROGRESS_STAGES, ReportProgress
from backend.app.models.report import Report
from backend.app.models.report_history import ReportHistory
from backend.app.models.user import Officer
from backend.app.services.report_service import find_report_by_id_or_code, to_officer_response
from backend.app.utils.file_handler import save_uploaded_image, validate_and_read_image

ACTIVE_STATUSES = ("verified", "handling")


def _bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


def _active_damkar(db: Session):
    return (
        db.query(Officer)
        .filter(Officer.role == "damkar", Officer.is_active == True)  # noqa: E712
        .order_by(Officer.full_name.asc())
        .all()
    )


def list_damkar_officers(db: Session) -> List[dict]:
    return [{"id": o.id, "username": o.username, "full_name": o.full_name} for o in _active_damkar(db)]


# ---------------------------------------------------------------------------
# Operator: tugaskan petugas
# ---------------------------------------------------------------------------
def assign_officers(db: Session, identifier, officer_ids: Optional[List[int]], assign_all: bool,
                    operator: Officer, note: str = ""):
    report = find_report_by_id_or_code(db, identifier)
    if report.status not in ACTIVE_STATUSES:
        raise _bad_request("Verifikasi laporan terlebih dahulu sebelum menugaskan Tim Damkar.")
    candidates = {o.id: o for o in _active_damkar(db)}
    if not candidates:
        raise _bad_request("Belum ada akun Petugas Damkar yang aktif. Admin perlu membuatnya.")
    if assign_all:
        chosen = list(candidates.values())
    else:
        ids = {int(i) for i in (officer_ids or [])}
        unknown = ids - set(candidates)
        if unknown:
            raise _bad_request("Ada petugas yang tidak ditemukan atau tidak aktif.")
        chosen = [candidates[i] for i in ids]
    if not chosen:
        raise _bad_request("Pilih minimal satu petugas Damkar.")

    # Penugasan baru menggantikan susunan sebelumnya; progres yang sudah tercatat tetap ada
    db.query(ReportAssignment).filter(ReportAssignment.report_id == report.id).delete(synchronize_session=False)
    now = datetime.utcnow()
    for o in chosen:
        db.add(ReportAssignment(report_id=report.id, officer_id=o.id, assigned_by=operator.username, assigned_at=now))
    names = "semua petugas Damkar" if assign_all else ", ".join(o.full_name for o in chosen)
    clean_note = sanitize_text(note or "", max_length=500)
    db.add(ReportHistory(
        report_id=report.id, previous_status=report.status, new_status=report.status,
        note=f"Ditugaskan ke {names}. {clean_note}".strip(),
        changed_by=operator.username, changed_at=now,
    ))
    report.updated_at = now
    db.commit()
    db.refresh(report)
    return to_officer_response(report, db=db)


# ---------------------------------------------------------------------------
# Damkar: tugas saya dan progres
# ---------------------------------------------------------------------------
def _is_assigned(db: Session, report_id: int, officer_id: int) -> bool:
    return (
        db.query(ReportAssignment)
        .filter(ReportAssignment.report_id == report_id, ReportAssignment.officer_id == officer_id)
        .first()
        is not None
    )


def list_tasks(db: Session, officer: Officer, include_done: bool = False):
    statuses = ACTIVE_STATUSES + (("completed",) if include_done else ())
    rows = (
        db.query(Report)
        .join(ReportAssignment, ReportAssignment.report_id == Report.id)
        .filter(ReportAssignment.officer_id == officer.id, Report.status.in_(statuses))
        .order_by(Report.updated_at.desc())
        .limit(50)
        .all()
    )
    return [to_officer_response(r, db=db) for r in rows]


def add_progress(db: Session, identifier, officer: Officer, stage: str, note: str,
                 photo: Optional[UploadFile]):
    report = find_report_by_id_or_code(db, identifier)
    if not _is_assigned(db, report.id, officer.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Laporan ini tidak ditugaskan kepada Anda.")
    if report.status not in ACTIVE_STATUSES:
        raise _bad_request("Laporan ini belum terverifikasi atau sudah selesai.")
    stage = (stage or "").strip().lower()
    if stage not in PROGRESS_STAGES:
        raise _bad_request(f"Tahap tidak valid. Pilih: {', '.join(PROGRESS_STAGES)}.")

    has_photo = photo is not None and getattr(photo, "filename", "")
    if stage == "padam" and not has_photo:
        raise _bad_request("Foto lokasi setelah api padam wajib dilampirkan.")
    photo_url = None
    if has_photo:
        data, ext, _ = validate_and_read_image(photo)
        _, photo_url = save_uploaded_image(data, ext, prefix="tkp")

    clean_note = sanitize_text(note or "", max_length=1000)
    now = datetime.utcnow()
    db.add(ReportProgress(
        report_id=report.id, stage=stage, note=clean_note,
        photo_path=photo_url, created_by=officer.full_name or officer.username, created_at=now,
    ))
    prev = report.status
    new_status = None
    if stage == "padam":
        new_status, label = "completed", f"Api padam. {clean_note}".strip()
    elif prev == "verified":
        new_status, label = "handling", f"Tim Damkar menangani di lapangan. {clean_note}".strip()
    if new_status:
        report.status = new_status
        db.add(ReportHistory(
            report_id=report.id, previous_status=prev, new_status=new_status,
            note=label, changed_by=officer.username, changed_at=now,
        ))
    report.updated_at = now
    db.commit()
    db.refresh(report)
    return to_officer_response(report, db=db)
