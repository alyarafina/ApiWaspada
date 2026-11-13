"""
Schema Pydantic untuk halaman Admin: akun petugas dan rekapitulasi.
"""
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class OfficerCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., description="admin | operator | damkar")


class OfficerUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class OfficerOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None


class RecapResponse(BaseModel):
    total_reports: int
    by_status: Dict[str, int] = Field(default_factory=dict)
    by_month: Dict[str, int] = Field(default_factory=dict)
    avg_minutes_to_decision: Optional[float] = Field(
        None, description="Rata-rata menit dari laporan masuk sampai keputusan pertama operator"
    )
    rejected_ratio: float = 0.0
    generated_at: datetime
