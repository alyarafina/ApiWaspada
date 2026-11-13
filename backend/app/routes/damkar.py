"""
Router Petugas Damkar:
- Operator: daftar petugas Damkar dan penugasan laporan (`/api/damkar/officers`, `/api/damkar/assign/{id}`)
- Damkar: tugas saya dan progres TKP (`/api/damkar/tasks`, UC-09)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile
from pydantic import BaseModel, Field

from backend.app.database import Session, get_db
from backend.app.dependencies import get_damkar, get_operator
from backend.app.models.user import Officer
from backend.app.schemas.report import ReportOfficerResponse
from backend.app.services import damkar_service

router = APIRouter(prefix="/api/damkar", tags=["Damkar"])


class AssignRequest(BaseModel):
    officer_ids: List[int] = Field(default_factory=list, description="ID petugas Damkar yang ditugaskan")
    all: bool = Field(default=False, description="True = tugaskan semua petugas Damkar aktif")
    note: Optional[str] = Field(default="", max_length=500)


@router.get("/officers", summary="Daftar petugas Damkar aktif (untuk Operator)")
def damkar_officers_endpoint(db: Session = Depends(get_db), _: Officer = Depends(get_operator)) -> List[dict]:
    return damkar_service.list_damkar_officers(db)


@router.post("/assign/{report_id}", response_model=ReportOfficerResponse,
             summary="Tugaskan laporan terverifikasi ke petugas Damkar tertentu atau semua petugas")
def damkar_assign_endpoint(
    payload: AssignRequest,
    report_id: str = Path(...),
    db: Session = Depends(get_db),
    operator: Officer = Depends(get_operator),
) -> ReportOfficerResponse:
    return damkar_service.assign_officers(db, report_id, payload.officer_ids, payload.all, operator, payload.note or "")


@router.get("/tasks", response_model=List[ReportOfficerResponse],
            summary="UC-09: laporan yang ditugaskan kepada petugas Damkar ini")
def damkar_tasks_endpoint(
    include_done: bool = Query(default=False),
    db: Session = Depends(get_db),
    officer: Officer = Depends(get_damkar),
) -> List[ReportOfficerResponse]:
    return damkar_service.list_tasks(db, officer, include_done)


@router.post("/tasks/{report_id}/progress", response_model=ReportOfficerResponse,
             summary="UC-09: catat progres TKP (foto wajib untuk tahap padam)")
def damkar_progress_endpoint(
    report_id: str = Path(...),
    stage: str = Form(..., description="berangkat | tiba | pemadaman | padam"),
    note: Optional[str] = Form(default="", max_length=1000),
    photo: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    officer: Officer = Depends(get_damkar),
) -> ReportOfficerResponse:
    return damkar_service.add_progress(db, report_id, officer, stage, note or "", photo)
