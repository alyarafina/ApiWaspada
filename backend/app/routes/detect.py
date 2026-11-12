"""
Router Deteksi Visual AI YOLO (`/api/detect`).
"""
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, status

from backend.app.schemas.detection import DetectionResponse, DetectionStatusResponse
from backend.app.services.ai_service import ai_service
from backend.app.utils.file_handler import save_uploaded_image, validate_and_read_image

router = APIRouter(prefix="/api/detect", tags=["AI Detection"])


@router.get(
    "/status",
    response_model=DetectionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Periksa status ketersediaan model AI YOLO (best.pt)",
)
def get_ai_detection_status() -> DetectionStatusResponse:
    """
    Mengembalikan informasi apakah model `ml/weights/best.pt` sudah tersedia
    dan siap melakukan deteksi api serta asap.
    """
    return ai_service.get_status()


@router.post(
    "",
    response_model=DetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Jalankan deteksi visual api dan asap pada gambar yang diunggah",
)
def detect_fire_and_smoke(
    image: UploadFile = File(..., description="File gambar (JPG, JPEG, PNG)"),
    confidence: Optional[float] = Form(
        default=None,
        ge=0.05,
        le=0.95,
        description="Ambang batas confidence opsional (default: 0.25)",
    ),
) -> DetectionResponse:
    """
    Memvalidasi gambar yang diunggah, menyimpannya ke `storage/uploads/`,
    memprosesnya menggunakan model YOLO, membuat visualisasi bounding box di
    `storage/results/`, dan mengembalikan hasil deteksi beserta confidence score.
    """
    file_bytes, ext, _ = validate_and_read_image(image)
    saved_path, relative_url = save_uploaded_image(file_bytes, ext, prefix="det")

    return ai_service.run_detection(
        image_path=saved_path,
        original_image_url=relative_url,
        conf_threshold=confidence,
    )
