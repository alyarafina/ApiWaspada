"""
Schema Pydantic untuk layanan Deteksi Visual AI YOLO (Api & Asap).
"""
from typing import List, Optional
from pydantic import BaseModel, Field

AI_DISCLAIMER_TEXT = (
    "Hasil deteksi AI merupakan indikasi awal berdasarkan gambar yang diunggah dan "
    "bukan konfirmasi resmi kejadian kebakaran. Setiap laporan tetap memerlukan verifikasi petugas."
)


class BoundingBoxItem(BaseModel):
    """Informasi satu bounding box objek yang terdeteksi."""

    class_id: int = Field(..., description="ID kelas dari model YOLO")
    class_name: str = Field(..., description="Nama kelas terstandar: Fire atau Smoke")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Skor keyakinan (0.0 - 1.0)")
    bbox_xyxy: List[float] = Field(
        ..., description="Koordinat piksel [x1, y1, x2, y2]"
    )
    bbox_xywhn: List[float] = Field(
        ..., description="Koordinat ternormalisasi YOLO [x_center, y_center, width, height]"
    )


class DetectionStatusResponse(BaseModel):
    """Response untuk memeriksa status ketersediaan model YOLO (`GET /api/detect/status`)."""

    ai_available: bool = Field(..., description="Apakah model YOLO siap melakukan inferensi")
    model_loaded: bool = Field(..., description="Apakah weights model berhasil dimuat di memori")
    model_path: str = Field(..., description="Lokasi relatif file model bobot YOLO")
    model_exists_on_disk: bool = Field(..., description="Apakah file best.pt ditemukan di disk")
    device: str = Field(..., description="Perangkat komputasi (cpu / cuda)")
    confidence_threshold: float = Field(..., description="Ambang batas confidence deteksi")
    iou_threshold: float = Field(..., description="Ambang batas IoU NMS")
    class_mapping: dict = Field(..., description="Pemetaan ID kelas ke nama kelas")
    status_label: str = Field(..., description="Status operasional layanan AI")
    message: str = Field(..., description="Penjelasan status layanan AI")
    disclaimer: str = Field(default=AI_DISCLAIMER_TEXT)


class DetectionResponse(BaseModel):
    """Response hasil deteksi gambar oleh endpoint `POST /api/detect`."""

    success: bool = Field(..., description="Apakah proses pemanggilan endpoint berhasil")
    ai_available: bool = Field(..., description="Apakah model YOLO aktif saat pemrosesan")
    detection_status: str = Field(
        ...,
        description=(
            "Status indikasi deteksi: 'Terdeteksi indikasi api', 'Terdeteksi indikasi asap', "
            "'Api dan asap terindikasi', 'Tidak ditemukan indikasi api atau asap', atau "
            "'Deteksi gagal atau model belum tersedia'"
        ),
    )
    highest_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence tertinggi")
    fire_detected: bool = Field(..., description="Apakah ditemukan kelas Fire")
    smoke_detected: bool = Field(..., description="Apakah ditemukan kelas Smoke")
    total_objects: int = Field(..., ge=0, description="Jumlah bounding box yang terdeteksi")
    detections: List[BoundingBoxItem] = Field(default_factory=list)
    original_image_url: Optional[str] = Field(None, description="URL gambar asli")
    result_image_url: Optional[str] = Field(None, description="URL gambar hasil visualisasi bounding box")
    inference_time_ms: float = Field(..., ge=0.0, description="Waktu pemrosesan inferensi dalam milidetik")
    image_dimensions: List[int] = Field(..., description="Dimensi gambar [width, height]")
    model_info: str = Field(..., description="Informasi model yang digunakan")
    disclaimer: str = Field(default=AI_DISCLAIMER_TEXT)
