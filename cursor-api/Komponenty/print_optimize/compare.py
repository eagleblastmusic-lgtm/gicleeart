"""Metryki porownania obrazow (kalibracja vs Whitewall lub A/B)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .apply import load_rgb_image


@dataclass
class CompareMetrics:
    delta_e_mean: float
    delta_e_p95: float
    ssim: float
    psnr: float
    width: int
    height: int

    def summary(self) -> str:
        return (
            f"dE mean={self.delta_e_mean:.2f}  dE p95={self.delta_e_p95:.2f}  "
            f"SSIM={self.ssim:.4f}  PSNR={self.psnr:.2f} dB  "
            f"{self.width}x{self.height}"
        )


def compare_images(
    reference_path: Path | str,
    candidate_path: Path | str,
    *,
    max_edge: int = 1200,
) -> CompareMetrics:
    ref = _to_array(load_rgb_image(reference_path), max_edge)
    cand = _to_array(load_rgb_image(candidate_path), max_edge)
    if ref.shape != cand.shape:
        raise ValueError(
            f"Rozmiary po skalowaniu rozne: ref={ref.shape} cand={cand.shape}"
        )

    lab_ref = _rgb_to_lab(ref)
    lab_cand = _rgb_to_lab(cand)
    delta = np.linalg.norm(lab_ref - lab_cand, axis=-1)
    mse = float(np.mean((ref - cand) ** 2))
    psnr = 100.0 if mse <= 1e-12 else 10.0 * np.log10(1.0 / mse)

    return CompareMetrics(
        delta_e_mean=float(np.mean(delta)),
        delta_e_p95=float(np.percentile(delta, 95)),
        ssim=float(_ssim(ref, cand)),
        psnr=float(psnr),
        width=int(ref.shape[1]),
        height=int(ref.shape[0]),
    )


def _to_array(image: Image.Image, max_edge: int) -> np.ndarray:
    w, h = image.size
    scale = min(1.0, max_edge / max(w, h))
    if scale < 1.0:
        image = image.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))),
            Image.Resampling.LANCZOS,
        )
    return np.asarray(image, dtype=np.float32) / 255.0


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB -> CIELAB (D65), wektorowo."""
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    xn, yn, zn = 0.95047, 1.0, 1.08883
    x, y, z = x / xn, y / yn, z / zn

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > 0.008856, t ** (1.0 / 3.0), 7.787 * t + 16.0 / 116.0)

    fx, fy, fz = f(x), f(y), f(z)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def _ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """Uproszczony SSIM na jawnosci (Y) — wystarczy do trendu kalibracji."""
    y1 = 0.2126 * img1[..., 0] + 0.7152 * img1[..., 1] + 0.0722 * img1[..., 2]
    y2 = 0.2126 * img2[..., 0] + 0.7152 * img2[..., 1] + 0.0722 * img2[..., 2]
    c1 = (0.01 ** 2)
    c2 = (0.03 ** 2)
    mu1 = y1.mean()
    mu2 = y2.mean()
    sigma1 = y1.var()
    sigma2 = y2.var()
    sigma12 = float(((y1 - mu1) * (y2 - mu2)).mean())
    num = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
    den = (mu1 ** 2 + mu2 ** 2 + c1) * (sigma1 + sigma2 + c2)
    return float(num / (den + 1e-12))
