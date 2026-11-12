"""
Router Autentikasi Petugas Dashboard (`/api/auth`).
"""
from fastapi import APIRouter, Depends, Response, status

from backend.app.database import Session, get_db
from backend.app.dependencies import get_current_officer
from backend.app.models.user import Officer
from backend.app.schemas.auth import (
    LoginRequest,
    OfficerProfileResponse,
    TokenResponse,
)
from backend.app.services.auth_service import authenticate_officer

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login petugas dashboard dan terbitkan token JWT",
)
def login_officer(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Memvalidasi username dan password petugas lalu mengembalikan token Bearer."""
    token_res = authenticate_officer(db, payload.username, payload.password)
    response.set_cookie(
        key="apiwaspada_token",
        value=token_res.access_token,
        httponly=True,
        samesite="lax",
        max_age=token_res.expires_in_minutes * 60,
    )
    return token_res


@router.get(
    "/me",
    response_model=OfficerProfileResponse,
    summary="Ambil informasi profil petugas yang sedang aktif login",
)
def get_me(current_officer: Officer = Depends(get_current_officer)) -> OfficerProfileResponse:
    """Mengembalikan informasi akun petugas berdasarkan token autentikasi yang valid."""
    return OfficerProfileResponse(
        id=current_officer.id,
        username=current_officer.username,
        full_name=current_officer.full_name,
        role=current_officer.role,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout sesi petugas",
)
def logout_officer(response: Response) -> dict:
    """Menghapus cookie sesi petugas."""
    response.delete_cookie("apiwaspada_token")
    return {"message": "Berhasil logout dari sesi petugas."}
