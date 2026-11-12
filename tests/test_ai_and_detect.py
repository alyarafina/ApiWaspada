"""
Pengujian Layanan Deteksi Visual AI YOLO & Validasi Gambar (`tests/test_ai_and_detect.py`).
Mencakup:
- Pemeriksaan status model (`/api/detect/status`)
- Mode fallback saat `ml/weights/best.pt` belum tersedia
- Inferensi dengan model aktif (menguji visualisasi bounding box, pemetaan kelas `Fire` & `Smoke`,
  perhitungan confidence score, dan kelima status indikasi resmi)
- Penanganan upload gambar tidak valid (ekstensi terlarang, file kosong, file biner rusak).
"""
import unittest
from pathlib import Path

from backend.app.config import settings
from backend.app.services.ai_service import (
    STATUS_FIRE_AND_SMOKE,
    STATUS_FIRE_ONLY,
    STATUS_MODEL_UNAVAILABLE,
    STATUS_NO_DETECTION,
    STATUS_SMOKE_ONLY,
    ai_service,
)
from tests.conftest import create_test_image_bytes, get_test_client_and_token


class TestAIDetectionAndImageValidation(unittest.TestCase):
    """Menguji layanan deteksi visual YOLO dan validasi keamanan file gambar."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client, _ = get_test_client_and_token()

    def tearDown(self) -> None:
        # Kembalikan predictor ke mode default setelah setiap pengujian
        ai_service.set_custom_predictor(None)

    def test_01_ai_status_endpoint(self) -> None:
        """GET /api/detect/status harus mengembalikan informasi kesiapan model dan disclaimer."""
        resp = self.client.get("/api/detect/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ai_available", data)
        self.assertIn("class_mapping", data)
        self.assertIn("Hasil deteksi AI merupakan indikasi awal", data["disclaimer"])

    def test_02_fallback_when_model_unavailable(self) -> None:
        """Jika best.pt belum tersedia, POST /api/detect harus berjalan aman dengan status fallback."""
        ai_service.set_custom_predictor(None)
        img_bytes = create_test_image_bytes("JPEG")
        resp = self.client.post(
            "/api/detect",
            files={"image": ("uji_fallback.jpg", img_bytes, "image/jpeg")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        if not ai_service.model_file_exists():
            self.assertFalse(data["ai_available"])
            self.assertEqual(data["detection_status"], STATUS_MODEL_UNAVAILABLE)
            self.assertEqual(data["total_objects"], 0)
            self.assertTrue(data["result_image_url"].startswith("/storage/results/"))

    def test_03_active_model_fire_and_smoke_detection_and_bbox_visualization(self) -> None:
        """
        Saat model aktif mendeteksi Fire dan Smoke, sistem harus menghasilkan
        status 'Api dan asap terindikasi', daftar bounding box, confidence score,
        dan menyimpan file gambar hasil anotasi di storage/results/.
        """
        def mock_yolo_fire_and_smoke(img_bgr, conf_thresh):
            return [
                {
                    "class_id": 1,
                    "class_name": "fire",
                    "confidence": 0.89,
                    "bbox_xyxy": [110.0, 90.0, 250.0, 230.0],
                },
                {
                    "class_id": 0,
                    "class_name": "smoke",
                    "confidence": 0.76,
                    "bbox_xyxy": [140.0, 20.0, 310.0, 115.0],
                },
            ]

        ai_service.set_custom_predictor(
            mock_yolo_fire_and_smoke, class_mapping={0: "smoke", 1: "fire"}
        )

        img_bytes = create_test_image_bytes("PNG")
        resp = self.client.post(
            "/api/detect",
            files={"image": ("kebakaran_lahan.png", img_bytes, "image/png")},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ai_available"])
        self.assertEqual(data["detection_status"], STATUS_FIRE_AND_SMOKE)
        self.assertTrue(data["fire_detected"])
        self.assertTrue(data["smoke_detected"])
        self.assertEqual(data["total_objects"], 2)
        self.assertAlmostEqual(data["highest_confidence"], 0.89, places=2)

        classes_found = [d["class_name"] for d in data["detections"]]
        self.assertIn("Fire", classes_found)
        self.assertIn("Smoke", classes_found)

        # Pastikan file gambar hasil anotasi benar-benar tersimpan di disk
        result_rel = data["result_image_url"].replace("/storage/results/", "")
        result_file = settings.RESULT_DIR / Path(result_rel).name
        self.assertTrue(result_file.exists())
        self.assertGreater(result_file.stat().st_size, 1000)

    def test_04_active_model_single_class_and_empty_detection_statuses(self) -> None:
        """Menguji status 'Terdeteksi indikasi api', 'Terdeteksi indikasi asap', dan 'Tidak ditemukan indikasi api atau asap'."""
        img_bytes = create_test_image_bytes("JPEG")

        # Hanya Api
        ai_service.set_custom_predictor(
            lambda img, th: [{"class_id": 1, "class_name": "fire", "confidence": 0.81, "bbox_xyxy": [50, 50, 180, 180]}]
        )
        r_fire = self.client.post(
            "/api/detect", files={"image": ("api.jpg", img_bytes, "image/jpeg")}
        ).json()
        self.assertEqual(r_fire["detection_status"], STATUS_FIRE_ONLY)

        # Hanya Asap
        ai_service.set_custom_predictor(
            lambda img, th: [{"class_id": 0, "class_name": "smoke", "confidence": 0.68, "bbox_xyxy": [30, 30, 200, 140]}]
        )
        r_smoke = self.client.post(
            "/api/detect", files={"image": ("asap.jpg", img_bytes, "image/jpeg")}
        ).json()
        self.assertEqual(r_smoke["detection_status"], STATUS_SMOKE_ONLY)

        # Tidak ditemukan api atau asap
        ai_service.set_custom_predictor(lambda img, th: [])
        r_none = self.client.post(
            "/api/detect", files={"image": ("normal.jpg", img_bytes, "image/jpeg")}
        ).json()
        self.assertEqual(r_none["detection_status"], STATUS_NO_DETECTION)

    def test_05_reject_invalid_image_uploads(self) -> None:
        """Sistem harus menolak ekstensi berbahaya (.exe/.txt), file kosong, dan biner rusak."""
        # 1. Ekstensi tidak didukung
        r_ext = self.client.post(
            "/api/detect",
            files={"image": ("script.exe", b"MZ-fake-binary", "application/octet-stream")},
        )
        self.assertEqual(r_ext.status_code, 400)

        # 2. File kosong (0 byte)
        r_empty = self.client.post(
            "/api/detect",
            files={"image": ("kosong.jpg", b"", "image/jpeg")},
        )
        self.assertEqual(r_empty.status_code, 400)

        # 3. File dengan ekstensi .jpg namun berisi teks bukan gambar
        r_corrupt = self.client.post(
            "/api/detect",
            files={"image": ("palsu.jpg", b"ini bukan biner jpeg yang valid", "image/jpeg")},
        )
        self.assertEqual(r_corrupt.status_code, 400)


if __name__ == "__main__":
    unittest.main()
