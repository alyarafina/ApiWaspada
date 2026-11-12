"""
Script Inisialisasi Database SQLite dan Akun Petugas Default (`scripts/init_admin.py`).
Dapat dijalankan langsung melalui terminal:
    python scripts/init_admin.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.config import settings  # noqa: E402
from backend.app.database import SessionLocal, init_db  # noqa: E402
from backend.app.services.auth_service import ensure_default_officer  # noqa: E402


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        officer = ensure_default_officer(db)
        print(
            f"[OK] Database SQLite siap di: {settings.DATABASE_PATH}\n"
            f"[OK] Akun petugas aktif    : username='{officer.username}' ({officer.full_name})"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
