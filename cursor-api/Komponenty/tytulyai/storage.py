"""Trwaly zapis roboczych tytulow i opisow (Tytuly AI)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, data_path

from .batch import BatchItemResult
from .descriptions import DescriptionVariant, ProductDescriptionDrafts

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_TITLE_DRAFTS_FILE = _LEGACY_DATA_DIR / "title_drafts.json"
_DEFAULT_DESCRIPTION_DRAFTS_FILE = _LEGACY_DATA_DIR / "description_drafts.json"
DATA_DIR = _LEGACY_DATA_DIR
TITLE_DRAFTS_FILE = _DEFAULT_TITLE_DRAFTS_FILE
DESCRIPTION_DRAFTS_FILE = _DEFAULT_DESCRIPTION_DRAFTS_FILE
_TITLE_DRAFTS = data_path("Komponenty/tytulyai/data/title_drafts.json", legacy=_DEFAULT_TITLE_DRAFTS_FILE)
_DESCRIPTION_DRAFTS = data_path("Komponenty/tytulyai/data/description_drafts.json", legacy=_DEFAULT_DESCRIPTION_DRAFTS_FILE)


def _resolved_path(path: Path, default: Path, app_path, *, for_write: bool) -> Path:
    if Path(path) != default:
        return Path(path)
    return app_path.write_path if for_write else app_path.read_path()


def _title_to_dict(item: BatchItemResult) -> dict[str, Any]:
    return {
        "product_id": item.product_id,
        "artist": item.artist,
        "painting_title": item.painting_title,
        "model_used": item.model_used,
        "raw_response": item.raw_response,
        "cursor_prompt": item.cursor_prompt,
        "error": item.error,
        "warning": item.warning,
        "generated_at": item.generated_at,
    }


def _title_from_dict(row: dict[str, Any]) -> BatchItemResult:
    gen_at = str(row.get("generated_at") or "").strip()
    return BatchItemResult(
        product_id=int(row.get("product_id") or 0),
        artist=str(row.get("artist") or ""),
        painting_title=str(row.get("painting_title") or ""),
        model_used=str(row.get("model_used") or ""),
        raw_response=str(row.get("raw_response") or ""),
        cursor_prompt=str(row.get("cursor_prompt") or ""),
        error=str(row.get("error") or ""),
        warning=str(row.get("warning") or ""),
        generated_at=gen_at,
    )


def _variant_to_dict(v: DescriptionVariant) -> dict[str, Any]:
    return {
        "model_used": v.model_used,
        "akapity": list(v.akapity),
        "raw_response": v.raw_response,
        "error": v.error,
        "generated_at": v.generated_at,
    }


def _variant_from_dict(row: dict[str, Any] | None) -> DescriptionVariant:
    if not isinstance(row, dict):
        return DescriptionVariant()
    akapity_raw = row.get("akapity")
    akapity = [str(a) for a in akapity_raw] if isinstance(akapity_raw, list) else []
    return DescriptionVariant(
        model_used=str(row.get("model_used") or ""),
        akapity=akapity,
        raw_response=str(row.get("raw_response") or ""),
        error=str(row.get("error") or ""),
        generated_at=str(row.get("generated_at") or ""),
    )


def _description_to_dict(item: ProductDescriptionDrafts) -> dict[str, Any]:
    return {
        "product_id": item.product_id,
        "artist": item.artist,
        "painting_title": item.painting_title,
        "v1": _variant_to_dict(item.v1),
        "v2": _variant_to_dict(item.v2),
    }


def _description_from_dict(row: dict[str, Any]) -> ProductDescriptionDrafts:
    if "v1" in row or "v2" in row:
        return ProductDescriptionDrafts(
            product_id=int(row.get("product_id") or 0),
            artist=str(row.get("artist") or ""),
            painting_title=str(row.get("painting_title") or ""),
            v1=_variant_from_dict(row.get("v1") if isinstance(row.get("v1"), dict) else None),
            v2=_variant_from_dict(row.get("v2") if isinstance(row.get("v2"), dict) else None),
        )
    # Stary format (tylko v1 w pliku plaskim)
    legacy = _variant_from_dict(row)
    return ProductDescriptionDrafts(
        product_id=int(row.get("product_id") or 0),
        artist=str(row.get("artist") or ""),
        painting_title=str(row.get("painting_title") or ""),
        v1=legacy,
        v2=DescriptionVariant(),
    )


def _load_drafts_file(path: Path, from_dict: Any) -> dict[int, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    raw = data.get("drafts") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return {}
    out: dict[int, Any] = {}
    for key, row in raw.items():
        if not isinstance(row, dict):
            continue
        try:
            pid = int(key)
        except (TypeError, ValueError):
            pid = int(row.get("product_id") or 0)
        if pid:
            out[pid] = from_dict(row)
    return out


def _save_drafts_file(path: Path, drafts: dict[int, Any], to_dict: Any) -> None:
    payload = {
        "version": 2,
        "drafts": {str(pid): to_dict(item) for pid, item in sorted(drafts.items())},
    }
    default = _DEFAULT_TITLE_DRAFTS_FILE if Path(path).name == "title_drafts.json" else _DEFAULT_DESCRIPTION_DRAFTS_FILE
    app_path = _TITLE_DRAFTS if default == _DEFAULT_TITLE_DRAFTS_FILE else _DESCRIPTION_DRAFTS
    atomic_write_text(_resolved_path(path, default, app_path, for_write=True), json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def load_title_drafts() -> dict[int, BatchItemResult]:
    return _load_drafts_file(_resolved_path(TITLE_DRAFTS_FILE, _DEFAULT_TITLE_DRAFTS_FILE, _TITLE_DRAFTS, for_write=False), _title_from_dict)


def save_title_drafts(drafts: dict[int, BatchItemResult]) -> None:
    _save_drafts_file(TITLE_DRAFTS_FILE, drafts, _title_to_dict)


def load_description_drafts() -> dict[int, ProductDescriptionDrafts]:
    return _load_drafts_file(_resolved_path(DESCRIPTION_DRAFTS_FILE, _DEFAULT_DESCRIPTION_DRAFTS_FILE, _DESCRIPTION_DRAFTS, for_write=False), _description_from_dict)


def save_description_drafts(drafts: dict[int, ProductDescriptionDrafts]) -> None:
    _save_drafts_file(DESCRIPTION_DRAFTS_FILE, drafts, _description_to_dict)
