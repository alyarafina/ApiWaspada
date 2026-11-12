"""
Utilitas validasi koordinat geografis (Latitude & Longitude) dan pemeriksaan
cakupan wilayah Kota Jambi.
"""
import math
from typing import Any, Dict, Tuple

from fastapi import HTTPException, status

from backend.app.config import settings


def validate_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Memvalidasi koordinat GPS berada pada rentang bumi yang sah
    (Latitude: -90 s/d 90, Longitude: -180 s/d 180) dan bukan NaN/Inf.
    """
    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Koordinat lokasi (latitude dan longitude) wajib diisi.",
        )

    try:
        lat = float(latitude)
        lng = float(longitude)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Koordinat latitude dan longitude harus berupa angka desimal yang valid.",
        ) from exc

    if math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nilai koordinat tidak boleh NaN atau Infinity.",
        )

    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Latitude ({lat}) tidak valid. Nilai harus berada di antara -90 dan 90.",
        )

    if not (-180.0 <= lng <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Longitude ({lng}) tidak valid. Nilai harus berada di antara -180 dan 180.",
        )

    if lat == 0.0 and lng == 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Koordinat (0.0, 0.0) tidak valid. Silakan ambil lokasi GPS atau pilih titik di peta.",
        )

    return round(lat, 6), round(lng, 6)


def check_jambi_bounds(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Memeriksa apakah koordinat berada di dalam atau sekitar cakupan Kota Jambi.
    Tidak menolak laporan di luar batas administratif (agar pengujian dari luar kota
    tetap berfungsi), tetapi menyertakan penanda informasi cakupan wilayah.
    """
    in_jambi = (
        settings.JAMBI_BOUNDS_MIN_LAT <= latitude <= settings.JAMBI_BOUNDS_MAX_LAT
        and settings.JAMBI_BOUNDS_MIN_LNG <= longitude <= settings.JAMBI_BOUNDS_MAX_LNG
    )
    return {
        "in_jambi_area": in_jambi,
        "region_note": (
            "Koordinat berada di wilayah Kota Jambi / sekitarnya."
            if in_jambi
            else "Koordinat berada di luar batas referensi Kota Jambi."
        ),
    }
