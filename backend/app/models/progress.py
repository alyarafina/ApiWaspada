"""
Model `report_progress`: tahapan penanganan di lapangan oleh Petugas Damkar (UC-09).
"""
from datetime import datetime

from backend.app.database import Base, Column, DateTime, ForeignKey, Integer, String, Text

# Tahapan penanganan, berurutan
PROGRESS_STAGES = ("berangkat", "tiba", "pemadaman", "padam")
PROGRESS_STAGE_LABELS = {
    "berangkat": "Tim Damkar berangkat",
    "tiba": "Tim Damkar tiba di lokasi",
    "pemadaman": "Pemadaman sedang berlangsung",
    "padam": "Api padam",
}


class ReportProgress(Base):
    """Satu catatan tahapan penanganan di lapangan (bisa disertai foto)."""

    __tablename__ = "report_progress"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(32), nullable=False)
    note = Column(Text, nullable=False, default="")
    photo_path = Column(String(500), nullable=True)
    created_by = Column(String(100), nullable=True, default="damkar")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
