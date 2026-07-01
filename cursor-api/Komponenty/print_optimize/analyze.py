"""Analiza sceny przez Gemini -> CorrectionParams."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from Komponenty._shared.gemini_client import generate_from_image_file

from .json_util import extract_json_object
from .prompt import ANALYSIS_PROMPT
from .schemas import CorrectionParams

Logger = Callable[[str], None] | None


def analyze_image(
    image_path: Path | str,
    *,
    on_status: Logger = None,
) -> CorrectionParams:
    text, model = generate_from_image_file(
        image_path=image_path,
        prompt=ANALYSIS_PROMPT,
        on_status=on_status,
    )
    if on_status:
        on_status(f"Gemini ({model}): parsuje parametry korekcji...")
    data = extract_json_object(text)
    return CorrectionParams.from_dict(data)


def analyze_image_with_raw(
    image_path: Path | str,
    *,
    on_status: Logger = None,
) -> tuple[CorrectionParams, str, str]:
    text, model = generate_from_image_file(
        image_path=image_path,
        prompt=ANALYSIS_PROMPT,
        on_status=on_status,
    )
    data = extract_json_object(text)
    return CorrectionParams.from_dict(data), text, model


def load_preset(path: Path | str) -> CorrectionParams:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return CorrectionParams.from_dict(data)
