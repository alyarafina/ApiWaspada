"""
Schema Pydantic untuk Statistik Dashboard Petugas dan Peta GIS.
"""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.report import ReportOfficerResponse


class DailyReportCount(BaseModel):
    """Jumlah laporan per tanggal untuk grafik garis/batang Chart.js."""

    date: str = Field(..., description="Tanggal dalam format YYYY-MM-DD")
    count: int = Field(..., ge=0, description="Jumlah laporan pada tanggal tersebut")


class DashboardStatsResponse(BaseModel):
    """Response endpoint `GET /api/dashboard/stats`."""

    total_reports: int = Field(..., ge=0)
    pending_count: int = Field(..., ge=0)
    verified_count: int = Field(..., ge=0)
    rejected_count: int = Field(..., ge=0)
    completed_count: int = Field(..., ge=0)
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    detection_distribution: Dict[str, int] = Field(default_factory=dict)
    reports_by_date: List[DailyReportCount] = Field(default_factory=list)
    ai_active: bool = Field(default=False)
    last_updated: datetime


class DashboardReportsResponse(BaseModel):
    """Response daftar laporan untuk tabel Dashboard Petugas (`GET /api/dashboard/reports`)."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ReportOfficerResponse]


class MapMarkerItem(BaseModel):
    """Data titik koordinat laporan untuk marker Leaflet.js."""

    id: int
    tracking_code: str
    latitude: float
    longitude: float
    detection_result: str
    detection_confidence: float
    status: str
    status_label_id: str
    description_excerpt: str
    image_url: str
    result_image_url: Optional[str] = None
    created_at: datetime


class MapDataResponse(BaseModel):
    """Response endpoint `GET /api/dashboard/map`."""

    total_markers: int
    center_lat: float
    center_lng: float
    default_zoom: int
    markers: List[MapMarkerItem]
