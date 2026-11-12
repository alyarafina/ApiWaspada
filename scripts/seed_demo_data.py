"""
Script Pengisian Data Simulasi Pengembangan (`scripts/seed_demo_data.py`).
Sesuai Bagian 12 ("Gunakan data simulasi selama pengembangan"), script ini
memungkinkan pengembang membuat sampel laporan simulasi di wilayah Kota Jambi
beserta gambar uji agar peta GIS dan grafik Dashboard dapat langsung diuji.
"""
import io
import sys
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageDraw
from starlette.datastructures import Headers

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.database import SessionLocal, init_db  # noqa: E402
from backend.app.models.report import Report  # noqa: E402
from backend.app.schemas.report import ReportStatusUpdateRequest  # noqa: E402
from backend.app.services.auth_service import ensure_default_officer  # noqa: E402
from backend.app.services.report_service import (  # noqa: E402
    create_new_report,
    update_report_status,
)


def _generate_synthetic_scene_image(scene_type: str = "fire") -> bytes:
    """Membuat gambar simulasi sederhana untuk keperluan data contoh pengembangan."""
    img = Image.new("RGB", (640, 420), color=(30, 41, 59))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 640, 260], fill=(51, 65, 85))
    draw.rectangle([0, 260, 640, 420], fill=(30, 58, 38))

    if scene_type in ("fire", "both"):
        draw.ellipse([220, 140, 360, 290], fill=(220, 38, 38))
        draw.ellipse([245, 175, 335, 285], fill=(249, 115, 22))
        draw.ellipse([265, 205, 315, 280], fill=(250, 204, 21))
    if scene_type in ("smoke", "both"):
        draw.ellipse([260, 40, 450, 165], fill=(148, 163, 184))
        draw.ellipse([310, 20, 500, 130], fill=(203, 213, 225))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf.read()


def seed_development_reports() -> None:
    """Mengisi 4 laporan simulasi di Kota Jambi jika tabel `reports` masih kosong."""
    init_db()
    db = SessionLocal()
    try:
        ensure_default_officer(db)
        existing_count = db.query(Report).count()
        if existing_count > 0:
            print(f"[INFO] Database sudah berisi {existing_count} laporan. Melewati proses seeding.")
            return

        samples = [
            {
                "scene": "both",
                "reporter": "Warga Simpang IV Sipin (Simulasi)",
                "desc": "[SIMULASI PENGEMBANGAN] Terlihat kepulan asap tebal dan nyala api pada lahan semak kering di dekat Jl. Kolonel Abunjani, Kec. Telanaipura, Kota Jambi.",
                "lat": -1.6108,
                "lng": 103.5934,
                "target_status": "verified",
                "officer_note": "Data simulasi pengembangan: Laporan telah diverifikasi oleh petugas piket.",
            },
            {
                "scene": "smoke",
                "reporter": "Warga Pasar Jambi (Simulasi)",
                "desc": "[SIMULASI PENGEMBANGAN] Terlihat indikasi asap putih pekat dari area belakang ruko di kawasan Pasar Kota Jambi.",
                "lat": -1.5892,
                "lng": 103.6158,
                "target_status": "pending",
                "officer_note": "",
            },
            {
                "scene": "fire",
                "reporter": "Warga Paal Merah (Simulasi)",
                "desc": "[SIMULASI PENGEMBANGAN] Tampak titik api pembakaran tumpukan sampah yang merembet ke pagar lahan kosong di Kec. Paal Merah, Kota Jambi.",
                "lat": -1.6385,
                "lng": 103.6482,
                "target_status": "completed",
                "officer_note": "Data simulasi pengembangan: Penanganan di lokasi telah selesai.",
            },
            {
                "scene": "none",
                "reporter": "Warga Kota Baru (Simulasi)",
                "desc": "[SIMULASI PENGEMBANGAN] Laporan pengujian kabut pagi di sekitar Tugu Keris Siginjai, Kota Baru, Kota Jambi.",
                "lat": -1.6324,
                "lng": 103.6055,
                "target_status": "rejected",
                "officer_note": "Data simulasi pengembangan: Setelah diperiksa, objek merupakan kabut lampu jalan, bukan kebakaran.",
            },
        ]

        for idx, item in enumerate(samples, start=1):
            img_bytes = _generate_synthetic_scene_image(item["scene"])
            upload = UploadFile(
                filename=f"simulasi_jambi_{idx}.jpg",
                file=io.BytesIO(img_bytes),
                headers=Headers({"content-type": "image/jpeg"}),
            )
            created = create_new_report(
                db=db,
                image=upload,
                description=item["desc"],
                latitude=item["lat"],
                longitude=item["lng"],
                reporter_name=item["reporter"],
            )
            if item["target_status"] != "pending":
                update_report_status(
                    db=db,
                    identifier=created.id,
                    payload=ReportStatusUpdateRequest(
                        status=item["target_status"],
                        note=item["officer_note"],
                    ),
                    officer_username="petugas_jambi",
                )
        print("[OK] Berhasil menambahkan 4 laporan simulasi pengembangan Kota Jambi.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_development_reports()
