"""API optymalizacji pod druk — analiza + korekcja + blend strength."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image

from .analyze import analyze_image
from .apply import apply_corrections, blend_strength, load_rgb_image
from .schemas import CorrectionParams

Logger = Callable[[str], None] | None


@dataclass
class OptimizeResult:
    params: CorrectionParams
    strength: float
    output_path: Path | None = None

    def params_json(self) -> str:
        return json.dumps(self.params.to_dict(), ensure_ascii=False, indent=2)


def optimize_image(
    image_path: Path | str,
    *,
    strength: float = 70.0,
    params: CorrectionParams | None = None,
    use_gemini: bool = True,
    on_status: Logger = None,
) -> tuple[Image.Image, OptimizeResult]:
    path = Path(image_path)
    original = load_rgb_image(path)

    if params is None:
        if use_gemini:
            params = analyze_image(path, on_status=on_status)
        else:
            params = CorrectionParams()

    corrected = apply_corrections(original, params)
    blended = blend_strength(original, corrected, strength)
    return blended, OptimizeResult(params=params, strength=strength)


def optimize_to_file(
    image_path: Path | str,
    output_path: Path | str,
    *,
    strength: float = 70.0,
    params: CorrectionParams | None = None,
    use_gemini: bool = True,
    save_params_path: Path | str | None = None,
    on_status: Logger = None,
) -> OptimizeResult:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    image, result = optimize_image(
        image_path,
        strength=strength,
        params=params,
        use_gemini=use_gemini,
        on_status=on_status,
    )
    image.save(out, quality=95, subsampling=0)
    result.output_path = out

    if save_params_path:
        p = Path(save_params_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(result.params_json(), encoding="utf-8")

    return result
