"""
Script Pemeriksaan & Validasi Struktur Dataset D-Fire (`ml/check_dataset.py`).

Sumber Dataset Resmi:
- GitHub Repository : https://github.com/gaia-solutions-on-demand/DFireDataset
- Dokumentasi Web   : https://gaia-solutions-on-demand.github.io/DFireDataset/

Fungsi Script:
1. Memeriksa ketersediaan folder dataset (`train`, `val`, `test`, `images`, `labels`).
2. Memeriksa format anotasi pada file `.txt` apakah mengikuti standar YOLO
   (`<class_id> <x_center> <y_center> <width> <height>` ternormalisasi `0.0 - 1.0`)
   atau format piksel/Pascal VOC, dan menyediakan fungsi konversi jika diperlukan.
3. Menghitung statistik nyata dari file yang ada di disk:
   - Total gambar per split (`train`, `val`, `test`)
   - Kategori gambar: `Only fire`, `Only smoke`, `Fire and smoke`, `None` (negatif/kosong)
   - Jumlah bounding box per ID kelas
4. Memeriksa file metadata kelas (`classes.txt`, `obj.names`, atau `data.yaml`) jika tersedia
   agar tidak mengasumsikan pemetaan kelas secara buta.
5. Menyediakan opsi `--create-val-split` (mis. 10% dari train) apabila rilis D-Fire yang
   diunduh hanya memiliki folder `train/` dan `test/`, serta memperbarui `ml/data.yaml`.
"""
import argparse
import json
import random
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def detect_class_mapping(dataset_dir: Path) -> Dict[int, str]:
    """
    Mencari definisi nama kelas dari `classes.txt`, `obj.names`, atau `data.yaml`
    di dalam folder dataset. Jika tidak ditemukan file metadata eksternal,
    menggunakan standar dokumentasi D-Fire Dataset (`0: smoke, 1: fire`) sambil
    memberikan catatan verifikasi.
    """
    for candidate_name in ("classes.txt", "obj.names", "class_names.txt"):
        candidate_file = dataset_dir / candidate_name
        if candidate_file.exists():
            lines = [
                line.strip()
                for line in candidate_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if lines:
                return {idx: name for idx, name in enumerate(lines)}

    for yaml_name in ("data.yaml", "dataset.yaml", "dfire.yaml"):
        yaml_file = dataset_dir / yaml_name
        if yaml_file.exists():
            try:
                cfg = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
                names = cfg.get("names")
                if isinstance(names, dict):
                    return {int(k): str(v) for k, v in names.items()}
                if isinstance(names, list):
                    return {idx: str(v) for idx, v in enumerate(names)}
            except Exception:
                pass

    # Default resmi D-Fire Dataset (Venâncio et al., GAIA)
    return {0: "smoke", 1: "fire"}


def inspect_label_file(label_path: Path) -> Tuple[List[int], int, List[str]]:
    """
    Memeriksa satu file anotasi `.txt` YOLO.
    Mengembalikan: `(list_of_class_ids, invalid_lines_count, format_warnings)`
    """
    class_ids: List[int] = []
    invalid_count = 0
    warnings: List[str] = []

    if not label_path.exists():
        return class_ids, 0, ["missing_label_file"]

    try:
        raw_text = label_path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception as exc:
        return class_ids, 1, [f"read_error: {exc}"]

    if not raw_text:
        # Gambar negatif (None / tanpa api maupun asap) pada D-Fire memiliki file .txt kosong
        return class_ids, 0, []

    for line_num, line in enumerate(raw_text.splitlines(), start=1):
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) != 5:
            invalid_count += 1
            warnings.append(f"{label_path.name}:L{line_num} bukan 5 kolom ({len(parts)} kolom)")
            continue
        try:
            cid = int(float(parts[0]))
            coords = [float(x) for x in parts[1:]]
        except ValueError:
            invalid_count += 1
            warnings.append(f"{label_path.name}:L{line_num} nilai non-numerik")
            continue

        # Periksa apakah koordinat sudah ternormalisasi [0.0, 1.0]
        if any(c < -0.001 or c > 1.001 for c in coords):
            invalid_count += 1
            warnings.append(
                f"{label_path.name}:L{line_num} koordinat di luar [0,1] ({coords}) - kemungkinan format piksel"
            )
        class_ids.append(cid)

    return class_ids, invalid_count, warnings


