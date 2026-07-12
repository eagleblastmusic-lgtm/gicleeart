"""Historia ostatnio użytych grafik (shopify refs) — wspólna dla edytorów stron.

Odczyt preferuje AppData i zachowuje tymczasowy fallback do starego pliku w
`_shared/data/recent_images.json`. Każdy nowy zapis trafia wyłącznie do AppData.
"""

from __future__ import annotations

import json
from pathlib import Path

from giclee_app.app_paths import atomic_write_text, data_path

_LEGACY_STORE_FILE = Path(__file__).resolve().parent / "data" / "recent_images.json"
_STORE = data_path(
    "Komponenty/_shared/data/recent_images.json",
    legacy=_LEGACY_STORE_FILE,
)
MAX_RECENT = 30


def _load_raw() -> list[str]:
    path = _STORE.read_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
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
        atomic_write_text(
            _STORE.write_path,
            json.dumps(refs, ensure_ascii=False, indent=2) + "\n",
        )
    except OSError:
        pass


__all__ = ["MAX_RECENT", "add_recent_image", "list_recent_images"]
