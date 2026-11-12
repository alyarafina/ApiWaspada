"""
Schema Pydantic untuk Autentikasi Petugas Dashboard.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Payload login petugas (`POST /api/auth/login`)."""

    username: str = Field(..., min_length=3, max_length=64, description="Username petugas")
    password: str = Field(..., min_length=4, max_length=128, description="Password petugas")


class OfficerProfileResponse(BaseModel):
    """Informasi profil petugas yang sedang login."""

    id: int
    username: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    """Response sukses autentikasi petugas."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    officer: OfficerProfileResponse
