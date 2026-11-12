"""
Pengujian Halaman Frontend, Responsivitas CSS, Notebook Training, dan Script ML
(`tests/test_frontend_and_ml_scripts.py`).
"""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from backend.app.config import settings
from ml.check_dataset import check_dataset, convert_pixel_bbox_to_yolo
from ml.evaluate import plot_training_history_from_csv
from ml.predict import run_batch_prediction
from tests.conftest import create_test_image_bytes, get_test_client_and_token


class TestFrontendAndMLPipeline(unittest.TestCase):
    """Menguji ketersediaan halaman frontend, struktur notebook 22 bagian, dan script ML."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client, _ = get_test_client_and_token()

    def test_01_all_frontend_pages_served_and_contain_no_dead_links(self) -> None:
        """Semua 6 halaman HTML frontend harus dapat diakses (HTTP 200) dan tidak memiliki link kosong."""
        pages = [
            "/index.html",
            "/report.html",
            "/tracking.html",
            "/login.html",
            "/dashboard.html",
            "/report-detail.html",
        ]
        for page in pages:
            resp = self.client.get(page)
            self.assertEqual(resp.status_code, 200, f"Gagal memuat {page}")
            html_text = resp.text
            self.assertNotIn('href="#"', html_text, f"Ditemukan link kosong di {page}")
            self.assertNotIn('href=""', html_text, f"Ditemukan link kosong di {page}")

        # Pastikan disclaimer wajib tercantum pada halaman masyarakat dan hasil deteksi
        report_html = self.client.get("/report.html").text
        self.assertIn(
            "Hasil deteksi AI merupakan indikasi awal berdasarkan gambar yang diunggah dan bukan konfirmasi resmi kejadian kebakaran. Setiap laporan tetap memerlukan verifikasi petugas.",
            report_html,
        )

    def test_02_frontend_assets_and_responsive_css(self) -> None:
        """Static assets (CSS, JS, SVG logo) harus dapat dimuat dan memiliki aturan responsif @media."""
        css_resp = self.client.get("/assets/css/style.css")
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn("@media", css_resp.text)

        logo_resp = self.client.get("/assets/images/logo.svg")
        self.assertEqual(logo_resp.status_code, 200)
        self.assertIn("<svg", logo_resp.text)

        for js_file in ("config.js", "utils.js", "map.js", "report.js", "tracking.js", "auth.js", "dashboard.js", "report-detail.js"):
            js_resp = self.client.get(f"/assets/js/{js_file}")
            self.assertEqual(js_resp.status_code, 200, f"Gagal memuat /assets/js/{js_file}")

    def test_03_jupyter_notebook_structure_22_sections(self) -> None:
        """File ApiWaspada_Training_YOLO.ipynb harus berupa JSON notebook valid dengan 22 bagian lengkap."""
        nb_path = settings.BASE_DIR / "ml" / "ApiWaspada_Training_YOLO.ipynb"
        self.assertTrue(nb_path.exists(), "Notebook ApiWaspada_Training_YOLO.ipynb tidak ditemukan")
        nb_data = json.loads(nb_path.read_text(encoding="utf-8"))
        self.assertEqual(nb_data.get("nbformat"), 4)
        cells = nb_data.get("cells", [])
        self.assertGreaterEqual(len(cells), 40)

        md_headers = [
            "".join(c.get("source", []))
            for c in cells
            if c.get("cell_type") == "markdown"
        ]
        self.assertEqual(len(md_headers), 22)
        for sec_num in range(1, 23):
            self.assertTrue(
                any(f"# {sec_num}." in h for h in md_headers),
                f"Bagian #{sec_num} belum ada di notebook",
            )

    def test_04_ml_check_dataset_and_annotation_validation(self) -> None:
        """Menguji ml/check_dataset.py dengan struktur dataset YOLO sintetis (train/val/test)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ds_root = Path(tmpdir) / "DFireSynthetic"
            for split in ("train", "val", "test"):
                (ds_root / split / "images").mkdir(parents=True, exist_ok=True)
                (ds_root / split / "labels").mkdir(parents=True, exist_ok=True)

            (ds_root / "classes.txt").write_text("smoke\nfire\n", encoding="utf-8")

            # Buat 3 gambar di train: 1 fire+smoke, 1 only smoke, 1 negative (empty label)
            for idx, lbl_content in enumerate(
                [
                    "0 0.5 0.5 0.3 0.3\n1 0.4 0.6 0.2 0.2\n",
                    "0 0.3 0.3 0.2 0.2\n",
                    "",
                ],
                start=1,
            ):
                img_path = ds_root / "train" / "images" / f"sample_{idx}.jpg"
                lbl_path = ds_root / "train" / "labels" / f"sample_{idx}.txt"
                Image.new("RGB", (320, 240), color=(40, 40, 40)).save(img_path)
                lbl_path.write_text(lbl_content, encoding="utf-8")

            # Buat 1 gambar di val
            val_img = ds_root / "val" / "images" / "val_1.jpg"
            val_lbl = ds_root / "val" / "labels" / "val_1.txt"
            Image.new("RGB", (320, 240), color=(60, 60, 60)).save(val_img)
            val_lbl.write_text("1 0.5 0.5 0.4 0.4\n", encoding="utf-8")

            out_yaml = Path(tmpdir) / "data_test.yaml"
            report = check_dataset(ds_root, output_yaml_path=out_yaml)
            self.assertTrue(report["dataset_ready"])
            self.assertEqual(report["class_mapping"], {0: "smoke", 1: "fire"})
            self.assertEqual(report["splits"]["train"]["total_images"], 3)
            self.assertEqual(
                report["splits"]["train"]["image_categories"],
                {"only_fire": 0, "only_smoke": 1, "fire_and_smoke": 1, "none": 1},
            )
            self.assertTrue(out_yaml.exists())

        # Uji juga konversi koordinat piksel ke YOLO
        xc, yc, wn, hn = convert_pixel_bbox_to_yolo(100, 50, 300, 250, 400, 400)
        self.assertAlmostEqual(xc, 0.5)
        self.assertAlmostEqual(yc, 0.375)
        self.assertAlmostEqual(wn, 0.5)
        self.assertAlmostEqual(hn, 0.5)

    def test_05_ml_evaluate_loss_plot_and_batch_predict(self) -> None:
        """Menguji fungsi visualisasi kurva loss pada evaluate.py dan prediksi batch pada predict.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            csv_file = tmp_path / "results.csv"
            csv_file.write_text(
                "epoch,train/box_loss,val/box_loss,metrics/mAP50(B),metrics/mAP50-95(B)\n"
                "1,1.45,1.38,0.42,0.21\n"
                "2,1.12,1.15,0.61,0.34\n"
                "3,0.89,0.94,0.75,0.46\n",
                encoding="utf-8",
            )
            plot_file = tmp_path / "loss_plot.png"
            ok = plot_training_history_from_csv(csv_file, plot_file)
            self.assertTrue(ok)
            self.assertTrue(plot_file.exists())

            # Uji batch prediction pada folder berisi 2 gambar
            imgs_dir = tmp_path / "batch_imgs"
            imgs_dir.mkdir()
            (imgs_dir / "img1.jpg").write_bytes(create_test_image_bytes("JPEG"))
            (imgs_dir / "img2.png").write_bytes(create_test_image_bytes("PNG"))

            pred_summary = run_batch_prediction(
                source=imgs_dir,
                weights=settings.YOLO_MODEL_PATH,
                conf_threshold=0.25,
            )
            self.assertTrue(pred_summary["success"])
            self.assertEqual(pred_summary["total_images_processed"], 2)


if __name__ == "__main__":
    unittest.main()
