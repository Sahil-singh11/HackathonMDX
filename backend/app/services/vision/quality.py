"""Image quality gate — runs BEFORE any model call. Unusable images never spend tokens."""
from __future__ import annotations

import hashlib
import io

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.analysis import ImageQuality

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MIN_DIM = 200
MAX_ANALYSIS_DIM = 1280
BLUR_POOR = 60.0
BLUR_INVALID = 15.0
DARK = 45.0
BRIGHT = 215.0


class ProcessedImage:
    def __init__(self, quality: ImageQuality, jpeg_for_api: bytes | None, sha256: str | None):
        self.quality = quality
        self.jpeg_for_api = jpeg_for_api
        self.sha256 = sha256


def assess(data: bytes, content_type: str | None, max_bytes: int) -> ProcessedImage:
    warnings: list[str] = []
    if content_type and content_type.lower() not in ALLOWED_MIME:
        return ProcessedImage(ImageQuality(status="invalid", warnings=[f"unsupported_type:{content_type}"]), None, None)
    if len(data) > max_bytes:
        return ProcessedImage(ImageQuality(status="invalid", warnings=["file_too_large"]), None, None)
    if len(data) < 100:
        return ProcessedImage(ImageQuality(status="invalid", warnings=["file_too_small"]), None, None)
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))  # reopen after verify
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        return ProcessedImage(ImageQuality(status="invalid", warnings=["not_a_valid_image"]), None, None)

    if min(img.size) < MIN_DIM:
        return ProcessedImage(ImageQuality(status="invalid", warnings=["image_too_small"]), None, None)

    img.thumbnail((MAX_ANALYSIS_DIM, MAX_ANALYSIS_DIM))
    arr = np.asarray(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())

    if brightness < DARK:
        warnings.append("underexposed")
    if brightness > BRIGHT:
        warnings.append("overexposed")
    # glare: large share of near-saturated pixels
    if float((gray > 245).mean()) > 0.12:
        warnings.append("possible_glare")
    if blur_score < BLUR_POOR:
        warnings.append("blurry")

    if blur_score < BLUR_INVALID:
        status = "invalid"
    elif warnings:
        status = "poor"
    else:
        status = "acceptable"

    quality = ImageQuality(status=status, blur_score=round(blur_score, 1), brightness=round(brightness, 1), warnings=warnings)

    jpeg = None
    if status != "invalid":
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        jpeg = buf.getvalue()
    return ProcessedImage(quality, jpeg, hashlib.sha256(data).hexdigest())
