"""
Pengujian Health Check, Autentikasi, dan Otorisasi Endpoint Petugas (`tests/test_health_and_auth.py`).
"""
import unittest

from tests.conftest import get_test_client_and_token
from backend.app.config import settings


class TestHealthAndAuthentication(unittest.TestCase):
    """Menguji health check sistem, login petugas, dan proteksi endpoint dashboard."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client, cls.officer_token = get_test_client_and_token()

    def test_01_health_check_endpoint(self) -> None:
        """GET /api/health harus mengembalikan status 200 dan informasi konektivitas DB & AI."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["database_connected"])
        self.assertIn("ai_status", data)
        self.assertIn("default_map_center", data)
        self.assertAlmostEqual(data["default_map_center"]["lat"], settings.DEFAULT_MAP_LAT, places=3)

    def test_02_root_json_metadata(self) -> None:
        """GET /?format=json harus mengembalikan metadata aplikasi ApiWaspada."""
        resp = self.client.get("/?format=json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("pages", data)

    def test_03_officer_login_valid_and_invalid(self) -> None:
        """POST /api/auth/login harus menerima kredensial valid dan menolak password salah."""
        ok_resp = self.client.post(
            "/api/auth/login",
            json={
                "username": settings.DEFAULT_ADMIN_USERNAME,
                "password": settings.DEFAULT_ADMIN_PASSWORD,
            },
        )
        self.assertEqual(ok_resp.status_code, 200)
        body = ok_resp.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["officer"]["username"], settings.DEFAULT_ADMIN_USERNAME)

        bad_resp = self.client.post(
            "/api/auth/login",
            json={
                "username": settings.DEFAULT_ADMIN_USERNAME,
                "password": "PasswordSalah123!",
            },
        )
        self.assertEqual(bad_resp.status_code, 401)

    def test_04_protected_endpoints_reject_unauthenticated(self) -> None:
        """Endpoint dashboard dan update status harus menolak akses tanpa token petugas (401)."""
        fresh_client = self.client.__class__(self.client.app)
        fresh_client.cookies.clear()

        r_stats = fresh_client.get("/api/dashboard/stats")
        self.assertEqual(r_stats.status_code, 401)

        r_reports = fresh_client.get("/api/dashboard/reports")
        self.assertEqual(r_reports.status_code, 401)

        r_patch = fresh_client.patch(
            "/api/reports/1/status",
            json={"status": "verified", "note": "Percobaan tanpa token"},
        )
        self.assertEqual(r_patch.status_code, 401)

    def test_05_officer_profile_me_endpoint(self) -> None:
        """GET /api/auth/me dengan token valid harus mengembalikan profil petugas."""
        resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.officer_token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["username"], settings.DEFAULT_ADMIN_USERNAME)


if __name__ == "__main__":
    unittest.main()
