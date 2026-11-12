"""
Model Database Tabel `report_history` untuk mencatat audit trail perubahan status laporan.
"""
from datetime import datetime

from backend.app.database import (
    Base,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    relationship,
)


class ReportHistory(Base):
    """Representasi tabel `report_history` pada database SQLite."""

    __tablename__ = "report_history"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    note = Column(Text, nullable=False, default="")
    changed_by = Column(String(100), nullable=True, default="system")
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    report = relationship("Report", back_populates="histories")
