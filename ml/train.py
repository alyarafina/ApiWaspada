"""
Script Pelatihan Model YOLO ApiWaspada (`ml/train.py`).

Mendukung:
- Transfer learning dari pretrained weights Ultralytics YOLO (`yolov8n.pt`, `yolov8s.pt`, dll.)
- Konfigurasi melalui file YAML (`ml/configs/train_lightweight.yaml` atau `ml/configs/train_experiment.yaml`)
  maupun argumen baris perintah (CLI)
- Deteksi perangkat otomatis: GPU NVIDIA (CUDA) jika tersedia, atau fallback ke CPU
- Early stopping (`patience`), random seed reproduksibel, dan penyalinan otomatis
  bobot terbaik ke `ml/weights/best.pt`.
"""
import argparse
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.check_dataset import check_dataset  # noqa: E402


def resolve_compute_device(requested_device: str = "auto") -> str:
    """Menentukan device training: CUDA GPU jika tersedia, atau CPU."""
    try:
        import torch

        if requested_device.lower() in ("auto", ""):
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                print(f"[INFO] GPU NVIDIA terdeteksi: {gpu_name} (menggunakan device='0')")
                return "0"
            print("[INFO] GPU CUDA tidak terdeteksi. Menggunakan CPU untuk training.")
            return "cpu"
        if requested_device != "cpu" and not torch.cuda.is_available():
            print("[WARN] CUDA diminta tetapi tidak tersedia. Beralih ke CPU.")
            return "cpu"
        return requested_device
    except ImportError:
        return "cpu"


def load_training_config(config_path: Path) -> Dict[str, Any]:
    """Memuat konfigurasi hyperparameter dari file YAML."""
    default_cfg: Dict[str, Any] = {
        "base_model": "yolov8n.pt",
        "data_yaml": "ml/data.yaml",
        "imgsz": 416,
        "batch": 8,
        "epochs": 10,
        "lr0": 0.01,
        "lrf": 0.01,
        "optimizer": "auto",
        "patience": 5,
        "device": "auto",
        "workers": 2,
        "seed": 42,
        "project_dir": "ml/runs/detect",
        "experiment_name": "apiwaspada_dfire",
        "export_best_to": "ml/weights/best.pt",
    }
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        default_cfg.update(user_cfg)
    return default_cfg


def run_training(cfg: Dict[str, Any]) -> int:
    """Menjalankan pipeline training YOLO dan menyimpan model terbaik ke `ml/weights/best.pt`."""
    data_yaml_path = Path(cfg["data_yaml"]).resolve()
    if not data_yaml_path.exists():
        print(f"[ERROR] File konfigurasi dataset '{data_yaml_path}' tidak ditemukan.")
        return 1

    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data_cfg = yaml.safe_load(f) or {}

    dataset_root = Path(data_cfg.get("path", "ml/dataset/DFireDataset"))
    if not dataset_root.is_absolute():
        dataset_root = (data_yaml_path.parent / dataset_root).resolve()

    ds_status = check_dataset(dataset_root)
    if not ds_status.get("dataset_ready"):
        print(f"[ERROR] Dataset belum siap: {ds_status.get('message')}")
        print("[INFO] Pastikan D-Fire Dataset telah diekstrak sebelum menjalankan training.")
        return 1

    try:
        from ultralytics import YOLO
    except ImportError:
        print(
            "[ERROR] Pustaka 'ultralytics' belum terinstal. "
            "Jalankan: pip install -r requirements.txt"
        )
        return 1

    device = resolve_compute_device(str(cfg.get("device", "auto")))
    base_model = str(cfg.get("base_model", "yolov8n.pt"))

    print("=" * 72)
    print("  APIWASPADA - MULAI TRAINING MODEL YOLO (D-FIRE DATASET)")
    print(f"  Model Dasar     : {base_model}")
    print(f"  Konfigurasi Data: {data_yaml_path}")
    print(f"  Image Size      : {cfg['imgsz']} | Batch: {cfg['batch']} | Epochs: {cfg['epochs']}")
    print(f"  Optimizer       : {cfg['optimizer']} | LR0: {cfg['lr0']} | Patience: {cfg['patience']}")
    print(f"  Device          : {device} | Seed: {cfg['seed']}")
    print("=" * 72)

    model = YOLO(base_model)
    model.train(
        data=str(data_yaml_path),
        imgsz=int(cfg["imgsz"]),
        batch=int(cfg["batch"]),
        epochs=int(cfg["epochs"]),
        lr0=float(cfg["lr0"]),
        lrf=float(cfg.get("lrf", 0.01)),
        optimizer=str(cfg["optimizer"]),
        patience=int(cfg["patience"]),
        device=device,
        workers=int(cfg.get("workers", 2)),
        seed=int(cfg["seed"]),
        project=str(cfg["project_dir"]),
        name=str(cfg["experiment_name"]),
        exist_ok=True,
    )

    # Cari lokasi best.pt dari hasil training
    run_dir = Path(cfg["project_dir"]) / str(cfg["experiment_name"])
    trained_best = run_dir / "weights" / "best.pt"
    target_best = Path(cfg.get("export_best_to", "ml/weights/best.pt")).resolve()

    if trained_best.exists():
        target_best.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(trained_best), str(target_best))
        print(f"[SUCCESS] Model terbaik berhasil disalin ke: {target_best}")
        return 0

    print(f"[WARN] Pelatihan selesai, namun file '{trained_best}' tidak ditemukan.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Script Training YOLO ApiWaspada")
    parser.add_argument(
        "--config",
        type=str,
        default="ml/configs/train_lightweight.yaml",
        help="Path file konfigurasi YAML training (default: train_lightweight.yaml)",
    )
    parser.add_argument("--data", type=str, default=None, help="Override path data.yaml")
    parser.add_argument("--model", type=str, default=None, help="Override base model (mis. yolov8n.pt)")
    parser.add_argument("--epochs", type=int, default=None, help="Override jumlah epoch")
    parser.add_argument("--batch", type=int, default=None, help="Override ukuran batch")
    parser.add_argument("--imgsz", type=int, default=None, help="Override ukuran gambar")
    parser.add_argument("--device", type=str, default=None, help="Override device (cpu / 0 / auto)")
    args = parser.parse_args()

    cfg = load_training_config(Path(args.config))
    if args.data:
        cfg["data_yaml"] = args.data
    if args.model:
        cfg["base_model"] = args.model
    if args.epochs is not None:
        cfg["epochs"] = args.epochs
    if args.batch is not None:
        cfg["batch"] = args.batch
    if args.imgsz is not None:
        cfg["imgsz"] = args.imgsz
    if args.device:
        cfg["device"] = args.device

    return run_training(cfg)


if __name__ == "__main__":
    sys.exit(main())
