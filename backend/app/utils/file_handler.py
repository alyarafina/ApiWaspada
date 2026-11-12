"""
Utilitas penanganan upload file gambar secara aman:
- Validasi ekstensi (.jpg, .jpeg, .png) dan MIME type.
- Validasi ukuran maksimum file.
- Verifikasi integritas gambar menggunakan Pillow (mencegah file berbahaya yang menyamar sebagai gambar).
- Pencegahan Path Traversal dengan pembuatan nama file unik berbasis UUID + timestamp.
"""
import io
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from backend.app.config import settings
from backend.app.core.exceptions import InvalidImageError


def validate_and_read_image(upload_file: UploadFile) -> Tuple[bytes, str, Tuple[int, int]]:
    """
    Memvalidasi file gambar yang diunggah dan mengembalikan:
    (image_bytes, clean_extension, (width, height)).
    """
    if not upload_file or not upload_file.filename:
        raise InvalidImageError("File foto wajib diunggah.")

    # Cegah path traversal dengan hanya mengambil nama dasar file
    raw_filename = os.path.basename(upload_file.filename.strip())
    if ".." in raw_filename or "/" in raw_filename or "\\" in raw_filename:
        raise InvalidImageError("Nama file tidak valid.")

    ext = Path(raw_filename).suffix.lower().lstrip(".")
    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(e.upper() for e in settings.ALLOWED_EXTENSIONS)
        raise InvalidImageError(
            f"Format file '.{ext}' tidak didukung. Gunakan format: {allowed_str}."
        )

    content_type = (upload_file.content_type or "").lower()
    if content_type and content_type not in settings.ALLOWED_MIME_TYPES:
        raise InvalidImageError(
            f"Tipe konten '{content_type}' tidak diizinkan. Hanya gambar JPG, JPEG, dan PNG yang diperbolehkan."
        )

    # Baca isi file dan periksa ukuran
    file_bytes = upload_file.file.read()
    upload_file.file.seek(0)

    if not file_bytes or len(file_bytes) == 0:
        raise InvalidImageError("File gambar kosong (0 byte).")

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise InvalidImageError(
            f"Ukuran file melebihi batas maksimum {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # Verifikasi integritas biner gambar menggunakan Pillow
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img_format = (img.format or "").lower()
            if img_format not in ("jpeg", "jpg", "png"):
                raise InvalidImageError(
                    "Isi biner file bukan gambar JPEG atau PNG yang valid."
                )
            width, height = img.size
            img.verify()
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, Exception) as exc:
        raise InvalidImageError(
            f"File gambar rusak atau tidak dapat dibaca sebagai citra valid: {str(exc)}"
        ) from exc

    normalized_ext = "jpg" if ext in ("jpg", "jpeg") else "png"
    return file_bytes, normalized_ext, (width, height)


def save_uploaded_image(file_bytes: bytes, ext: str, prefix: str = "rep") -> Tuple[Path, str]:
    """
    Menyimpan gambar yang sudah divalidasi ke `storage/uploads/` dengan nama unik
    dan mengembalikan `(absolute_path, relative_url_path)`.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_token = uuid.uuid4().hex[:10]
    safe_filename = f"{prefix}_{timestamp}_{unique_token}.{ext}"

    target_path = (settings.UPLOAD_DIR / safe_filename).resolve()
    # Pastikan target_path benar-benar berada di dalam UPLOAD_DIR (anti path traversal)
    if settings.UPLOAD_DIR not in target_path.parents:
        raise InvalidImageError("Lokasi penyimpanan file tidak valid.")

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    relative_url = f"/storage/uploads/{safe_filename}"
    return target_path, relative_url
