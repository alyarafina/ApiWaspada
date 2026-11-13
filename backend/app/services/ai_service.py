"""
Layanan Inferensi AI YOLO (Api & Asap) untuk ApiWaspada.
Mendukung:
1. Pemuatan model Ultralytics YOLO dari `ml/weights/best.pt` secara otomatis pada GPU (CUDA) atau CPU.
2. Pemetaan nama kelas dinamis dari metadata model (`model.names`) maupun `ml/data.yaml`
   tanpa mengasumsikan secara kaku ID kelas, serta menormalisasi label menjadi `Fire` dan `Smoke`.
3. Visualisasi bounding box, nama kelas, dan confidence score menggunakan OpenCV / Pillow.
4. Mode Graceful Fallback yang transparan apabila file `ml/weights/best.pt` belum tersedia,
   tanpa membuat model palsu.
"""
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
import yaml

from backend.app.config import settings
from backend.app.schemas.detection import (
    AI_DISCLAIMER_TEXT,
    BoundingBoxItem,
    DetectionResponse,
    DetectionStatusResponse,
    ModelOption,
)

# Status resmi sesuai spesifikasi Bagian 4
STATUS_FIRE_ONLY = "Terdeteksi indikasi api"
STATUS_SMOKE_ONLY = "Terdeteksi indikasi asap"
STATUS_FIRE_AND_SMOKE = "Api dan asap terindikasi"
STATUS_NO_DETECTION = "Tidak ditemukan indikasi api atau asap"
STATUS_MODEL_UNAVAILABLE = "Deteksi gagal atau model belum tersedia"


def determine_detection_status(
    ai_available: bool, fire_detected: bool, smoke_detected: bool
) -> str:
    """Menentukan string status indikasi deteksi berdasarkan hasil inferensi."""
    if not ai_available:
        return STATUS_MODEL_UNAVAILABLE
    if fire_detected and smoke_detected:
        return STATUS_FIRE_AND_SMOKE
    if fire_detected:
        return STATUS_FIRE_ONLY
    if smoke_detected:
        return STATUS_SMOKE_ONLY
    return STATUS_NO_DETECTION


def normalize_class_label(raw_name: str) -> str:
    """Menormalisasi nama kelas dari model/dataset menjadi 'Fire' atau 'Smoke'."""
    cleaned = str(raw_name).strip().lower()
    if cleaned in ("fire", "api", "flame", "kebakaran"):
        return "Fire"
    if cleaned in ("smoke", "asap", "fume"):
        return "Smoke"
    return raw_name.strip().capitalize()


class UnknownModelError(ValueError):
    """Dilempar bila kunci model yang diminta tidak terdaftar."""


@dataclass(frozen=True)
class ModelSpec:
    """Definisi satu model YOLO yang dapat dipilih pengguna."""

    key: str
    label: str
    description: str
    path: Path


def build_model_registry() -> Dict[str, ModelSpec]:
    """
    Daftar model yang dapat dipilih. Tiga model `fire_*` adalah YOLOv8 hasil latih
    D-Fire Dataset (sumber: repositori wildfire-detection, lisensi MIT);
    `best` adalah model hasil pelatihan sendiri (`YOLO_MODEL_PATH`).
    """
    weights_dir = settings.BASE_DIR / "ml" / "weights"
    specs = [
        ModelSpec("fire_n", "YOLOv8 Nano", "Paling cepat & ringan (mAP@50 0.787)", weights_dir / "fire_n.pt"),
        ModelSpec("fire_m", "YOLOv8 Medium", "Seimbang, disarankan (mAP@50 0.801)", weights_dir / "fire_m.pt"),
        ModelSpec("fire_l", "YOLOv8 Large", "Paling akurat, paling berat (mAP@50 0.812)", weights_dir / "fire_l.pt"),
        ModelSpec("best", "Model kustom", "Hasil pelatihan sendiri (best.pt)", settings.YOLO_MODEL_PATH),
    ]
    return {s.key: s for s in specs}


class AIDetectionService:
    """Service singleton untuk mengelola beberapa model YOLO dan inferensi gambar."""

    def __init__(self) -> None:
        self.registry: Dict[str, ModelSpec] = build_model_registry()
        self.conf_threshold: float = settings.YOLO_CONFIDENCE_THRESHOLD
        self.iou_threshold: float = settings.YOLO_IOU_THRESHOLD
        self.imgsz: int = settings.YOLO_IMAGE_SIZE
        self._models: Dict[str, Any] = {}
        self._mappings: Dict[str, Dict[int, str]] = {}
        self._load_errors: Dict[str, str] = {}
        self._load_lock = threading.Lock()
        self._default_override: Optional[str] = None
        self._custom_predictor: Optional[Callable[[np.ndarray, float], List[Dict[str, Any]]]] = None
        self._device: str = self._resolve_device(settings.YOLO_DEVICE)
        self._class_mapping: Dict[int, str] = self._load_class_mapping_from_yaml()

    # ------------------------------------------------------------------
    # Pemilihan model
    # ------------------------------------------------------------------
    @property
    def default_model_key(self) -> str:
        """Model default dari `YOLO_DEFAULT_MODEL`; jika filenya tidak ada, model pertama yang tersedia."""
        if self._default_override:
            return self._default_override
        preferred = settings.YOLO_DEFAULT_MODEL
        if preferred in self.registry and self.model_file_exists(preferred):
            return preferred
        for key in self.registry:
            if self.model_file_exists(key):
                return key
        return preferred if preferred in self.registry else "fire_m"

    def resolve_model_key(self, model_key: Optional[str]) -> str:
        """Memvalidasi kunci model dari pengguna; None/kosong berarti model default."""
        key = (model_key or "").strip().lower()
        if not key:
            return self.default_model_key
        if key not in self.registry:
            raise UnknownModelError(
                f"Model '{model_key}' tidak dikenal. Pilihan: {', '.join(self.registry)}."
            )
        return key

    @property
    def model_path(self) -> Path:
        """Lokasi file model default (kompatibel dengan kode lama)."""
        return self.registry[self.default_model_key].path

    @model_path.setter
    def model_path(self, path: Path) -> None:
        """Memakai file bobot tertentu sebagai model default (dipakai `ml/predict.py`)."""
        path = Path(path).resolve()
        self.registry["custom"] = ModelSpec("custom", "Model pilihan", "File bobot dari argumen", path)
        self._models.pop("custom", None)
        self._mappings.pop("custom", None)
        self._default_override = "custom"

    def _resolve_device(self, configured_device: str) -> str:
        """Menentukan perangkat komputasi (GPU NVIDIA CUDA jika tersedia, atau CPU)."""
        try:
            import torch

            if configured_device.lower() in ("auto", ""):
                return "cuda:0" if torch.cuda.is_available() else "cpu"
            if "cuda" in configured_device.lower() and not torch.cuda.is_available():
                return "cpu"
            return configured_device
        except ImportError:
            return "cpu"

    def _load_class_mapping_from_yaml(self) -> Dict[int, str]:
        """Membaca pemetaan kelas dari `ml/data.yaml` jika ada, atau dari settings."""
        data_yaml_path = settings.BASE_DIR / "ml" / "data.yaml"
        mapping: Dict[int, str] = {}
        if data_yaml_path.exists():
            try:
                with open(data_yaml_path, "r", encoding="utf-8") as f:
                    data_cfg = yaml.safe_load(f) or {}
                names = data_cfg.get("names")
                if isinstance(names, dict):
                    for k, v in names.items():
                        mapping[int(k)] = normalize_class_label(str(v))
                elif isinstance(names, list):
                    for idx, v in enumerate(names):
                        mapping[idx] = normalize_class_label(str(v))
            except Exception:
                pass
        if not mapping:
            for k, v in settings.YOLO_CLASS_MAP.items():
                mapping[int(k)] = normalize_class_label(v)
        return mapping

    def _rel_path(self, path: Path) -> str:
        try:
            return path.relative_to(settings.BASE_DIR).as_posix()
        except ValueError:
            return str(path)

    def model_file_exists(self, model_key: Optional[str] = None) -> bool:
        """
        Memeriksa apakah file bobot model (default bila `model_key` kosong)
        benar-benar ada dan bukan file kosong (> 1 KB).
        """
        path = self.registry[model_key].path if model_key else self.model_path
        return path.exists() and path.is_file() and path.stat().st_size > 1024

    def ensure_model_loaded(self, model_key: Optional[str] = None) -> bool:
        """Memuat model YOLO ke memori (sekali saja per model) jika filenya tersedia."""
        if self._custom_predictor is not None:
            return True
        key = self.resolve_model_key(model_key)
        if key in self._models:
            return True
        spec = self.registry[key]
        if not self.model_file_exists(key):
            self._load_errors[key] = (
                f"File model bobot YOLO belum tersedia di '{self._rel_path(spec.path)}'. "
                "Sistem berjalan dalam Mode AI Belum Aktif."
            )
            return False

        with self._load_lock:
            if key in self._models:
                return True
            try:
                from ultralytics import YOLO

                model = YOLO(str(spec.path))
                # Ambil pemetaan kelas asli dari metadata internal model YOLO.
                # Urutan kelas tiap model bisa berbeda (mis. 0:smoke,1:fire vs 0:fire,1:smoke).
                mapping = dict(self._class_mapping)
                model_names = getattr(model, "names", None)
                if isinstance(model_names, dict) and model_names:
                    mapping = {int(k): normalize_class_label(str(v)) for k, v in model_names.items()}
                elif isinstance(model_names, list) and model_names:
                    mapping = {idx: normalize_class_label(str(v)) for idx, v in enumerate(model_names)}
                self._mappings[key] = mapping
                self._models[key] = model
                self._load_errors.pop(key, None)
                return True
            except Exception as exc:
                self._load_errors[key] = f"Gagal memuat model YOLO '{key}': {str(exc)}"
                return False

    def set_custom_predictor(
        self,
        predictor_fn: Optional[Callable[[np.ndarray, float], List[Dict[str, Any]]]],
        class_mapping: Optional[Dict[int, str]] = None,
    ) -> None:
        """
        Mengatur predictor khusus (digunakan untuk pengujian terisolasi / unit testing AI
        tanpa memalsukan file `best.pt` di disk).
        """
        self._custom_predictor = predictor_fn
        if class_mapping:
            self._class_mapping = {
                int(k): normalize_class_label(v) for k, v in class_mapping.items()
            }

    def get_status(self) -> DetectionStatusResponse:
        """Mengembalikan status kesiapan modul AI YOLO untuk endpoint `/api/detect/status`."""
        default_key = self.default_model_key
        is_ready = self.ensure_model_loaded(default_key)
        default_spec = self.registry[default_key]
        class_mapping = self._mappings.get(default_key, self._class_mapping)

        if is_ready:
            status_label = "AI Aktif (Siap Inferensi)"
            msg = (
                f"Model default {default_spec.label} ({default_key}) dimuat pada perangkat "
                f"'{self._device}' dengan pemetaan kelas {class_mapping}."
            )
        else:
            status_label = "Mode AI Belum Aktif (Menunggu Model best.pt)"
            msg = (
                self._load_errors.get(default_key)
                or "Model YOLO belum tersedia. Laporan masyarakat tetap dapat dikirim dan diverifikasi manual oleh petugas."
            )

        options = [
            ModelOption(
                key=spec.key,
                label=spec.label,
                description=spec.description,
                file=self._rel_path(spec.path),
                available=self.model_file_exists(spec.key),
                is_default=spec.key == default_key,
            )
            for spec in self.registry.values()
        ]

        return DetectionStatusResponse(
            ai_available=is_ready,
            model_loaded=(default_key in self._models) or (self._custom_predictor is not None),
            model_path=self._rel_path(default_spec.path),
            model_exists_on_disk=self.model_file_exists(default_key),
            device=self._device,
            confidence_threshold=self.conf_threshold,
            iou_threshold=self.iou_threshold,
            class_mapping=class_mapping,
            status_label=status_label,
            message=msg,
            default_model=default_key,
            available_models=options,
            disclaimer=AI_DISCLAIMER_TEXT,
        )

    def _draw_annotations(
        self,
        image_bgr: np.ndarray,
        detections: List[BoundingBoxItem],
        ai_available: bool,
        detection_status: str,
    ) -> Tuple[Path, str]:
        """
        Menggambar bounding box, label kelas, confidence score, dan header status
        pada salinan citra menggunakan OpenCV, lalu menyimpannya ke `storage/results/`.
        """
        canvas = image_bgr.copy()
        h, w = canvas.shape[:2]
        scale = max(0.5, min(w, h) / 700.0)
        thickness = max(2, int(2.5 * scale))
        font = cv2.FONT_HERSHEY_SIMPLEX

        for det in detections:
            x1, y1, x2, y2 = [int(round(v)) for v in det.bbox_xyxy]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            # Warna BGR: Merah untuk Fire, Oranye untuk Smoke
            if det.class_name.lower() == "fire":
                color = (38, 38, 220)  # BGR untuk #DC2626
            else:
                color = (22, 115, 249)  # BGR untuk #F97316

            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

            label_text = f"{det.class_name.upper()} {det.confidence * 100:.1f}%"
            (tw, th), baseline = cv2.getTextSize(label_text, font, 0.58 * scale, max(1, thickness - 1))
            label_y1 = max(0, y1 - th - baseline - 8)
            label_y2 = y1 if y1 - th - baseline - 8 >= 0 else min(h, y1 + th + baseline + 8)
            cv2.rectangle(
                canvas,
                (x1, label_y1),
                (min(w - 1, x1 + tw + 12), label_y2),
                color,
                -1,
            )
            text_y = label_y2 - baseline - 4 if label_y1 < y1 else label_y2 - 4
            cv2.putText(
                canvas,
                label_text,
                (x1 + 6, text_y),
                font,
                0.58 * scale,
                (255, 255, 255),
                max(1, thickness - 1),
                cv2.LINE_AA,
            )

        # Tambahkan pita informasi status di bagian bawah gambar
        banner_h = max(32, int(38 * scale))
        overlay = canvas.copy()
        banner_color = (30, 41, 59) if ai_available else (30, 64, 120)
        cv2.rectangle(overlay, (0, h - banner_h), (w, h), banner_color, -1)
        cv2.addWeighted(overlay, 0.82, canvas, 0.18, 0, canvas)

        footer_text = f"ApiWaspada AI: {detection_status}"
        cv2.putText(
            canvas,
            footer_text,
            (12, h - int(banner_h * 0.32)),
            font,
            0.52 * scale,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:10]
        result_filename = f"res_{timestamp}_{unique_id}.jpg"
        result_path = (settings.RESULT_DIR / result_filename).resolve()
        cv2.imwrite(str(result_path), canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        result_url = f"/storage/results/{result_filename}"
        return result_path, result_url

    def run_detection(
        self,
        image_path: Path,
        original_image_url: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        model_key: Optional[str] = None,
    ) -> DetectionResponse:
        """
        Menjalankan deteksi YOLO pada satu file gambar yang berada di `image_path`
        menggunakan model `model_key` (default bila kosong).
        Jika model belum tersedia, mengembalikan status fallback yang jelas tanpa error 500.
        """
        start_time = time.perf_counter()
        threshold = conf_threshold if conf_threshold is not None else self.conf_threshold
        key = self.resolve_model_key(model_key)
        spec = self.registry[key]

        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            raise ValueError(f"Tidak dapat membaca citra dari path: {image_path}")

        img_h, img_w = image_bgr.shape[:2]
        is_ready = self.ensure_model_loaded(key)
        model = self._models.get(key)
        class_mapping = self._mappings.get(key, self._class_mapping)

        detections: List[BoundingBoxItem] = []
        fire_detected = False
        smoke_detected = False
        highest_conf = 0.0
        model_info = f"{spec.label}: model belum tersedia (Mode Fallback)"

        if is_ready:
            if self._custom_predictor is not None:
                raw_preds = self._custom_predictor(image_bgr, threshold)
                model_info = f"Custom/Test YOLO Predictor ({self._device})"
                for item in raw_preds:
                    cid = int(item["class_id"])
                    cname = normalize_class_label(
                        item.get("class_name") or class_mapping.get(cid, f"Class_{cid}")
                    )
                    conf = float(item["confidence"])
                    if conf < threshold:
                        continue
                    x1, y1, x2, y2 = [float(v) for v in item["bbox_xyxy"]]
                    bw = max(1.0, x2 - x1)
                    bh = max(1.0, y2 - y1)
                    xc = (x1 + x2) / 2.0 / img_w
                    yc = (y1 + y2) / 2.0 / img_h
                    wn = bw / img_w
                    hn = bh / img_h
                    detections.append(
                        BoundingBoxItem(
                            class_id=cid,
                            class_name=cname,
                            confidence=round(conf, 4),
                            bbox_xyxy=[round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                            bbox_xywhn=[round(xc, 4), round(yc, 4), round(wn, 4), round(hn, 4)],
                        )
                    )
            elif model is not None:
                try:
                    results = model.predict(
                        source=str(image_path),
                        conf=threshold,
                        iou=self.iou_threshold,
                        imgsz=self.imgsz,
                        device=self._device,
                        verbose=False,
                    )
                    model_info = f"{spec.label} ({spec.path.name} @ {self._device})"
                    if results and len(results) > 0:
                        res = results[0]
                        boxes = getattr(res, "boxes", None)
                        if boxes is not None and len(boxes) > 0:
                            xyxy_arr = boxes.xyxy.cpu().numpy()
                            xywhn_arr = boxes.xywhn.cpu().numpy()
                            conf_arr = boxes.conf.cpu().numpy()
                            cls_arr = boxes.cls.cpu().numpy()
                            for i in range(len(xyxy_arr)):
                                cid = int(cls_arr[i])
                                conf = float(conf_arr[i])
                                cname = class_mapping.get(cid, f"Class_{cid}")
                                cname = normalize_class_label(cname)
                                x1, y1, x2, y2 = [float(v) for v in xyxy_arr[i]]
                                xc, yc, wn, hn = [float(v) for v in xywhn_arr[i]]
                                detections.append(
                                    BoundingBoxItem(
                                        class_id=cid,
                                        class_name=cname,
                                        confidence=round(conf, 4),
                                        bbox_xyxy=[round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                                        bbox_xywhn=[round(xc, 4), round(yc, 4), round(wn, 4), round(hn, 4)],
                                    )
                                )
                except Exception as exc:
                    is_ready = False
                    model_info = f"Inferensi gagal: {str(exc)}"

        # Urutkan deteksi dari confidence tertinggi
        detections.sort(key=lambda d: d.confidence, reverse=True)
        for d in detections:
            if d.confidence > highest_conf:
                highest_conf = d.confidence
            if d.class_name.lower() == "fire":
                fire_detected = True
            elif d.class_name.lower() == "smoke":
                smoke_detected = True

        detection_status = determine_detection_status(
            ai_available=is_ready,
            fire_detected=fire_detected,
            smoke_detected=smoke_detected,
        )

        _, result_image_url = self._draw_annotations(
            image_bgr=image_bgr,
            detections=detections,
            ai_available=is_ready,
            detection_status=detection_status,
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return DetectionResponse(
            success=True,
            ai_available=is_ready,
            detection_status=detection_status,
            highest_confidence=round(highest_conf, 4),
            fire_detected=fire_detected,
            smoke_detected=smoke_detected,
            total_objects=len(detections),
            detections=detections,
            original_image_url=original_image_url,
            result_image_url=result_image_url,
            inference_time_ms=elapsed_ms,
            image_dimensions=[img_w, img_h],
            model_info=model_info,
            model_key=key,
            disclaimer=AI_DISCLAIMER_TEXT,
        )


ai_service = AIDetectionService()
