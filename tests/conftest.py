"""
Utilitas bersama untuk pengujian otomatis (`pytest` dan `unittest`) ApiWaspada.
Menyediakan helper pembuatan gambar valid JPEG/PNG di memori serta TestClient FastAPI.
"""
import io
import sys
from pathlib import Path
from typing import Tuple

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.config import settings  # noqa: E402
from backend.app.database import SessionLocal, init_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.services.auth_service import ensure_default_officer  # noqa: E402


def create_test_image_bytes(
    fmt: str = "JPEG", size: Tuple[int, int] = (400, 300), draw_flame: bool = True
) -> bytes:
    """Membuat citra sintetis valid dalam format JPEG atau PNG untuk pengujian upload & AI."""
    img = Image.new("RGB", size, color=(25, 35, 50))
    draw = ImageDraw.Draw(img)
    if draw_flame:
        draw.ellipse([120, 80, 260, 240], fill=(220, 38, 38))
        draw.ellipse([150, 120, 230, 230], fill=(249, 115, 22))
        draw.ellipse([180, 30, 310, 110], fill=(160, 174, 192))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


def get_test_client_and_token() -> Tuple[TestClient, str]:
    """Menginisialisasi database, membuat TestClient FastAPI, dan mengambil token petugas."""
    init_db()
    db = SessionLocal()
    try:
        ensure_default_officer(db)
    finally:
        db.close()

    client = TestClient(app)
    resp = client.post(
        "/api/auth/login",
        json={
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": settings.DEFAULT_ADMIN_PASSWORD,
        },
    )
    assert resp.status_code == 200, f"Login petugas gagal: {resp.text}"
    token = resp.json()["access_token"]
    return client, token
