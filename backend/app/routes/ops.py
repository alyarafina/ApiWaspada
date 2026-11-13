"""
Router Admin Sistem (UC-10): akun petugas dan rekapitulasi laporan (`/api/admin/...`).
"""
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from backend.app.database import Session, get_db
from backend.app.dependencies import get_admin
from backend.app.models.user import Officer
from backend.app.schemas.ops import OfficerCreate, OfficerOut, OfficerUpdate, RecapResponse
from backend.app.services import ops_service

router = APIRouter(tags=["Admin"])


@router.get("/api/admin/officers", response_model=List[OfficerOut], summary="UC-10: semua akun petugas")
def admin_list_officers(db: Session = Depends(get_db), _: Officer = Depends(get_admin)) -> List[OfficerOut]:
    return ops_service.list_officers(db)


@router.post("/api/admin/officers", response_model=OfficerOut, status_code=201, summary="UC-10: buat akun")
def admin_create_officer(payload: OfficerCreate, db: Session = Depends(get_db),
                         _: Officer = Depends(get_admin)) -> OfficerOut:
    return ops_service.create_officer(db, payload)


@router.patch("/api/admin/officers/{officer_id}", response_model=OfficerOut, summary="UC-10: ubah akun")
def admin_update_officer(officer_id: int, payload: OfficerUpdate, db: Session = Depends(get_db),
                         admin: Officer = Depends(get_admin)) -> OfficerOut:
    return ops_service.update_officer(db, officer_id, payload, admin)


@router.get("/api/admin/recap", response_model=RecapResponse, summary="UC-10: rekapitulasi")
def admin_recap(db: Session = Depends(get_db), _: Officer = Depends(get_admin)) -> RecapResponse:
    return ops_service.build_recap(db)


@router.get("/api/admin/recap.csv", summary="UC-10: unduh rekap laporan (CSV)")
def admin_recap_csv(db: Session = Depends(get_db), _: Officer = Depends(get_admin)) -> Response:
    return Response(
        content=ops_service.recap_csv(db),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="rekap-apiwaspada.csv"'},
    )
