"""
Layanan halaman Admin Sistem (UC-10): akun petugas dan rekapitulasi laporan.
"""
import csv
import io
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException, status

from backend.app.core.security import hash_password, sanitize_text
from backend.app.database import Session
from backend.app.dependencies import VALID_ROLES, normalized_role
from backend.app.models.report import Report
from backend.app.models.report_history import ReportHistory
from backend.app.models.user import Officer
from backend.app.schemas.ops import OfficerCreate, OfficerOut, OfficerUpdate, RecapResponse


def _bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ---------------------------------------------------------------------------
# Akun petugas
# ---------------------------------------------------------------------------
def _officer_out(o: Officer) -> OfficerOut:
    return OfficerOut(
        id=o.id, username=o.username, full_name=o.full_name, role=normalized_role(o),
        is_active=bool(o.is_active), created_at=o.created_at,
    )


def list_officers(db: Session) -> List[OfficerOut]:
    return [_officer_out(o) for o in db.query(Officer).order_by(Officer.created_at.asc()).all()]


def _check_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role not in VALID_ROLES:
        raise _bad_request(f"Peran tidak valid. Pilih: {', '.join(VALID_ROLES)}.")
    return role


def create_officer(db: Session, payload: OfficerCreate) -> OfficerOut:
    username = payload.username.strip().lower()
    if db.query(Officer).filter(Officer.username == username).first():
        raise _bad_request("Username sudah dipakai.")
    o = Officer(
        username=username,
        password_hash=hash_password(payload.password),
        full_name=sanitize_text(payload.full_name, max_length=120) or username,
        role=_check_role(payload.role),
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return _officer_out(o)


def update_officer(db: Session, officer_id: int, payload: OfficerUpdate, actor: Officer) -> OfficerOut:
    o = db.query(Officer).filter(Officer.id == officer_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan.")
    role = _check_role(payload.role or normalized_role(o))
    if o.id == actor.id and (role != "admin" or payload.is_active is False):
        raise _bad_request("Anda tidak bisa menurunkan peran atau menonaktifkan akun Anda sendiri.")
    o.role = role
    if payload.full_name:
        o.full_name = sanitize_text(payload.full_name, max_length=120)
    if payload.is_active is not None:
        o.is_active = payload.is_active
    if payload.password:
        o.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(o)
    return _officer_out(o)


# ---------------------------------------------------------------------------
# Rekapitulasi
# ---------------------------------------------------------------------------
def _first_decisions(db: Session) -> Dict[int, datetime]:
    """Waktu keputusan pertama operator (perubahan status pertama dari 'pending') per laporan."""
    first: Dict[int, datetime] = {}
    rows = (
        db.query(ReportHistory)
        .filter(ReportHistory.previous_status == "pending", ReportHistory.new_status != "pending")
        .all()
    )
    for h in rows:
        if h.report_id not in first or h.changed_at < first[h.report_id]:
            first[h.report_id] = h.changed_at
    return first


def build_recap(db: Session) -> RecapResponse:
    reports = db.query(Report).all()
    by_status = Counter(r.status for r in reports)
    by_month = Counter(r.created_at.strftime("%Y-%m") for r in reports if r.created_at)
    decisions = _first_decisions(db)
    minutes: List[float] = []
    for r in reports:
        d = decisions.get(r.id)
        if d and r.created_at and d >= r.created_at:
            minutes.append((d - r.created_at).total_seconds() / 60.0)
    return RecapResponse(
        total_reports=len(reports),
        by_status=dict(by_status),
        by_month=dict(sorted(by_month.items())),
        avg_minutes_to_decision=round(sum(minutes) / len(minutes), 1) if minutes else None,
        rejected_ratio=round(by_status.get("rejected", 0) / len(reports), 3) if reports else 0.0,
        generated_at=datetime.utcnow(),
    )


def recap_csv(db: Session) -> str:
    """Seluruh laporan sebagai CSV untuk diunduh admin (tanpa nama pelapor)."""
    decisions = _first_decisions(db)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["kode", "dibuat_utc", "status", "indikasi_ai", "keyakinan", "latitude", "longitude",
                "keputusan_pertama_utc"])
    for r in db.query(Report).order_by(Report.created_at.asc()).all():
        d: Optional[datetime] = decisions.get(r.id)
        w.writerow([
            r.tracking_code, r.created_at.isoformat() if r.created_at else "", r.status,
            r.detection_result, round(float(r.detection_confidence or 0), 4), r.latitude, r.longitude,
            d.isoformat() if d else "",
        ])
    return buf.getvalue()
