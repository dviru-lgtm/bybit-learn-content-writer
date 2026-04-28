"""
Screenshot processing utilities.
Handles resizing, base64 encoding, and thumbnail generation.
"""

import base64
import io
from pathlib import Path

from PIL import Image

MAX_DIMENSION = 1568  # Anthropic API max for vision
THUMBNAIL_SIZE = (200, 200)
SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    media_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return media_types.get(ext, "image/png")


def resize_for_api(image_bytes: bytes) -> bytes:
    """Resize image so the longest side is at most MAX_DIMENSION."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size

    if max(w, h) <= MAX_DIMENSION:
        return image_bytes

    if w > h:
        new_w = MAX_DIMENSION
        new_h = int(h * MAX_DIMENSION / w)
    else:
        new_h = MAX_DIMENSION
        new_w = int(w * MAX_DIMENSION / h)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    fmt = img.format or "PNG"
    if fmt.upper() == "JPEG":
        img.save(buf, format="JPEG", quality=85)
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()


def to_base64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def make_thumbnail(image_bytes: bytes) -> bytes:
    """Create a small thumbnail for UI preview."""
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def process_uploaded_file(uploaded_file) -> dict:
    """
    Process a Streamlit UploadedFile into the format needed by claude_api.

    Returns dict with keys: data (base64), media_type, filename, thumbnail_bytes
    """
    raw_bytes = uploaded_file.read()
    resized = resize_for_api(raw_bytes)
    thumbnail = make_thumbnail(raw_bytes)

    return {
        "data": to_base64(resized),
        "media_type": get_media_type(uploaded_file.name),
        "filename": uploaded_file.name,
        "thumbnail_bytes": thumbnail,
        "caption": "",
    }
