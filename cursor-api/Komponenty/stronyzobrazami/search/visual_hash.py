"""Perceptual hash (dHash) — porownanie podobienstwa obrazow bez zewnetrznych bibliotek."""

from __future__ import annotations

from io import BytesIO

from PIL import Image


def _load_rgb(data: bytes | Image.Image) -> Image.Image:
    if isinstance(data, Image.Image):
        img = data.convert("RGB")
    else:
        img = Image.open(BytesIO(data))
        img = img.convert("RGB")
    return img


def dhash(data: bytes | Image.Image, *, size: int = 9) -> int:
    """Difference hash — 64 bity (size=9 -> 8x8 roznic)."""
    img = _load_rgb(data)
    img = img.resize((size, size - 1), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    w = size
    bits = 0
    bit = 0
    for row in range(size - 1):
        for col in range(w - 1):
            left = pixels[row * w + col]
            right = pixels[row * w + col + 1]
            gray_l = left[0] * 299 + left[1] * 587 + left[2] * 114
            gray_r = right[0] * 299 + right[1] * 587 + right[2] * 114
            if gray_l > gray_r:
                bits |= 1 << bit
            bit += 1
    return bits


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def similarity_score(a: int, b: int, *, bits: int = 64) -> float:
    """0..100 — wyzsze = bardziej podobne."""
    dist = hamming(a, b)
    return max(0.0, min(100.0, (1.0 - dist / bits) * 100.0))
