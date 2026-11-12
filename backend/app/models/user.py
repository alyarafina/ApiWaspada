"""
Model Database Tabel `officers` untuk menyimpan akun petugas verifikasi dashboard.
"""
from datetime import datetime

from backend.app.database import (
    Base,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)


class Officer(Base):
    """Representasi tabel `officers` pada database SQLite."""

    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False, default="Petugas Verifikasi")
    role = Column(String(32), nullable=False, default="officer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
