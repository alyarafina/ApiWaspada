"""
Script Evaluasi Model YOLO ApiWaspada (`ml/evaluate.py`).

Mengevaluasi model yang sesungguhnya (`ml/weights/best.pt`) menggunakan metrik:
- Precision (P)
- Recall (R)
- mAP@0.5
- mAP@0.5:0.95
- Confusion Matrix & Precision-Recall Curve (dihasilkan oleh validator YOLO di folder output)
- Visualisasi kurva Training Loss & Validation Loss dari `results.csv` hasil pelatihan.

Catatan: Script ini TIDAK menghasilkan metrik palsu. Apabila model atau dataset
belum tersedia, script berhenti dengan pesan informatif.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_training_history_from_csv(results_csv_path: Path, output_plot_path: Path) -> bool:
    """
    Membaca file `results.csv` asli dari Ultralytics YOLO dan membuat grafik
    Training Loss vs Validation Loss serta kurva mAP.
    """
    if not results_csv_path.exists():
        return False

    epochs: List[int] = []
    train_box_loss: List[float] = []
    val_box_loss: List[float] = []
    map50: List[float] = []
    map50_95: List[float] = []

    with open(results_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            try:
                epochs.append(int(float(clean_row.get("epoch", len(epochs) + 1))))
                train_box_loss.append(float(clean_row.get("train/box_loss", 0.0)))
                val_box_loss.append(float(clean_row.get("val/box_loss", 0.0)))
                map50.append(float(clean_row.get("metrics/mAP50(B)", 0.0)))
                map50_95.append(float(clean_row.get("metrics/mAP50-95(B)", 0.0)))
            except ValueError:
                continue

    if not epochs:
        return False

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].plot(epochs, train_box_loss, label="Train Box Loss", color="#DC2626", linewidth=2)
    axes[0].plot(epochs, val_box_loss, label="Val Box Loss", color="#F97316", linewidth=2)
    axes[0].set_title("Training vs Validation Box Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(True, linestyle="--", alpha=0.4)
    axes[0].legend()

    axes[1].plot(epochs, map50, label="mAP@0.5", color="#2563EB", linewidth=2)
    axes[1].plot(epochs, map50_95, label="mAP@0.5:0.95", color="#16A34A", linewidth=2)
    axes[1].set_title("Validation mAP Progression")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("mAP")
    axes[1].grid(True, linestyle="--", alpha=0.4)
    axes[1].legend()

    plt.tight_layout()
    output_plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_plot_path), dpi=150)
    plt.close(fig)
    return True


def evaluate_model(
    weights_path: Path,
    data_yaml_path: Path,
    split: str = "val",
    imgsz: int = 640,
    batch: int = 16,
    device: str = "auto",
    output_dir: Path = Path("ml/runs/eval"),
) -> Dict[str, Any]:
    """Menjalankan evaluasi resmi Ultralytics YOLO pada split `val` atau `test`."""
    if not weights_path.exists() or weights_path.stat().st_size <= 1024:
        return {
            "evaluated": False,
            "error": (
                f"File model bobot '{weights_path}' belum tersedia. "
                "Lakukan pelatihan model terlebih dahulu sebelum menjalankan evaluasi."
            ),
        }

    if not data_yaml_path.exists():
        return {
            "evaluated": False,
            "error": f"File konfigurasi dataset '{data_yaml_path}' tidak ditemukan.",
        }

    try:
        import torch
        from ultralytics import YOLO
    except ImportError:
        return {
            "evaluated": False,
            "error": "Pustaka 'ultralytics' dan 'torch' diperlukan untuk menjalankan evaluasi.",
        }

    resolved_device = device
    if device.lower() in ("auto", ""):
        resolved_device = "0" if torch.cuda.is_available() else "cpu"

    model = YOLO(str(weights_path))
    metrics = model.val(
        data=str(data_yaml_path),
        split=split,
        imgsz=imgsz,
        batch=batch,
        device=resolved_device,
        project=str(output_dir),
        name=f"eval_{split}",
        plots=True,
        exist_ok=True,
    )

    box_metrics = getattr(metrics, "box", None)
    precision = float(getattr(box_metrics, "mp", 0.0)) if box_metrics else 0.0
    recall = float(getattr(box_metrics, "mr", 0.0)) if box_metrics else 0.0
    map50 = float(getattr(box_metrics, "map50", 0.0)) if box_metrics else 0.0
    map50_95 = float(getattr(box_metrics, "map", 0.0)) if box_metrics else 0.0

    save_dir = Path(getattr(metrics, "save_dir", output_dir / f"eval_{split}"))
    summary = {
        "evaluated": True,
        "weights": str(weights_path),
        "data_yaml": str(data_yaml_path),
        "split": split,
        "metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "mAP_50": round(map50, 4),
            "mAP_50_95": round(map50_95, 4),
        },
        "artifacts": {
            "save_dir": str(save_dir),
            "confusion_matrix": str(save_dir / "confusion_matrix.png"),
            "pr_curve": str(save_dir / "PR_curve.png"),
        },
    }

    summary_file = save_dir / f"evaluation_summary_{split}.json"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Script Evaluasi Model YOLO ApiWaspada")
    parser.add_argument(
        "--weights",
        type=str,
        default="ml/weights/best.pt",
        help="Path menuju file bobot model YOLO (default: ml/weights/best.pt)",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="ml/data.yaml",
        help="Path menuju file data.yaml",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="val",
        choices=["val", "test"],
        help="Split dataset yang dievaluasi: 'val' (default) atau 'test' (evaluasi final)",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Ukuran gambar evaluasi")
    parser.add_argument("--batch", type=int, default=16, help="Ukuran batch evaluasi")
    parser.add_argument("--device", type=str, default="auto", help="Device komputasi")
    parser.add_argument(
        "--results-csv",
        type=str,
        default=None,
        help="Opsional: Path menuju results.csv hasil training untuk membuat plot loss",
    )
    args = parser.parse_args()

    if args.results_csv:
        csv_path = Path(args.results_csv)
        plot_out = Path("ml/runs/eval/training_validation_loss_curve.png")
        if plot_training_history_from_csv(csv_path, plot_out):
            print(f"[INFO] Grafik Training & Validation Loss disimpan di: {plot_out}")

    res = evaluate_model(
        weights_path=Path(args.weights),
        data_yaml_path=Path(args.data),
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("evaluated") else 1


if __name__ == "__main__":
    sys.exit(main())