def convert_pixel_bbox_to_yolo(
    x_min: float, y_min: float, x_max: float, y_max: float, img_w: int, img_h: int
) -> Tuple[float, float, float, float]:
    """
    Mengonversi koordinat piksel `[x_min, y_min, x_max, y_max]` menjadi
    format YOLO ternormalisasi `[x_center, y_center, width, height]`.
    """
    bw = max(0.0, x_max - x_min)
    bh = max(0.0, y_max - y_min)
    xc = (x_min + bw / 2.0) / float(img_w)
    yc = (y_min + bh / 2.0) / float(img_h)
    wn = bw / float(img_w)
    hn = bh / float(img_h)
    return (
        min(1.0, max(0.0, xc)),
        min(1.0, max(0.0, yc)),
        min(1.0, max(0.0, wn)),
        min(1.0, max(0.0, hn)),
    )


def analyze_split(
    split_dir: Path, class_map: Dict[int, str]
) -> Dict[str, Any]:
    """Menganalisis satu split (`train`, `val`, atau `test`)."""
    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"

    if not images_dir.exists() or not labels_dir.exists():
        return {
            "exists": False,
            "path": str(split_dir),
            "images_dir_exists": images_dir.exists(),
            "labels_dir_exists": labels_dir.exists(),
            "total_images": 0,
            "total_labels": 0,
        }

    image_files = sorted(
        [p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    )
    label_files = sorted(
        [p for p in labels_dir.iterdir() if p.is_file() and p.suffix.lower() == ".txt"]
    )

    bbox_counter: Counter = Counter()
    category_counter: Counter = Counter(
        {"only_fire": 0, "only_smoke": 0, "fire_and_smoke": 0, "none": 0}
    )
    missing_labels = 0
    invalid_lines = 0
    sample_warnings: List[str] = []

    # Tentukan ID mana yang merepresentasikan fire vs smoke berdasarkan class_map
    fire_ids: Set[int] = {
        k for k, v in class_map.items() if "fire" in v.lower() or "api" in v.lower()
    }
    smoke_ids: Set[int] = {
        k for k, v in class_map.items() if "smoke" in v.lower() or "asap" in v.lower()
    }

    for img_path in image_files:
        lbl_path = labels_dir / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            missing_labels += 1
            category_counter["none"] += 1
            continue

        cids, inv_cnt, warns = inspect_label_file(lbl_path)
        invalid_lines += inv_cnt
        if warns and len(sample_warnings) < 10:
            sample_warnings.extend(warns[: 10 - len(sample_warnings)])

        for cid in cids:
            bbox_counter[cid] += 1

        unique_cids = set(cids)
        has_fire = bool(unique_cids & fire_ids)
        has_smoke = bool(unique_cids & smoke_ids)

        if has_fire and has_smoke:
            category_counter["fire_and_smoke"] += 1
        elif has_fire:
            category_counter["only_fire"] += 1
        elif has_smoke:
            category_counter["only_smoke"] += 1
        else:
            category_counter["none"] += 1

    bbox_by_name = {
        f"{cid} ({class_map.get(cid, f'unknown_{cid}')})": count
        for cid, count in sorted(bbox_counter.items())
    }

    return {
        "exists": True,
        "path": str(split_dir),
        "total_images": len(image_files),
        "total_labels": len(label_files),
        "missing_labels": missing_labels,
        "invalid_annotation_lines": invalid_lines,
        "image_categories": dict(category_counter),
        "bounding_boxes_by_class_id": dict(bbox_counter),
        "bounding_boxes_by_class_name": bbox_by_name,
        "total_bounding_boxes": sum(bbox_counter.values()),
        "sample_warnings": sample_warnings,
    }


def create_validation_split_from_train(
    dataset_dir: Path, val_ratio: float = 0.10, seed: int = 42
) -> Dict[str, Any]:
    """
    Jika dataset unduhan D-Fire hanya memiliki folder `train/` dan `test/`
    (tanpa `val/`), fungsi ini memindahkan sebagian proporsional (default 10%)
    dari `train/` ke `val/` secara deterministik agar proses validasi tidak
    menyentuh `test/` set.
    """
    train_img_dir = dataset_dir / "train" / "images"
    train_lbl_dir = dataset_dir / "train" / "labels"
    val_img_dir = dataset_dir / "val" / "images"
    val_lbl_dir = dataset_dir / "val" / "labels"

    if not train_img_dir.exists():
        return {"created": False, "reason": "Folder train/images tidak ditemukan."}

    existing_val_imgs = (
        list(val_img_dir.glob("*")) if val_img_dir.exists() else []
    )
    if existing_val_imgs:
        return {
            "created": False,
            "reason": f"Folder val/images sudah berisi {len(existing_val_imgs)} file.",
        }

    val_img_dir.mkdir(parents=True, exist_ok=True)
    val_lbl_dir.mkdir(parents=True, exist_ok=True)

    all_train_images = sorted(
        [p for p in train_img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    )
    rng = random.Random(seed)
    rng.shuffle(all_train_images)
    val_count = max(1, int(len(all_train_images) * val_ratio))
    selected_for_val = all_train_images[:val_count]

    moved = 0
    for img_path in selected_for_val:
        lbl_path = train_lbl_dir / f"{img_path.stem}.txt"
        shutil.move(str(img_path), str(val_img_dir / img_path.name))
        if lbl_path.exists():
            shutil.move(str(lbl_path), str(val_lbl_dir / lbl_path.name))
        moved += 1

    return {
        "created": True,
        "moved_images_count": moved,
        "val_images_dir": str(val_img_dir),
    }


def check_dataset(
    dataset_dir: Path,
    output_yaml_path: Optional[Path] = None,
    auto_create_val: bool = False,
    val_ratio: float = 0.10,
) -> Dict[str, Any]:
    """Menjalankan pemeriksaan menyeluruh pada folder dataset D-Fire."""
    dataset_dir = dataset_dir.resolve()
    if not dataset_dir.exists():
        return {
            "dataset_ready": False,
            "dataset_dir": str(dataset_dir),
            "message": (
                f"Direktori dataset belum ditemukan di '{dataset_dir}'. "
                "Silakan unduh D-Fire Dataset dari https://github.com/gaia-solutions-on-demand/DFireDataset "
                "dan ekstrak ke lokasi tersebut."
            ),
        }

    if auto_create_val:
        create_validation_split_from_train(dataset_dir, val_ratio=val_ratio)

    class_map = detect_class_mapping(dataset_dir)
    splits_report: Dict[str, Any] = {}
    for split_name in ("train", "val", "test"):
        splits_report[split_name] = analyze_split(dataset_dir / split_name, class_map)

    has_train = splits_report["train"]["exists"] and splits_report["train"]["total_images"] > 0
    has_val = splits_report["val"]["exists"] and splits_report["val"]["total_images"] > 0
    has_test = splits_report["test"]["exists"] and splits_report["test"]["total_images"] > 0

    dataset_ready = has_train and (has_val or has_test)

    if output_yaml_path and dataset_ready:
        val_rel = "val/images" if has_val else "test/images"
        yaml_data: Dict[str, Any] = {
            "path": dataset_dir.as_posix(),
            "train": "train/images",
            "val": val_rel,
            "nc": len(class_map),
            "names": class_map,
        }
        if has_test:
            yaml_data["test"] = "test/images"
        output_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False, allow_unicode=True)

    return {
        "dataset_ready": dataset_ready,
        "dataset_dir": str(dataset_dir),
        "class_mapping": class_map,
        "num_classes": len(class_map),
        "splits": splits_report,
        "message": (
            "Dataset D-Fire terverifikasi dan siap digunakan untuk training YOLO."
            if dataset_ready
            else "Struktur folder dataset belum lengkap (pastikan minimal train/images dan train/labels tersedia)."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pemeriksaan Struktur dan Anotasi D-Fire Dataset untuk ApiWaspada"
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="ml/dataset/DFireDataset",
        help="Path menuju direktori root D-Fire Dataset",
    )
    parser.add_argument(
        "--update-yaml",
        type=str,
        default="ml/data.yaml",
        help="Path file data.yaml yang akan diperbarui jika dataset valid",
    )
    parser.add_argument(
        "--create-val-split",
        action="store_true",
        help="Buat folder val/ otomatis (10%% dari train/) jika val/ belum tersedia",
    )
    args = parser.parse_args()

    report = check_dataset(
        dataset_dir=Path(args.dataset_dir),
        output_yaml_path=Path(args.update_yaml) if args.update_yaml else None,
        auto_create_val=args.create_val_split,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("dataset_ready") else 1


if __name__ == "__main__":
    sys.exit(main())
