"""Schemat parametrow korekcji pod druk (odpowiednik pcStrength + scene AI)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class CorrectionParams:
    scene: str = "general"
    exposure: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    shadow_lift: float = 0.0
    highlight_recovery: float = 0.0
    temperature_shift: float = 0.0
    tint_shift: float = 0.0
    confidence: float = 0.0

    def clamp(self) -> CorrectionParams:
        self.exposure = _clamp(self.exposure, -0.35, 0.35)
        self.contrast = _clamp(self.contrast, 0.85, 1.25)
        self.saturation = _clamp(self.saturation, 0.85, 1.20)
        self.shadow_lift = _clamp(self.shadow_lift, 0.0, 0.35)
        self.highlight_recovery = _clamp(self.highlight_recovery, 0.0, 0.25)
        self.temperature_shift = _clamp(self.temperature_shift, -0.15, 0.15)
        self.tint_shift = _clamp(self.tint_shift, -0.10, 0.10)
        self.confidence = _clamp(self.confidence, 0.0, 1.0)
        self.scene = (self.scene or "general").strip()[:80] or "general"
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorrectionParams:
        known = {f.name for f in fields(cls)}
        kwargs = {k: data[k] for k in known if k in data}
        return cls(**kwargs).clamp()


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))
