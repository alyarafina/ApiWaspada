"""
Layanan Autentikasi dan Pengelolaan Akun Petugas Dashboard ApiWaspada.
"""
from datetime import datetime
from typing import Optional

from backend.app.config import settings
from backend.app.core.exceptions import UnauthorizedAccessError
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.database import Session
from backend.app.models.user import Officer
from backend.app.schemas.auth import OfficerProfileResponse, TokenResponse


def ensure_default_officer(db: Session) -> Officer:
    """
    Memastikan akun petugas default tersedia di database saat aplikasi dijalankan.
    """
    existing = (
        db.query(Officer)
        .filter(Officer.username == settings.DEFAULT_ADMIN_USERNAME)
        .first()
    )
    if existing:
        return existing

    officer = Officer(
        username=settings.DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        full_name=settings.DEFAULT_ADMIN_FULLNAME,
        role="admin",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(officer)
    db.commit()
    db.refresh(officer)
    return officer


def authenticate_officer(db: Session, username: str, password: str) -> TokenResponse:
    """Memvalidasi kredensial petugas dan menerbitkan JWT access token."""
    ensure_default_officer(db)
    clean_username = username.strip()
    officer: Optional[Officer] = (
        db.query(Officer).filter(Officer.username == clean_username).first()
    )
    if not officer or not officer.is_active:
        raise UnauthorizedAccessError("Username atau password petugas tidak sesuai.")

    if not verify_password(password, officer.password_hash):
        raise UnauthorizedAccessError("Username atau password petugas tidak sesuai.")

    token = create_access_token(
        subject=officer.username,
        role=officer.role,
        full_name=officer.full_name,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        officer=OfficerProfileResponse(
            id=officer.id,
            username=officer.username,
            full_name=officer.full_name,
            role=officer.role,
        ),
    )
