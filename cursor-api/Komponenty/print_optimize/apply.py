"""Deterministyczna korekcja obrazu (RGB, wektorowo przez numpy)."""

from __future__ import annotations

from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "print_optimize wymaga Pillow i numpy: pip install Pillow numpy"
    ) from exc

from .schemas import CorrectionParams


def load_rgb_image(path: Path | str) -> Image.Image:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        return im.convert("RGB")


def apply_corrections(image: Image.Image, params: CorrectionParams) -> Image.Image:
    params = params.clamp()
    arr = np.asarray(image, dtype=np.float32) / 255.0

    arr = _apply_exposure(arr, params.exposure)
    arr = _apply_contrast(arr, params.contrast)
    arr = _apply_temperature_tint(arr, params.temperature_shift, params.tint_shift)
    arr = _apply_saturation(arr, params.saturation)
    arr = _apply_shadow_lift(arr, params.shadow_lift)
    arr = _apply_highlight_recovery(arr, params.highlight_recovery)

    arr = np.clip(arr, 0.0, 1.0)
    return Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8), mode="RGB")


def blend_strength(
    original: Image.Image,
    corrected: Image.Image,
    strength: float,
) -> Image.Image:
    """Mieszanka oryginal / skorygowany (0..100 jak Whitewall pcStrength)."""
    s = max(0.0, min(100.0, float(strength))) / 100.0
    if s <= 0.0:
        return original.copy()
    if s >= 1.0:
        return corrected.copy()
    if original.size != corrected.size:
        corrected = corrected.resize(original.size, Image.Resampling.LANCZOS)
    o = np.asarray(original, dtype=np.float32)
    c = np.asarray(corrected, dtype=np.float32)
    out = o * (1.0 - s) + c * s
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")


def _apply_exposure(arr: np.ndarray, exposure: float) -> np.ndarray:
    if abs(exposure) < 1e-6:
        return arr
    return arr * (1.0 + exposure)


def _apply_contrast(arr: np.ndarray, contrast: float) -> np.ndarray:
    if abs(contrast - 1.0) < 1e-6:
        return arr
    return (arr - 0.5) * contrast + 0.5


def _luma(arr: np.ndarray) -> np.ndarray:
    return (
        0.2126 * arr[..., 0]
        + 0.7152 * arr[..., 1]
        + 0.0722 * arr[..., 2]
    )


def _apply_shadow_lift(arr: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0.0:
        return arr
    y = _luma(arr)
    mask = (1.0 - y) ** 2.0
    return arr + mask[..., None] * amount


def _apply_highlight_recovery(arr: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0.0:
        return arr
    y = _luma(arr)
    mask = y ** 2.0
    return arr - mask[..., None] * amount


def _apply_temperature_tint(
    arr: np.ndarray,
    temperature: float,
    tint: float,
) -> np.ndarray:
    out = arr.copy()
    if abs(temperature) > 1e-6:
        out[..., 0] = out[..., 0] + temperature * 0.12
        out[..., 2] = out[..., 2] - temperature * 0.12
    if abs(tint) > 1e-6:
        out[..., 1] = out[..., 1] + tint * 0.08
    return out


def _rgb_to_hsv(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.max(arr, axis=-1)
    mn = np.min(arr, axis=-1)
    diff = mx - mn + 1e-8

    h = np.zeros_like(mx)
    mask = mx == r
    h[mask] = ((g - b)[mask] / diff[mask]) % 6.0
    mask = mx == g
    h[mask] = ((b - r)[mask] / diff[mask]) + 2.0
    mask = mx == b
    h[mask] = ((r - g)[mask] / diff[mask]) + 4.0
    h = h / 6.0

    s = np.where(mx <= 1e-8, 0.0, diff / (mx + 1e-8))
    v = mx
    return h, s, v


def _hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    i = np.floor(h * 6.0).astype(np.int32)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i % 6

    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def _apply_saturation(arr: np.ndarray, saturation: float) -> np.ndarray:
    if abs(saturation - 1.0) < 1e-6:
        return arr
    h, s, v = _rgb_to_hsv(arr)
    s = np.clip(s * saturation, 0.0, 1.0)
    return _hsv_to_rgb(h, s, v)
