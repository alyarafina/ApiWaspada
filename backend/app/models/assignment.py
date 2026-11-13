"""
Model `report_assignments`: petugas Damkar yang ditugaskan Operator untuk satu laporan.
"""
from datetime import datetime

from backend.app.database import Base, Column, DateTime, ForeignKey, Integer, String


class ReportAssignment(Base):
    __tablename__ = "report_assignments"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    officer_id = Column(Integer, ForeignKey("officers.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by = Column(String(100), nullable=True, default="operator")
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
