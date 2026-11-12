"""
Script Prediksi Gambar Api & Asap Menggunakan YOLO (`ml/predict.py`).

Mendukung:
- Prediksi satu gambar (`--source path/to/image.jpg`)
- Prediksi banyak gambar sekaligus dalam satu folder (`--source path/to/folder/`)
- Menyimpan hasil visualisasi bounding box, nama kelas (`Fire` / `Smoke`), dan
  confidence score ke folder output (`storage/results/` atau `--output-dir`).
- Menangani ketiadaan `ml/weights/best.pt` secara anggun dengan laporan status yang jelas.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.services.ai_service import AIDetectionService  # noqa: E402

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def collect_image_paths(source_path: Path) -> List[Path]:
    """Mengumpulkan daftar file gambar dari satu file atau satu direktori."""
    if not source_path.exists():
        return []
    if source_path.is_file() and source_path.suffix.lower() in IMAGE_EXTENSIONS:
        return [source_path]
    if source_path.is_dir():
        return sorted(
            [
                p
                for p in source_path.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            ]
        )
    return []


def run_batch_prediction(
    source: Path,
    weights: Path,
    conf_threshold: float = 0.25,
) -> Dict[str, Any]:
    """Menjalankan prediksi untuk satu atau banyak gambar dan mengembalikan ringkasan JSON."""
    images = collect_image_paths(source)
    if not images:
        return {
            "success": False,
            "error": f"Tidak ditemukan file gambar valid pada path: {source}",
            "results": [],
        }

    service = AIDetectionService()
    service.model_path = weights.resolve()
    service.conf_threshold = conf_threshold

    status_info = service.get_status()
    results_list: List[Dict[str, Any]] = []

    for img_path in images:
        det_res = service.run_detection(
            image_path=img_path,
            original_image_url=str(img_path),
            conf_threshold=conf_threshold,
        )
        results_list.append(
            {
                "input_image": str(img_path),
                "result_visualization": det_res.result_image_url,
                "ai_available": det_res.ai_available,
                "detection_status": det_res.detection_status,
                "highest_confidence": det_res.highest_confidence,
                "total_objects": det_res.total_objects,
                "detections": [d.dict() for d in det_res.detections],
                "inference_time_ms": det_res.inference_time_ms,
            }
        )

    return {
        "success": True,
        "ai_status": status_info.status_label,
        "total_images_processed": len(results_list),
        "results": results_list,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Script Prediksi Satu atau Banyak Gambar Menggunakan YOLO ApiWaspada"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path menuju satu file gambar (.jpg/.png) atau direktori berisi banyak gambar",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="ml/weights/best.pt",
        help="Path menuju file model YOLO (default: ml/weights/best.pt)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Ambang batas confidence deteksi (default: 0.25)",
    )
    args = parser.parse_args()

    summary = run_batch_prediction(
        source=Path(args.source),
        weights=Path(args.weights),
        conf_threshold=args.conf,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
