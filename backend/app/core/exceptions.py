"""
Definisi exception kustom dan handler error terstandar untuk FastAPI.
"""
from fastapi import HTTPException, status


class InvalidImageError(HTTPException):
    """Exception ketika file gambar tidak valid, rusak, atau melebihi ukuran."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ResourceNotFoundError(HTTPException):
    """Exception ketika data laporan tidak ditemukan di database."""

    def __init__(self, detail: str = "Data laporan tidak ditemukan."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedAccessError(HTTPException):
    """Exception ketika akses ke endpoint petugas tidak memiliki token valid."""

    def __init__(self, detail: str = "Akses ditolak. Silakan login sebagai petugas."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
