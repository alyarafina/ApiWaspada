"""
Modul Keamanan Aplikasi ApiWaspada:
- Password hashing menggunakan PBKDF2-HMAC-SHA256 dengan salt unik (standar kriptografi Python `hashlib` + `secrets`).
- Pembuatan dan verifikasi token autentikasi bertanda tangan HMAC-SHA256 (kompatibel JWT).
- Sanitasi string input terhadap serangan Cross-Site Scripting (XSS).
"""
import base64
import hashlib
import hmac
import html
import json
import re
import secrets
import time
from typing import Any, Dict, Optional

from backend.app.config import settings

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """Menghasilkan hash password dengan PBKDF2-HMAC-SHA256 dan salt acak 16-byte."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    digest = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Memverifikasi password terhadap hash yang tersimpan secara constant-time."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_digest = parts[3]
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        actual_digest = base64.b64encode(dk).decode("ascii")
        return hmac.compare_digest(actual_digest, expected_digest)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("ascii"))


def create_access_token(
    subject: str,
    role: str = "officer",
    full_name: str = "",
    expires_minutes: Optional[int] = None,
) -> str:
    """Membuat token autentikasi bertanda tangan HMAC-SHA256 (format JWT HS256)."""
    exp_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "full_name": full_name,
        "iat": now,
        "exp": now + (exp_minutes * 60),
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Memvalidasi tanda tangan dan masa berlaku token JWT HS256."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload: Dict[str, Any] = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if int(time.time()) > exp:
            return None
        return payload
    except Exception:
        return None


_SCRIPT_TAG_RE = re.compile(r"<\s*/?\s*script[^>]*>", re.IGNORECASE)


def sanitize_text(value: Optional[str], max_length: int = 1000) -> str:
    """
    Membersihkan teks input dari tag berbahaya untuk mencegah XSS
    dan membatasi panjang karakter.
    """
    if value is None:
        return ""
    cleaned = value.strip()
    cleaned = _SCRIPT_TAG_RE.sub("", cleaned)
    cleaned = html.escape(cleaned, quote=True)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned
