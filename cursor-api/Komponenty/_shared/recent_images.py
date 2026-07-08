"""Historia ostatnio użytych grafik (shopify refs) — wspólna dla edytorów stron.

Zapis w prostym JSON w `_shared/data/recent_images.json`. Lista refów w kolejności
od najnowszego. Deduplikacja po wartości ref, przycięcie do MAX_RECENT.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_STORE_FILE = _DATA_DIR / "recent_images.json"
MAX_RECENT = 30


def _load_raw() -> list[str]:
    if not _STORE_FILE.is_file():
        return []
    try:
        data = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip() for x in data if str(x).strip()]


def list_recent_images(limit: int = MAX_RECENT) -> list[str]:
    """Refy ostatnio użytych grafik, od najnowszej. Pusta lista gdy brak historii."""
    refs = _load_raw()
    if limit > 0:
        return refs[:limit]
    return refs


def add_recent_image(ref: str) -> None:
    """Dopisuje ref na początek historii (dedupe, cap MAX_RECENT). Ciche na błędzie I/O."""
    ref = (ref or "").strip()
    if not ref:
        return
    refs = [r for r in _load_raw() if r != ref]
    refs.insert(0, ref)
    refs = refs[:MAX_RECENT]
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _STORE_FILE.write_text(
            json.dumps(refs, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


__all__ = ["MAX_RECENT", "add_recent_image", "list_recent_images"]
