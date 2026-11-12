"""
Router untuk Health Check dan Informasi Sistem (`/api/health`).
"""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.database import Session, get_db
from backend.app.models.report import Report
from backend.app.services.ai_service import ai_service

router = APIRouter(tags=["General & Health"])


class HealthResponse(BaseModel):
    """Schema response pemeriksaan kesehatan sistem."""

    status: str
    app_name: str
    version: str
    environment: str
    database_connected: bool
    total_reports: int
    ai_status: Dict[str, Any]
    default_map_center: Dict[str, float]
    timestamp: datetime


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Pemeriksaan status kesehatan backend, database SQLite, dan modul AI YOLO",
)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Memeriksa konektivitas database SQLite dan status ketersediaan model AI YOLO."""
    db_ok = True
    report_count = 0
    try:
        report_count = db.query(Report).count()
    except Exception:
        db_ok = False

    ai_stat = ai_service.get_status()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        database_connected=db_ok,
        total_reports=report_count,
        ai_status={
            "ai_available": ai_stat.ai_available,
            "status_label": ai_stat.status_label,
            "device": ai_stat.device,
            "model_path": ai_stat.model_path,
        },
        default_map_center={
            "lat": settings.DEFAULT_MAP_LAT,
            "lng": settings.DEFAULT_MAP_LNG,
            "zoom": float(settings.DEFAULT_MAP_ZOOM),
        },
        timestamp=datetime.utcnow(),
    )
