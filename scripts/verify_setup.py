"""
Script Verifikasi Kesiapan Lingkungan dan Struktur Project ApiWaspada (`scripts/verify_setup.py`).
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


REQUIRED_FILES = [
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/database.py",
    "backend/app/dependencies.py",
    "backend/app/services/ai_service.py",
    "backend/app/services/report_service.py",
    "backend/app/services/dashboard_service.py",
    "backend/app/services/auth_service.py",
    "frontend/index.html",
    "frontend/report.html",
    "frontend/tracking.html",
    "frontend/login.html",
    "frontend/dashboard.html",
    "frontend/report-detail.html",
    "frontend/assets/css/style.css",
    "frontend/assets/js/config.js",
    "frontend/assets/js/utils.js",
    "frontend/assets/js/map.js",
    "frontend/assets/js/report.js",
    "frontend/assets/js/tracking.js",
    "frontend/assets/js/auth.js",
    "frontend/assets/js/dashboard.js",
    "frontend/assets/js/report-detail.js",
    "ml/ApiWaspada_Training_YOLO.ipynb",
    "ml/train.py",
    "ml/evaluate.py",
    "ml/predict.py",
    "ml/check_dataset.py",
    "ml/data.yaml",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "README.md",
    "run.bat",
]


def main() -> int:
    print("=" * 68)
    print("  VERIFIKASI STRUKTUR & KONFIGURASI PROJECT APIWASPADA")
    print("=" * 68)
    missing = []
    for rel in REQUIRED_FILES:
        p = BASE_DIR / rel
        if p.exists():
            print(f"  [OK] {rel}")
        else:
            print(f"  [MISSING] {rel}")
            missing.append(rel)

    print("-" * 68)
    if missing:
        print(f"[ERROR] Ditemukan {len(missing)} file yang belum lengkap: {missing}")
        return 1
    print(f"[SUCCESS] Seluruh {len(REQUIRED_FILES)} komponen inti terverifikasi lengkap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
