"""
Konfigurasi terpusat aplikasi ApiWaspada.
Membaca variabel lingkungan dari file .env atau environment OS dengan nilai default yang aman.
"""
import os
from pathlib import Path
from typing import Dict, List

# Tentukan direktori root proyek (ApiWaspada/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_dotenv_file(dotenv_path: Path) -> None:
    """Memuat file .env secara aman menggunakan python-dotenv atau parser internal."""
    if not dotenv_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=dotenv_path, override=False)
    except ImportError:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val


_load_dotenv_file(BASE_DIR / ".env")
_load_dotenv_file(BASE_DIR / ".env.example")


class Settings:
    """Konfigurasi utama aplikasi ApiWaspada."""

    def __init__(self) -> None:
        self.BASE_DIR: Path = BASE_DIR
        self.APP_NAME: str = os.getenv(
            "APP_NAME",
            "ApiWaspada - Sistem Cerdas Deteksi Visual Api dan Asap Kota Jambi",
        )
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
        self.HOST: str = os.getenv("HOST", "127.0.0.1")
        self.PORT: int = int(os.getenv("PORT", "8000"))

        # Keamanan & Autentikasi
        self.SECRET_KEY: str = os.getenv(
            "SECRET_KEY",
            "ganti-dengan-secret-key-acak-minimal-32-karakter-apiwaspada-jambi",
        )
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
        )
        self.DEFAULT_ADMIN_USERNAME: str = os.getenv(
            "DEFAULT_ADMIN_USERNAME", "petugas_jambi"
        )
        self.DEFAULT_ADMIN_PASSWORD: str = os.getenv(
            "DEFAULT_ADMIN_PASSWORD", "ApiWaspadaJambi2026!"
        )
        self.DEFAULT_ADMIN_FULLNAME: str = os.getenv(
            "DEFAULT_ADMIN_FULLNAME", "Petugas Piket Verifikasi Kota Jambi"
        )

        # CORS
        origins_raw = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500",
        )
        self.ALLOWED_ORIGINS: List[str] = [
            o.strip() for o in origins_raw.split(",") if o.strip()
        ]

        # Database SQLite
        db_url_env = os.getenv("DATABASE_URL", "")
        if db_url_env and db_url_env.startswith("sqlite:///"):
            rel_part = db_url_env.replace("sqlite:///", "")
            if rel_part.startswith("./") or not os.path.isabs(rel_part):
                clean_rel = rel_part.lstrip("./")
                db_file = (self.BASE_DIR / clean_rel).resolve()
            else:
                db_file = Path(rel_part).resolve()
            db_file.parent.mkdir(parents=True, exist_ok=True)
            self.DATABASE_PATH: Path = db_file
            self.DATABASE_URL: str = f"sqlite:///{db_file.as_posix()}"
        else:
            default_db = (self.BASE_DIR / "storage" / "database" / "apiwaspada.db").resolve()
            default_db.parent.mkdir(parents=True, exist_ok=True)
            self.DATABASE_PATH = default_db
            self.DATABASE_URL = f"sqlite:///{default_db.as_posix()}"

        # Direktori penyimpanan file
        upload_rel = os.getenv("UPLOAD_DIR", "storage/uploads")
        result_rel = os.getenv("RESULT_DIR", "storage/results")
        self.UPLOAD_DIR: Path = (
            Path(upload_rel) if os.path.isabs(upload_rel) else (self.BASE_DIR / upload_rel)
        ).resolve()
        self.RESULT_DIR: Path = (
            Path(result_rel) if os.path.isabs(result_rel) else (self.BASE_DIR / result_rel)
        ).resolve()
        self.FRONTEND_DIR: Path = (self.BASE_DIR / "frontend").resolve()

        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.RESULT_DIR.mkdir(parents=True, exist_ok=True)

        # Validasi file upload
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
        self.MAX_UPLOAD_SIZE_BYTES: int = self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        ext_raw = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png")
        self.ALLOWED_EXTENSIONS: List[str] = [
            e.strip().lower().lstrip(".") for e in ext_raw.split(",") if e.strip()
        ]
        self.ALLOWED_MIME_TYPES: List[str] = ["image/jpeg", "image/jpg", "image/png"]

        # Konfigurasi AI YOLO
        model_rel = os.getenv("YOLO_MODEL_PATH", "ml/weights/best.pt")
        self.YOLO_MODEL_PATH: Path = (
            Path(model_rel) if os.path.isabs(model_rel) else (self.BASE_DIR / model_rel)
        ).resolve()
        self.YOLO_CONFIDENCE_THRESHOLD: float = float(
            os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.25")
        )
        self.YOLO_IOU_THRESHOLD: float = float(
            os.getenv("YOLO_IOU_THRESHOLD", "0.45")
        )
        self.YOLO_IMAGE_SIZE: int = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
        self.YOLO_DEVICE: str = os.getenv("YOLO_DEVICE", "auto")

        # Pemetaan kelas default D-Fire Dataset (0: smoke, 1: fire)
        class_map_raw = os.getenv("YOLO_CLASS_MAP", "0:smoke,1:fire")
        self.YOLO_CLASS_MAP: Dict[int, str] = {}
        for item in class_map_raw.split(","):
            if ":" in item:
                k_str, v_str = item.split(":", 1)
                try:
                    self.YOLO_CLASS_MAP[int(k_str.strip())] = v_str.strip().lower()
                except ValueError:
                    pass
        if not self.YOLO_CLASS_MAP:
            self.YOLO_CLASS_MAP = {0: "smoke", 1: "fire"}

        # Konfigurasi GIS Kota Jambi
        self.DEFAULT_MAP_LAT: float = float(os.getenv("DEFAULT_MAP_LAT", "-1.6101"))
        self.DEFAULT_MAP_LNG: float = float(os.getenv("DEFAULT_MAP_LNG", "103.6131"))
        self.DEFAULT_MAP_ZOOM: int = int(os.getenv("DEFAULT_MAP_ZOOM", "12"))
        self.JAMBI_BOUNDS_MIN_LAT: float = float(os.getenv("JAMBI_BOUNDS_MIN_LAT", "-1.8500"))
        self.JAMBI_BOUNDS_MAX_LAT: float = float(os.getenv("JAMBI_BOUNDS_MAX_LAT", "-1.4000"))
        self.JAMBI_BOUNDS_MIN_LNG: float = float(os.getenv("JAMBI_BOUNDS_MIN_LNG", "103.4000"))
        self.JAMBI_BOUNDS_MAX_LNG: float = float(os.getenv("JAMBI_BOUNDS_MAX_LNG", "103.8500"))


settings = Settings()
