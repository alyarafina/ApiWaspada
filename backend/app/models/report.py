"""
Model Database Tabel `reports` untuk menyimpan laporan dugaan kebakaran masyarakat.
"""
from datetime import datetime

from backend.app.database import (
    Base,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    relationship,
)


class Report(Base):
    """Representasi tabel `reports` pada database SQLite."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    tracking_code = Column(String(32), unique=True, index=True, nullable=False)
    reporter_name = Column(String(120), nullable=True, default="Masyarakat")
    description = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    image_path = Column(String(500), nullable=False)
    result_image_path = Column(String(500), nullable=True)
    detection_result = Column(
        String(120),
        nullable=False,
        default="Deteksi gagal atau model belum tersedia",
    )
    detection_confidence = Column(Float, nullable=False, default=0.0)
    detections_json = Column(Text, nullable=True, default="[]")
    inference_time_ms = Column(Float, nullable=True, default=0.0)
    ai_model_used = Column(String(120), nullable=True, default="none")
    status = Column(String(32), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relasi ke riwayat perubahan status laporan
    histories = relationship(
        "ReportHistory",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="desc(ReportHistory.changed_at)",
    )
