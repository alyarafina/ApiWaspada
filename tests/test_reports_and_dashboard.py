"""
Pengujian Integrasi End-to-End Laporan, Riwayat Status, Dashboard, dan Peta GIS
(`tests/test_reports_and_dashboard.py`).
"""
import unittest

from backend.app.services.ai_service import ai_service
from tests.conftest import create_test_image_bytes, get_test_client_and_token


class TestReportsDashboardAndGIS(unittest.TestCase):
    """Menguji alur pembuatan laporan masyarakat hingga verifikasi petugas di dashboard & peta."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client, cls.officer_token = get_test_client_and_token()
        cls.auth_headers = {"Authorization": f"Bearer {cls.officer_token}"}

    def tearDown(self) -> None:
        ai_service.set_custom_predictor(None)

    def test_01_create_read_update_report_and_history_flow(self) -> None:
        """
        Alur terintegrasi:
        1. Masyarakat mengirim laporan dengan foto & koordinat Kota Jambi (`POST /api/reports`)
        2. Publik memeriksa laporan via ID & kode pelacakan (`GET /api/reports/{id}`), memastikan nama pelapor tidak bocor di publik
        3. Petugas memperbarui status ke `verified` lalu `completed` (`PATCH /api/reports/{id}/status`)
        4. Riwayat status tercatat lengkap (`GET /api/reports/{id}/history`)
        5. Statistik dashboard (`GET /api/dashboard/stats`) dan marker peta (`GET /api/dashboard/map`) mencerminkan laporan tersebut.
        """
        ai_service.set_custom_predictor(
            lambda img, th: [
                {"class_id": 1, "class_name": "fire", "confidence": 0.91, "bbox_xyxy": [100, 100, 240, 220]}
            ]
        )

        img_bytes = create_test_image_bytes("JPEG")
        create_resp = self.client.post(
            "/api/reports",
            files={"image": ("kebakaran_telanaipura.jpg", img_bytes, "image/jpeg")},
            data={
                "description": "Terlihat kobaran api pada lahan semak di sekitar Telanaipura Kota Jambi.",
                "latitude": "-1.6105",
                "longitude": "103.5940",
                "reporter_name": "Budi Santoso (Rahasia)",
            },
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.text)
        created = create_resp.json()

        report_id = created["id"]
        tracking_code = created["tracking_code"]
        self.assertTrue(tracking_code.startswith("AW-"))
        self.assertEqual(created["status"], "pending")
        self.assertEqual(created["detection_result"], "Terdeteksi indikasi api")
        # Pastikan informasi pribadi (reporter_name) TIDAK ditampilkan pada response publik
        self.assertNotIn("reporter_name", created)

        # 2. Ambil laporan berdasarkan tracking_code (publik)
        get_pub = self.client.get(f"/api/reports/{tracking_code}")
        self.assertEqual(get_pub.status_code, 200)
        self.assertEqual(get_pub.json()["id"], report_id)

        # 3. Petugas mengambil detail laporan di dashboard (reporter_name terlihat bagi petugas)
        get_officer = self.client.get(
            f"/api/dashboard/reports/{report_id}", headers=self.auth_headers
        )
        self.assertEqual(get_officer.status_code, 200)
        self.assertEqual(get_officer.json()["reporter_name"], "Budi Santoso (Rahasia)")

        # 4. Petugas memperbarui status menjadi 'verified'
        patch_ver = self.client.patch(
            f"/api/reports/{report_id}/status",
            headers=self.auth_headers,
            json={
                "status": "verified",
                "note": "Tim verifikasi telah mengonfirmasi titik asap dan api di lokasi.",
            },
        )
        self.assertEqual(patch_ver.status_code, 200)
        self.assertEqual(patch_ver.json()["status"], "verified")

        # 5. Petugas memperbarui status menjadi 'completed'
        patch_comp = self.client.patch(
            f"/api/reports/{report_id}/status",
            headers=self.auth_headers,
            json={
                "status": "completed",
                "note": "Api telah berhasil dipadamkan dan lokasi aman.",
            },
        )
        self.assertEqual(patch_comp.status_code, 200)
        self.assertEqual(patch_comp.json()["status"], "completed")

        # 6. Periksa riwayat perubahan status (`GET /api/reports/{id}/history`)
        hist_resp = self.client.get(f"/api/reports/{report_id}/history")
        self.assertEqual(hist_resp.status_code, 200)
        histories = hist_resp.json()
        self.assertGreaterEqual(len(histories), 3)
        statuses_recorded = [h["new_status"] for h in histories]
        self.assertIn("pending", statuses_recorded)
        self.assertIn("verified", statuses_recorded)
        self.assertIn("completed", statuses_recorded)

        # 7. Periksa statistik dashboard (`GET /api/dashboard/stats`)
        stats_resp = self.client.get("/api/dashboard/stats", headers=self.auth_headers)
        self.assertEqual(stats_resp.status_code, 200)
        stats = stats_resp.json()
        self.assertGreaterEqual(stats["total_reports"], 1)
        self.assertGreaterEqual(stats["completed_count"], 1)
        self.assertGreaterEqual(len(stats["reports_by_date"]), 1)

        # 8. Periksa daftar laporan dashboard dengan pencarian (`GET /api/dashboard/reports`)
        table_resp = self.client.get(
            f"/api/dashboard/reports?search={tracking_code}",
            headers=self.auth_headers,
        )
        self.assertEqual(table_resp.status_code, 200)
        self.assertEqual(table_resp.json()["total"], 1)

        # 9. Periksa endpoint peta GIS (`GET /api/dashboard/map`)
        map_resp = self.client.get("/api/dashboard/map")
        self.assertEqual(map_resp.status_code, 200)
        map_data = map_resp.json()
        self.assertGreaterEqual(map_data["total_markers"], 1)
        codes_on_map = [m["tracking_code"] for m in map_data["markers"]]
        self.assertIn(tracking_code, codes_on_map)

    def test_02_validate_coordinates_and_xss_sanitization(self) -> None:
        """Menguji penolakan koordinat di luar batas bumi dan sanitasi tag <script> XSS."""
        img_bytes = create_test_image_bytes("JPEG")

        # Latitude di luar [-90, 90] harus ditolak (400)
        bad_coord = self.client.post(
            "/api/reports",
            files={"image": ("uji.jpg", img_bytes, "image/jpeg")},
            data={
                "description": "Deskripsi laporan pengujian koordinat invalid.",
                "latitude": "-125.0",
                "longitude": "103.61",
            },
        )
        self.assertEqual(bad_coord.status_code, 400)

        # Tag <script> pada deskripsi harus dibersihkan
        xss_resp = self.client.post(
            "/api/reports",
            files={"image": ("uji_xss.jpg", img_bytes, "image/jpeg")},
            data={
                "description": "<script>alert('xss')</script>Asap tebal terlihat di dekat jembatan.",
                "latitude": "-1.6101",
                "longitude": "103.6131",
            },
        )
        self.assertEqual(xss_resp.status_code, 201)
        cleaned_desc = xss_resp.json()["description"]
        self.assertNotIn("<script>", cleaned_desc.lower())


if __name__ == "__main__":
    unittest.main()
