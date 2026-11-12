"""
Konfigurasi koneksi Database SQLite dan Session Manager menggunakan SQLAlchemy.
Menggunakan SQLAlchemy asli jika tersedia di environment, atau adaptor sqlite3
kompatibel jika dijalankan pada sandbox terisolasi.
"""
from typing import Generator

from backend.app.config import settings

try:
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        String,
        Text,
        create_engine,
        desc,
        or_,
    )
    from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

    USING_NATIVE_SQLALCHEMY = True
except ImportError:
    from backend.app.utils.sqlalchemy_compat import (  # type: ignore[assignment]
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        Session,
        String,
        Text,
        create_engine,
        declarative_base,
        desc,
        or_,
        relationship,
        sessionmaker,
    )

    USING_NATIVE_SQLALCHEMY = False

# Buat engine SQLite dengan check_same_thread=False untuk FastAPI
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency generator FastAPI untuk menyediakan sesi database per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Inisialisasi seluruh tabel database SQLite."""
    # Import semua model agar terdaftar pada Base.metadata
    from backend.app.models import report, report_history, user  # noqa: F401

    Base.metadata.create_all(bind=engine)


__all__ = [
    "Base",
    "Boolean",
    "Column",
    "DateTime",
    "Float",
    "ForeignKey",
    "Integer",
    "Session",
    "SessionLocal",
    "String",
    "Text",
    "USING_NATIVE_SQLALCHEMY",
    "create_engine",
    "desc",
    "engine",
    "get_db",
    "init_db",
    "or_",
    "relationship",
]
