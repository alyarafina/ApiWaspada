"""
Schema Pydantic untuk Laporan Kebakaran (`reports`) dan Riwayat Status (`report_history`).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.detection import AI_DISCLAIMER_TEXT, BoundingBoxItem

VALID_REPORT_STATUSES = ("pending", "verified", "rejected", "completed")


class ReportHistoryItem(BaseModel):
    """Schema item riwayat perubahan status laporan."""

    id: int
    report_id: int
    previous_status: Optional[str] = None
    new_status: str
    note: str
    changed_by: Optional[str] = "system"
    changed_at: datetime


class ReportStatusUpdateRequest(BaseModel):
    """Payload request untuk memperbarui status laporan (`PATCH /api/reports/{report_id}/status`)."""

    status: str = Field(
        ...,
        description="Status baru laporan: pending, verified, rejected, atau completed",
    )
    note: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Catatan verifikasi petugas (wajib diisi, minimal 3 karakter)",
    )


class ReportPublicResponse(BaseModel):
    """
    Schema response laporan untuk halaman publik/masyarakat.
    Sesuai kebijakan keamanan (Bagian 12): tidak menampilkan informasi pribadi
    pelapor pada halaman publik.
    """

    id: int
    tracking_code: str
    description: str
    latitude: float
    longitude: float
    image_url: str
    result_image_url: Optional[str] = None
    detection_result: str
    detection_confidence: float
    detections: List[BoundingBoxItem] = Field(default_factory=list)
    inference_time_ms: float = 0.0
    status: str
    status_label_id: str
    created_at: datetime
    updated_at: datetime
    region_info: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = Field(default=AI_DISCLAIMER_TEXT)


class ReportOfficerResponse(ReportPublicResponse):
    """
    Schema response detail laporan lengkap untuk petugas terautentikasi.
    Menyertakan nama pelapor, informasi model AI, dan riwayat verifikasi.
    """

    reporter_name: Optional[str] = "Masyarakat"
    ai_model_used: Optional[str] = "none"
    histories: List[ReportHistoryItem] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    """Schema response daftar laporan dengan pagination."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ReportPublicResponse]
