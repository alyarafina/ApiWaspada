"""
Dependencies FastAPI untuk injeksi sesi database dan otorisasi token petugas.
"""
from typing import Optional
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.exceptions import UnauthorizedAccessError
from backend.app.core.security import decode_access_token
from backend.app.database import Session, get_db
from backend.app.models.user import Officer

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_officer(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_token: Optional[str] = Header(default=None, alias="X-Officer-Token"),
    db: Session = Depends(get_db),
) -> Officer:
    """
    Memvalidasi token Bearer (atau header X-Officer-Token / cookie session)
    dan memastikan pengguna adalah petugas aktif yang terdaftar di database.
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    elif x_api_token:
        token = x_api_token
    elif "apiwaspada_token" in request.cookies:
        token = request.cookies.get("apiwaspada_token")

    if not token:
        raise UnauthorizedAccessError(
            "Token autentikasi tidak ditemukan. Silakan login sebagai petugas."
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedAccessError(
            "Sesi login tidak valid atau telah kedaluwarsa. Silakan login kembali."
        )

    username = str(payload["sub"])
    officer = db.query(Officer).filter(Officer.username == username).first()
    if not officer or not officer.is_active:
        raise UnauthorizedAccessError(
            "Akun petugas tidak ditemukan atau tidak aktif."
        )

    return officer
