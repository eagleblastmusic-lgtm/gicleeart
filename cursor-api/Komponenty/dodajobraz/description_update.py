"""Aktualizacja opisu produktu (akapity PL + tlumaczenia) z tablicy JSON LLM."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from giclee_app.app_paths import atomic_write_text, data_path

from . import shopify_client as sc
from .collection_control import collection_title_matches_expected
from .body_i18n import translate_field_value_or_pl
from .create import (
    PRODUCT_TYPE,
    _split_artist_title,
    push_product_translations,
)
from .html_template import (
    build_body_html,
    build_locale_body_html_from_pl,
    extract_display_title_from_body_html,
    extract_original_title_from_body_html,
    extract_paragraphs_from_body_html,
    replace_paragraphs_in_body_html,
    set_detail_value_in_body_html,
    set_display_title_in_body_html,
)
from .parser import (
    artist_display_from_catalog_title,
    artist_collection_title,
    compute_source_key,
    parse_artist_catalog_title,
    parse_filename,
)
from .prompt_builder import TRANSLATION_LANGS, canonical_product_filename

UpdateMode = Literal["replace_all", "replace_paragraph", "add_paragraph"]

LOCALE_LABELS: dict[str, str] = {
    "pl": "Polski (podstawowy)",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "nl": "Nederlands",
    "it": "Italiano",
}

Logger = Callable[[str], None] | None

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"


def _runtime_data_file(path: Path, *, for_write: bool = False) -> Path:
    """Resolve a DodajObraz mutable JSON path without writing to source.

    Existing tests and tools may monkeypatch a concrete file constant. Such an
    explicit override remains authoritative. In the default layout AppData wins
    for reads, while the source-tree file is a read-only legacy fallback.
    """

    current = Path(path)
    legacy = _LEGACY_DATA_DIR / current.name
    if current != legacy:
        return current
    app_path = data_path(
        f"Komponenty/dodajobraz/data/{current.name}",
        legacy=legacy,
    )
    return app_path.write_path if for_write else app_path.read_path()


_RUNTIME_FILE_CONSTANT_RE = re.compile(r"^_[A-Z0-9_]+_FILE$")


def _runtime_data_file_for_constant(
    constant_name: str,
    *,
    for_write: bool = False,
) -> Path:
    """Resolve the current value of a mutable-file module constant.

    The indirection keeps monkeypatched file constants authoritative without
    passing a source-derived ``Path`` into write-like helpers.
    """

    name = str(constant_name).strip()
    if not _RUNTIME_FILE_CONSTANT_RE.fullmatch(name):
        raise ValueError(f"Unsafe description runtime file constant: {constant_name!r}")
    try:
        configured = globals()[name]
    except KeyError as exc:
        raise KeyError(f"Unknown description runtime file constant: {name}") from exc
    return _runtime_data_file(Path(configured), for_write=for_write)


_AKAPITY_MAX = 4
_DESCRIPTION_UPDATE_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_update_marks.json"
)
_DESCRIPTION_PL_PENDING_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_pl_pending_marks.json"
)
_DESCRIPTION_GPT_TRANSLATION_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_gpt_translation_marks.json"
)
_DESCRIPTION_SONNET_TRANSLATION_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_sonnet_translation_marks.json"
)
_DESCRIPTION_FROM_IMAGE_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_from_image_marks.json"
)
_DESCRIPTION_DO_TLUMACZENIA_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_do_tlumaczenia_marks.json"
)
_DESCRIPTION_TRANSLATIONS_SENT_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_translations_sent_marks.json"
)
_DESCRIPTION_BEZ_16_MARKS_FILE = (
    _LEGACY_DATA_DIR / "description_bez_16_marks.json"
)
_TITLE_UPDATE_MARKS_FILE = (
    _LEGACY_DATA_DIR / "title_update_marks.json"
)
DESCRIPTION_UPDATED_LABEL = "Po aktualizacji"
DESCRIPTION_PL_PENDING_LABEL = "PL bez tlumaczen"
DESCRIPTION_DO_TLUMACZENIA_LABEL = "Do tlumaczenia"
DESCRIPTION_BEZ_16_LABEL = "Bez 1-6"
DESCRIPTION_RESUME_FLAG_LABEL = "Tu skonczylem"


def format_description_update_progress(*, marked: int, total: int) -> str:
    """Tekst postepu: «Po aktualizacji: 42/238 (17.6%)»."""
    if total <= 0:
        return f"{DESCRIPTION_UPDATED_LABEL}: —"
    marked_n = max(0, int(marked))
    pct = marked_n / total * 100.0
    return f"{DESCRIPTION_UPDATED_LABEL}: {marked_n}/{total} ({pct:.1f}%)"


def format_description_pl_pending_progress(*, marked: int, total: int) -> str:
    """Tekst postepu: «PL bez tlumaczen: 5/238 (2.1%)»."""
    if total <= 0:
        return f"{DESCRIPTION_PL_PENDING_LABEL}: —"
    marked_n = max(0, int(marked))
    pct = marked_n / total * 100.0
    return f"{DESCRIPTION_PL_PENDING_LABEL}: {marked_n}/{total} ({pct:.1f}%)"


def format_do_tlumaczenia_progress(*, marked: int, total: int) -> str:
    """Tekst postepu: «Do tlumaczenia: 42/238 (17.6%)»."""
    if total <= 0:
        return f"{DESCRIPTION_DO_TLUMACZENIA_LABEL}: —"
    marked_n = max(0, int(marked))
    pct = marked_n / total * 100.0
    return f"{DESCRIPTION_DO_TLUMACZENIA_LABEL}: {marked_n}/{total} ({pct:.1f}%)"


def bucket_has_filled_compare_versions(bucket: dict[str, Any]) -> bool:
    """True gdy porownywarka ma co najmniej jeden niepusty slot wersji (1–6, ZO1, ZO2, G1, G2)."""
    raw_versions = bucket.get("versions") or {}
    if not isinstance(raw_versions, dict):
        return False
    for slots in raw_versions.values():
        for text in _normalize_compare_slot_versions(slots):
            if (text or "").strip():
                return True
    return False


def product_has_filled_compare_versions(
    compare_store: dict[int, dict[str, Any]],
    product_id: int,
) -> bool:
    """True gdy produkt ma zapisane niepuste sloty wersji w porownywarc (dowolny jezyk)."""
    locales = compare_store.get(int(product_id))
    if not isinstance(locales, dict):
        return False
    for bucket in locales.values():
        if isinstance(bucket, dict) and bucket_has_filled_compare_versions(bucket):
            return True
    return False


def count_unmarked_products_with_compare_versions(
    rows: list[dict[str, Any]],
    compare_store: dict[int, dict[str, Any]],
    marked_ids: set[int],
) -> int:
    """Produkty z co najmniej jedna wypelniona wersja porownywarki, bez «Po aktualizacji»."""
    n = 0
    for row in rows:
        try:
            pid = int(row.get("product_id") or 0)
        except (TypeError, ValueError):
            continue
        if not pid or pid in marked_ids:
            continue
        if product_has_filled_compare_versions(compare_store, pid):
            n += 1
    return n


def format_compare_versions_unmarked_note(*, count: int, total: int) -> str:
    """Tekst licznika: «Inne wersje (nie oznaczone): 12/238 (5.0%)»."""
    count_n = max(0, int(count))
    if total <= 0:
        return "Inne wersje (nie oznaczone): —"
    pct = count_n / total * 100.0
    return f"Inne wersje (nie oznaczone): {count_n}/{total} ({pct:.1f}%)"


RESUME_FLAG_TREE_LABEL = "\U0001f6a9"
CHECKMARK_TREE_LABEL = "\u2713"
TITLE_UPDATED_LABEL = "Tytuł zmieniony"

_DESCRIPTION_RESUME_FLAG_FILE = (
    _LEGACY_DATA_DIR / "description_resume_flag.json"
)


def load_description_update_marks() -> set[int]:
    """Zestaw product_id oznaczonych w oknie «Aktualizuj opis» jako «opis po aktualizacji»."""
    path = _runtime_data_file(_DESCRIPTION_UPDATE_MARKS_FILE)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(data, list):
        return set()
    out: set[int] = set()
    for item in data:
        try:
            out.add(int(item))
        except (TypeError, ValueError):
            continue
    return out


def save_description_update_marks(product_ids: set[int]) -> None:
    path = _runtime_data_file(_DESCRIPTION_UPDATE_MARKS_FILE, for_write=True)
    payload = sorted(product_ids)
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def set_description_update_mark(product_id: int, *, marked: bool) -> None:
    marks = load_description_update_marks()
    pid = int(product_id)
    if marked:
        marks.add(pid)
        set_description_pl_pending_mark(pid, marked=False)
    else:
        marks.discard(pid)
    save_description_update_marks(marks)


def toggle_description_update_mark(product_id: int) -> bool:
    """Przelacza oznaczenie produktu. Zwraca nowy stan (True = oznaczony)."""
    marks = load_description_update_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
        set_description_pl_pending_mark(pid, marked=False)
    save_description_update_marks(marks)
    return marked


def load_description_pl_pending_marks() -> set[int]:
    """Produkty z zaktualizowanym opisem PL, bez kompletu tlumaczen."""
    return _load_marks_file("_DESCRIPTION_PL_PENDING_MARKS_FILE")


def save_description_pl_pending_marks(product_ids: set[int]) -> None:
    _save_marks_file("_DESCRIPTION_PL_PENDING_MARKS_FILE", product_ids)


def set_description_pl_pending_mark(product_id: int, *, marked: bool) -> None:
    marks = load_description_pl_pending_marks()
    if marked:
        marks.add(int(product_id))
    else:
        marks.discard(int(product_id))
    save_description_pl_pending_marks(marks)


def update_description_marks_after_save(
    product_id: int,
    *,
    saved_locales: Iterable[str],
    translations_pushed: bool = False,
    translations_pasted: bool = False,
) -> None:
    """Ustawia zielone (pelne) lub fioletowe (tylko PL) oznaczenie po zapisie opisu."""
    pid = int(product_id)
    saved = {str(loc) for loc in saved_locales}
    foreign = set(TRANSLATION_LANGS)
    if translations_pasted and saved & foreign:
        set_description_pl_pending_mark(pid, marked=False)
        set_description_update_mark(pid, marked=True)
        return
    if translations_pushed or foreign <= saved:
        set_description_pl_pending_mark(pid, marked=False)
        set_description_update_mark(pid, marked=True)
        return
    if "pl" in saved:
        set_description_update_mark(pid, marked=False)
        set_description_pl_pending_mark(pid, marked=True)


def load_description_resume_flag() -> int | None:
    """product_id pozycji oznaczonej flaga «tu skonczylem» (jedna na cala liste)."""
    path = _runtime_data_file(_DESCRIPTION_RESUME_FLAG_FILE)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data is None:
        return None
    if isinstance(data, dict):
        data = data.get("product_id")
    try:
        pid = int(data)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def set_description_resume_flag(product_id: int | None) -> None:
    """Ustawia lub czysci flage wznowienia (tylko jeden produkt naraz)."""
    path = _runtime_data_file(_DESCRIPTION_RESUME_FLAG_FILE, for_write=True)
    if product_id is None:
        atomic_write_text(path, "null\n")
        return
    atomic_write_text(path, json.dumps(int(product_id)) + "\n")


def toggle_description_resume_flag(product_id: int) -> bool:
    """Ustawia flage na produkcie lub zdejmuje, jesli juz jest. Zwraca True gdy flaga aktywna."""
    pid = int(product_id)
    current = load_description_resume_flag()
    if current == pid:
        set_description_resume_flag(None)
        return False
    set_description_resume_flag(pid)
    return True


def _load_marks_file(file_constant: str) -> set[int]:
    path = _runtime_data_file_for_constant(file_constant)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(data, list):
        return set()
    out: set[int] = set()
    for item in data:
        try:
            out.add(int(item))
        except (TypeError, ValueError):
            continue
    return out


def _save_marks_file(file_constant: str, product_ids: set[int]) -> None:
    path = _runtime_data_file_for_constant(file_constant, for_write=True)
    payload = sorted(product_ids)
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def load_title_update_marks() -> set[int]:
    """Zestaw product_id, dla ktorych tytul produktu juz zostal zmieniony w sklepie."""
    return _load_marks_file("_TITLE_UPDATE_MARKS_FILE")


def save_title_update_marks(product_ids: set[int]) -> None:
    _save_marks_file("_TITLE_UPDATE_MARKS_FILE", product_ids)


def set_title_update_mark(product_id: int, *, marked: bool) -> None:
    marks = load_title_update_marks()
    if marked:
        marks.add(int(product_id))
    else:
        marks.discard(int(product_id))
    save_title_update_marks(marks)


def toggle_title_update_mark(product_id: int) -> bool:
    """Przelacza oznaczenie «tytul zmieniony». Zwraca nowy stan (True = oznaczony)."""
    marks = load_title_update_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
    save_title_update_marks(marks)
    return marked


def set_title_update_marks_batch(
    product_ids: Iterable[int],
    *,
    marked: bool,
) -> int:
    """Ustawia oznaczenie «tytul zmieniony» dla wielu produktow. Zwraca liczbe ID."""
    ids = {int(pid) for pid in product_ids if int(pid) > 0}
    if not ids:
        return 0
    marks = load_title_update_marks()
    if marked:
        marks.update(ids)
    else:
        marks -= ids
    save_title_update_marks(marks)
    return len(ids)


def load_description_gpt_translation_marks() -> set[int]:
    """Produkty oznaczone recznie jako «tlumaczenie GPT»."""
    return _load_marks_file("_DESCRIPTION_GPT_TRANSLATION_MARKS_FILE")


def save_description_gpt_translation_marks(product_ids: set[int]) -> None:
    _save_marks_file("_DESCRIPTION_GPT_TRANSLATION_MARKS_FILE", product_ids)


def set_description_gpt_translation_marks_batch(
    product_ids: Iterable[int],
    *,
    marked: bool,
) -> int:
    ids = {int(pid) for pid in product_ids if int(pid) > 0}
    if not ids:
        return 0
    marks = load_description_gpt_translation_marks()
    if marked:
        marks.update(ids)
    else:
        marks -= ids
    save_description_gpt_translation_marks(marks)
    return len(ids)


def toggle_description_gpt_translation_mark(product_id: int) -> bool:
    marks = load_description_gpt_translation_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
    save_description_gpt_translation_marks(marks)
    return marked


def load_description_sonnet_translation_marks() -> set[int]:
    """Produkty oznaczone recznie jako «tlumaczenie Sonnet»."""
    return _load_marks_file("_DESCRIPTION_SONNET_TRANSLATION_MARKS_FILE")


def save_description_sonnet_translation_marks(product_ids: set[int]) -> None:
    _save_marks_file("_DESCRIPTION_SONNET_TRANSLATION_MARKS_FILE", product_ids)


def set_description_sonnet_translation_marks_batch(
    product_ids: Iterable[int],
    *,
    marked: bool,
) -> int:
    ids = {int(pid) for pid in product_ids if int(pid) > 0}
    if not ids:
        return 0
    marks = load_description_sonnet_translation_marks()
    if marked:
        marks.update(ids)
    else:
        marks -= ids
    save_description_sonnet_translation_marks(marks)
    return len(ids)


def toggle_description_sonnet_translation_mark(product_id: int) -> bool:
    marks = load_description_sonnet_translation_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
    save_description_sonnet_translation_marks(marks)
    return marked


def load_description_from_image_marks() -> set[int]:
    """Produkty oznaczone recznie jako «opis z obrazu»."""
    return _load_marks_file("_DESCRIPTION_FROM_IMAGE_MARKS_FILE")


def save_description_from_image_marks(product_ids: set[int]) -> None:
    _save_marks_file("_DESCRIPTION_FROM_IMAGE_MARKS_FILE", product_ids)


def set_description_from_image_marks_batch(
    product_ids: Iterable[int],
    *,
    marked: bool,
) -> int:
    ids = {int(pid) for pid in product_ids if int(pid) > 0}
    if not ids:
        return 0
    marks = load_description_from_image_marks()
    if marked:
        marks.update(ids)
    else:
        marks -= ids
    save_description_from_image_marks(marks)
    return len(ids)


def toggle_description_from_image_mark(product_id: int) -> bool:
    marks = load_description_from_image_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
    save_description_from_image_marks(marks)
    return marked


def _load_do_tlumaczenia_marks_raw(path: Path) -> set[int]:
    """Wczytuje oznaczenia «do tlumaczenia» (lista product_id lub stary format per-jezyk)."""
    path = _runtime_data_file(path)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if isinstance(data, list):
        out: set[int] = set()
        for item in data:
            try:
                pid = int(item)
            except (TypeError, ValueError):
                continue
            if pid > 0:
                out.add(pid)
        return out
    if isinstance(data, dict):
        out = set()
        for key, langs in data.items():
            try:
                pid = int(key)
            except (TypeError, ValueError):
                continue
            if pid <= 0:
                continue
            if langs:
                out.add(pid)
        return out
    return set()


def load_description_do_tlumaczenia_marks() -> set[int]:
    """Produkty recznie oznaczone ptaszkiem «do tlumaczenia» (domyslnie brak)."""
    path = _runtime_data_file(_DESCRIPTION_DO_TLUMACZENIA_MARKS_FILE)
    marks = _load_do_tlumaczenia_marks_raw(path)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict) and marks:
            save_description_do_tlumaczenia_marks(marks)
    return marks


def save_description_do_tlumaczenia_marks(product_ids: set[int]) -> None:
    _save_marks_file("_DESCRIPTION_DO_TLUMACZENIA_MARKS_FILE", product_ids)


def set_description_do_tlumaczenia_mark(product_id: int, *, marked: bool) -> None:
    marks = load_description_do_tlumaczenia_marks()
    pid = int(product_id)
    if marked:
        marks.add(pid)
    else:
        marks.discard(pid)
    save_description_do_tlumaczenia_marks(marks)


def set_description_do_tlumaczenia_marks_batch(
    product_ids: Iterable[int],
    *,
    marked: bool,
) -> None:
    ids = {int(pid) for pid in product_ids if int(pid) > 0}
    if not ids:
        return
    marks = load_description_do_tlumaczenia_marks()
    if marked:
        marks.update(ids)
    else:
        marks -= ids
    save_description_do_tlumaczenia_marks(marks)


def toggle_description_do_tlumaczenia_mark(product_id: int) -> bool:
    marks = load_description_do_tlumaczenia_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
    save_description_do_tlumaczenia_marks(marks)
    return marked


def load_description_bez_16_marks() -> set[int]:
    """Produkty oznaczone recznie ptaszkiem «Bez 1-6» (bez slotow wersji 1–6 w porownywarce)."""
    return _load_marks_file("_DESCRIPTION_BEZ_16_MARKS_FILE")


def save_description_bez_16_marks(product_ids: set[int]) -> None:
    _save_marks_file("_DESCRIPTION_BEZ_16_MARKS_FILE", product_ids)


def set_description_bez_16_marks_batch(
    product_ids: Iterable[int],
    *,
    marked: bool,
) -> int:
    ids = {int(pid) for pid in product_ids if int(pid) > 0}
    if not ids:
        return 0
    marks = load_description_bez_16_marks()
    if marked:
        marks.update(ids)
    else:
        marks -= ids
    save_description_bez_16_marks(marks)
    return len(ids)


def toggle_description_bez_16_mark(product_id: int) -> bool:
    marks = load_description_bez_16_marks()
    pid = int(product_id)
    if pid in marks:
        marks.discard(pid)
        marked = False
    else:
        marks.add(pid)
        marked = True
    save_description_bez_16_marks(marks)
    return marked


_COMPARE_VERSIONS_FILE = (
    _LEGACY_DATA_DIR / "compare_versions.json"
)
COMPARE_VERSION_SLOTS = 10
COMPARE_VERSION_LABELS: tuple[str, ...] = (
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "ZO1",
    "ZO2",
    "G1",
    "G2",
)


def compare_version_label(version_idx: int) -> str:
    """Etykieta slotu wersji w porownywarce (0-based)."""
    i = max(0, min(int(version_idx), COMPARE_VERSION_SLOTS - 1))
    return COMPARE_VERSION_LABELS[i]

COMPARE_LLM_PROVIDERS: tuple[str, ...] = ("sonnet", "gemini", "gpt")
COMPARE_LLM_LABELS: dict[str, str] = {
    "sonnet": "Sonnet",
    "gemini": "Gemini",
    "gpt": "GPT",
}
COMPARE_LLM_VERSION_IDX: dict[str, int] = {
    "sonnet": 0,
    "gemini": 2,
    "gpt": 4,
}
_DESCRIPTION_COMPARE_LLM_FILE = (
    _LEGACY_DATA_DIR / "description_compare_llm.json"
)


def compare_llm_provider_index(provider: str) -> int:
    try:
        return COMPARE_LLM_PROVIDERS.index(provider)
    except ValueError:
        return 0


def compare_provider_from_index(idx: int) -> str:
    i = max(0, min(int(idx), len(COMPARE_LLM_PROVIDERS) - 1))
    return COMPARE_LLM_PROVIDERS[i]


def compare_default_version_for_provider(provider: str) -> int:
    return COMPARE_LLM_VERSION_IDX.get(provider, 0)


def load_description_compare_llm() -> str:
    """Ostatnio wybrany model LLM w oknie «Aktualizuj opis» (domyslny slot porownywarki)."""
    path = _runtime_data_file(_DESCRIPTION_COMPARE_LLM_FILE)
    if not path.is_file():
        return COMPARE_LLM_PROVIDERS[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return COMPARE_LLM_PROVIDERS[0]
    provider = data.get("provider") if isinstance(data, dict) else data
    if isinstance(provider, str) and provider in COMPARE_LLM_VERSION_IDX:
        return provider
    return COMPARE_LLM_PROVIDERS[0]


def save_description_compare_llm(provider: str) -> None:
    if provider not in COMPARE_LLM_VERSION_IDX:
        provider = COMPARE_LLM_PROVIDERS[0]
    path = _runtime_data_file(_DESCRIPTION_COMPARE_LLM_FILE, for_write=True)
    atomic_write_text(
        path,
        json.dumps({"provider": provider}, indent=2, ensure_ascii=False) + "\n",
    )


_DESCRIPTION_UPDATE_PREFS_FILE = (
    _LEGACY_DATA_DIR / "description_update_prefs.json"
)


def load_description_auto_copy_prompt() -> bool:
    """Czy po zaznaczeniu produktu auto-kopiowac prompt do nowego opisu."""
    path = _runtime_data_file(_DESCRIPTION_UPDATE_PREFS_FILE)
    if not path.is_file():
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(data, dict):
        return True
    return bool(data.get("auto_copy_prompt", True))


def save_description_auto_copy_prompt(enabled: bool) -> None:
    path = _runtime_data_file(_DESCRIPTION_UPDATE_PREFS_FILE, for_write=True)
    atomic_write_text(
        path,
        json.dumps({"auto_copy_prompt": bool(enabled)}, indent=2, ensure_ascii=False) + "\n",
    )


def _normalize_compare_slot_versions(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return [""] * COMPARE_VERSION_SLOTS
    out = [str(x) if x is not None else "" for x in raw[:COMPARE_VERSION_SLOTS]]
    while len(out) < COMPARE_VERSION_SLOTS:
        out.append("")
    return out


def load_compare_versions() -> dict[int, dict[str, Any]]:
    """Wczytuje zapisane wersje porownywarki: product_id -> locale -> bucket."""
    path = _runtime_data_file(_COMPARE_VERSIONS_FILE)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for pid_raw, locales in data.items():
        try:
            pid = int(pid_raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(locales, dict):
            continue
        out[pid] = {}
        for loc, bucket in locales.items():
            if not isinstance(bucket, dict):
                continue
            versions_in: dict[int, list[str]] = {}
            raw_versions = bucket.get("versions") or {}
            if isinstance(raw_versions, dict):
                for para_raw, slots in raw_versions.items():
                    try:
                        para_idx = int(para_raw)
                    except (TypeError, ValueError):
                        continue
                    versions_in[para_idx] = _normalize_compare_slot_versions(slots)
            working_in: dict[int, str] = {}
            raw_working = bucket.get("working") or {}
            if isinstance(raw_working, dict):
                for para_raw, text in raw_working.items():
                    try:
                        para_idx = int(para_raw)
                    except (TypeError, ValueError):
                        continue
                    if isinstance(text, str):
                        working_in[para_idx] = text
            out[pid][str(loc)] = {
                "versions": versions_in,
                "working": working_in,
            }
    return out


def save_compare_versions(store: dict[int, dict[str, Any]]) -> None:
    """Zapisuje wersje porownywarki na dysk."""
    path = _runtime_data_file(_COMPARE_VERSIONS_FILE, for_write=True)
    payload: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for pid, locales in (store or {}).items():
        try:
            pid_key = str(int(pid))
        except (TypeError, ValueError):
            continue
        if not isinstance(locales, dict):
            continue
        loc_payload: dict[str, dict[str, dict[str, Any]]] = {}
        for loc, bucket in locales.items():
            if not isinstance(bucket, dict):
                continue
            versions_out: dict[str, list[str]] = {}
            for para_idx, slots in (bucket.get("versions") or {}).items():
                versions_out[str(int(para_idx))] = _normalize_compare_slot_versions(slots)
            working_out: dict[str, str] = {}
            for para_idx, text in (bucket.get("working") or {}).items():
                if isinstance(text, str):
                    working_out[str(int(para_idx))] = text
            if versions_out or working_out:
                loc_payload[str(loc)] = {
                    "versions": versions_out,
                    "working": working_out,
                }
        if loc_payload:
            payload[pid_key] = loc_payload
    atomic_write_text(
        path,
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )


def get_compare_bucket(
    store: dict[int, dict[str, Any]],
    *,
    product_id: int,
    locale: str,
) -> dict[str, Any]:
    """Zwraca bucket {versions, working} dla produktu i jezyka (tworzy jesli brak)."""
    pid = int(product_id)
    loc = str(locale)
    if pid not in store or not isinstance(store.get(pid), dict):
        store[pid] = {}
    product_bucket = store[pid]
    if loc not in product_bucket or not isinstance(product_bucket.get(loc), dict):
        product_bucket[loc] = {"versions": {}, "working": {}}
    bucket = product_bucket[loc]
    if "versions" not in bucket or not isinstance(bucket["versions"], dict):
        bucket["versions"] = {}
    if "working" not in bucket or not isinstance(bucket["working"], dict):
        bucket["working"] = {}
    return bucket


_TRANSLATION_PROMPT_HEADER = """\
- Sklep ma rynki w 6 jezykach obcych: en (Europa/UK), de (Niemcy), fr (Francja),
  es (Hiszpania), nl (Holandia), it (Wlochy). Kazdy z tych rynkow MUSI dostac
  produkt w lokalnym jezyku.
- Dla KAZDEGO z 6 jezykow utworz osobne tlumaczenie; NATURALNIE, nie doslowne tlumaczenie - dopuszczalna
  lekka swobodna adaptacja stylistyczna; zachowaj fakty.


Tekst:
"""


def build_translation_prompt(paragraph: str) -> str:
    """Prompt LLM do tlumaczenia jednego akapitu na 6 jezykow obcych."""
    body = (paragraph or "").strip()
    return f"{_TRANSLATION_PROMPT_HEADER}{body}"


def build_translation_prompt_all(paragraphs: list[str]) -> str:
    """Prompt LLM do tlumaczenia wielu akapitow (ta sama instrukcja, numerowane bloki)."""
    shown = [p.strip() for p in paragraphs if (p or "").strip()]
    if not shown:
        raise ValueError("Brak akapitow do tlumaczenia.")
    blocks = "\n\n".join(f"--- Akapit {i} ---\n{p}" for i, p in enumerate(shown, 1))
    return (
        f"{_TRANSLATION_PROMPT_HEADER}"
        f"(tlumacz KAZDY akapit osobno; dla kazdego zwroc osobny obiekt JSON "
        f'{{"en":"...","de":"...","fr":"...","es":"...","nl":"...","it":"..."}})\n\n'
        f"{blocks}"
    )


def build_giga_translation_prompt(items: list[dict[str, Any]]) -> str:
    """Prompt LLM do tlumaczenia akapitow wielu produktow naraz (jeden schowek)."""
    if not items:
        raise ValueError("Brak pozycji do tlumaczenia.")
    blocks: list[str] = []
    for i, it in enumerate(items, 1):
        artist = (it.get("artist") or "").strip()
        title = (it.get("title") or "").strip()
        paras = [p.strip() for p in (it.get("paragraphs") or []) if (p or "").strip()]
        if not paras:
            label = f"{artist} — {title}".strip(" —") or f"pozycja {i}"
            raise ValueError(f"{label}: brak akapitow PL do tlumaczenia.")
        para_block = "\n\n".join(
            f"--- Akapit {j} ---\n{p}" for j, p in enumerate(paras, 1)
        )
        blocks.append(
            f"=== PRODUKT {i} ===\n"
            f"Artysta: {artist}\n"
            f"Tytul: {title}\n"
            f"Liczba akapitow: {len(paras)}\n\n"
            f"{para_block}"
        )
    n = len(items)
    products_block = "\n\n".join(blocks)
    return (
        f"{_TRANSLATION_PROMPT_HEADER}"
        f"Zadanie: przetlumacz opisy {n} produktow (ponizej). "
        f"Kazdy produkt ma swoje akapity po polsku — przetlumacz KAZDY akapit na 6 jezykow.\n\n"
        f"Zwroc WYLACZNIE jeden obiekt JSON (bez markdown, bez tekstu dookola) w formacie:\n"
        f'{{"produkt_1": {{"akapit_1": {{"en":"...","de":"...","fr":"...","es":"...","nl":"...","it":"..."}}, '
        f'"akapit_2": {{...}}, ...}}, "produkt_2": {{...}}, ...}}\n'
        f"- Klucze produktow: produkt_1, produkt_2, ... produkt_{n}\n"
        f"- W kazdym produkcie klucze akapitow: akapit_1, akapit_2, ... "
        f"(tyle ile akapitow w danym produkcie)\n"
        f"- W kazdym akapicie pola: en, de, fr, es, nl, it (wszystkie wymagane)\n\n"
        f"{products_block}"
    )


def build_locales_from_translation_batch(
    *,
    baseline_by_locale: dict[str, list[str]],
    translation_batch: list[dict[str, str]],
) -> dict[str, list[str]]:
    """Scala tlumaczenia akapitow z biezacymi wersjami jezykowymi (bez PL)."""
    pl_paras = baseline_by_locale.get("pl") or []
    target_len = min(_AKAPITY_MAX, max(len(pl_paras), len(translation_batch), 3))
    out: dict[str, list[str]] = {}
    for lang in TRANSLATION_LANGS:
        baseline = list(baseline_by_locale.get(lang) or [])
        paras = list(baseline)
        while len(paras) < target_len:
            paras.append("")
        for para_idx, translations in enumerate(translation_batch):
            if para_idx >= target_len:
                break
            paras[para_idx] = translations[lang]
        out[lang] = paras[:target_len]
    return out


_DESCRIPTION_LOCALES: tuple[str, ...] = ("pl",) + TRANSLATION_LANGS


def load_all_locale_paragraphs(
    *,
    product_id: int,
    full_product: dict[str, Any],
    shop: str,
    token: str,
) -> dict[str, list[str]]:
    """Akapity opisu we wszystkich wersjach jezykowych (PL + 6 obcych)."""
    return {
        loc: load_current_paragraphs(
            product_id=product_id,
            full_product=full_product,
            locale=loc,
            shop=shop,
            token=token,
        )
        for loc in _DESCRIPTION_LOCALES
    }


def build_current_translations_json(
    *,
    artist: str,
    title: str,
    paragraphs_by_locale: dict[str, list[str]],
) -> str:
    """JSON z akapitami we wszystkich wersjach jezykowych (format akapit_N + pl, en, de, ...)."""
    counts = [len(paragraphs_by_locale.get(loc) or []) for loc in _DESCRIPTION_LOCALES]
    n = min(_AKAPITY_MAX, max(counts) if counts else 0)
    if n < 1:
        raise ValueError("Brak akapitow do wyeksportowania.")
    data: dict[str, Any] = {
        "artysta": (artist or "").strip(),
        "tytul": (title or "").strip(),
        "wersja_pierwotna": "pl",
        "uwaga": (
            "Pole pl w kazdym akapicie to wersja pierwotna tekstu; "
            "pozostale klucze (en, de, fr, es, nl, it) to tlumaczenia."
        ),
    }
    for i in range(n):
        block: dict[str, str] = {}
        for loc in _DESCRIPTION_LOCALES:
            paras = paragraphs_by_locale.get(loc) or []
            if i < len(paras) and (paras[i] or "").strip():
                block[loc] = paras[i].strip()
        if block:
            data[f"akapit_{i + 1}"] = block
    if not any(str(k).startswith("akapit_") for k in data):
        raise ValueError("Brak akapitow do wyeksportowania.")
    return json.dumps(data, ensure_ascii=False, indent=2)


# key=None — naglowek sekcji (granica pola, bez wartosci).
_TITLE_CHANGE_FIELD_PATTERNS: tuple[tuple[str | None, re.Pattern[str]], ...] = (
    (
        "orig",
        re.compile(
            r"Tytu[lł]\s+oryginalny(?:\s*/\s*[^:\n]+|\s*\([^)]*\))?\s*:\s*",
            re.IGNORECASE,
        ),
    ),
    ("pl", re.compile(r"Tytu[lł]\s+polski\s*:\s*", re.IGNORECASE)),
    ("en", re.compile(r"Tytu[lł]\s+angielski(?:\s*\(\s*EN\s*\))?\s*:\s*", re.IGNORECASE)),
    (
        None,
        re.compile(r"Tytu[lł]y\s+w\s+pozostałych\s+językach\s*:\s*", re.IGNORECASE),
    ),
    ("de", re.compile(r"Tytu[lł]\s+niemiecki\s*\(\s*DE\s*\)\s*:\s*", re.IGNORECASE)),
    ("fr", re.compile(r"Tytu[lł]\s+francuski\s*\(\s*FR\s*\)\s*:\s*", re.IGNORECASE)),
    (
        "es",
        re.compile(r"Tytu[lł]\s+hiszpa[nń]ski\s*\(\s*ES\s*\)\s*:\s*", re.IGNORECASE),
    ),
    (
        "nl",
        re.compile(r"Tytu[lł]\s+niderlandzki\s*\(\s*NL\s*\)\s*:\s*", re.IGNORECASE),
    ),
    ("it", re.compile(r"Tytu[lł]\s+w[lł]oski\s*\(\s*IT\s*\)\s*:\s*", re.IGNORECASE)),
)


def parse_title_change_product_ref(text: str) -> tuple[str, str]:
    """Parsuje identyfikacje produktu: linia 1 = tytul obrazu, linia 2 = artysta."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ValueError("Wklej dwie linie: tytul obrazu, potem artysta.")
    return lines[0], lines[1]


def _find_title_change_markers(raw: str) -> list[tuple[int, int, str | None]]:
    """Wszystkie etykiety tytulow w tekscie, posortowane; bez nakladajacych sie trafien."""
    hits: list[tuple[int, int, str | None]] = []
    for key, pat in _TITLE_CHANGE_FIELD_PATTERNS:
        for m in pat.finditer(raw):
            hits.append((m.start(), m.end(), key))
    if not hits:
        return []
    hits.sort(key=lambda item: item[0])
    filtered: list[tuple[int, int, str | None]] = []
    for hit in hits:
        if filtered and hit[0] < filtered[-1][1]:
            continue
        filtered.append(hit)
    return filtered


def parse_title_change_fields(text: str) -> dict[str, str]:
    """Parsuje pola tytulow z wklejonego tekstu (krok 2 — generowanie promptu)."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Pusty tekst z tytulami.")
    hits = _find_title_change_markers(raw)
    if not hits:
        raise ValueError(
            'Nie znaleziono pol tytulow (np. "Tytul polski", "Tytul angielski", '
            '"Tytul oryginalny", "Tytul niemiecki (DE)" itd.).'
        )
    out: dict[str, str] = {}
    for i, (_start, end, key) in enumerate(hits):
        if key is None:
            continue
        val_end = hits[i + 1][0] if i + 1 < len(hits) else len(raw)
        val = raw[end:val_end].strip()
        if not val:
            raise ValueError(f"Puste pole: {key}")
        out[key] = val
    if not out:
        raise ValueError("Podaj co najmniej jeden tytul.")
    return out


_TITLE_CHANGE_PRIMARY_PROMPT: tuple[tuple[str, str], ...] = (
    ("orig", "Tytuł oryginalny"),
    ("pl", "Tytuł polski"),
    ("en", "Tytuł angielski"),
)

_TITLE_CHANGE_OTHER_LANG_PROMPT: tuple[tuple[str, str], ...] = (
    ("de", "Tytuł niemiecki (DE)"),
    ("fr", "Tytuł francuski (FR)"),
    ("es", "Tytuł hiszpański (ES)"),
    ("nl", "Tytuł niderlandzki (NL)"),
    ("it", "Tytuł włoski (IT)"),
)


_TITLE_ALTERNATIVE_CONJ: dict[str, str] = {
    "pl": "lub",
    "en": "or",
    "orig": "of",
    "de": "oder",
    "fr": "ou",
    "es": "o",
    "nl": "of",
    "it": "o",
}

# Wielkosc liter w tytulach — konwencja per jezyk (katalog muzealny / sklep):
# PL: pierwsza litera + nazwy wlasne (miejsca, osoby); reszta malymi.
# EN: title case — glowne slowa wielka litera (The Great Pool); przyimki/spojniki w srodku malymi.
# DE: rzeczowniki wielka litera, reszta malymi (Der große Teich).
# FR/ES/IT/NL/orig: sentence case — artykul na poczatku wielka, pozostale slowa zwykle malymi
# (Le grand étang, El gran estanque, Il grande stagno, De grote poel).
_TITLE_CAPITALIZATION_NOTE = (
    "Wielkosc liter zgodnie z konwencja jezyka: PL — pierwsza litera i nazwy wlasne; "
    "EN — title case; DE — rzeczowniki wielka litera; FR/ES/IT/NL — sentence case. "
    "Alternatywa w nawiasie musi byc innym tytulem obrazu — nie powtarzaj glownego "
    "tytulu bez artykulu (np. zle: «The X (or X)», «Der X (oder X)»)."
)

_ARTICLE_PREFIX_RES: dict[str, re.Pattern[str]] = {
    "en": re.compile(r"^(?:The|A|An)\s+", re.IGNORECASE),
    "de": re.compile(
        r"^(?:Der|Die|Das|Den|Dem|Des|Ein|Eine|Einen|Einem|Einer)\s+",
        re.IGNORECASE,
    ),
    "fr": re.compile(
        r"^(?:Les|Le|La|L'|Un|Une|Des|Du|De la|De)\s+",
        re.IGNORECASE,
    ),
    "es": re.compile(
        r"^(?:El|La|Los|Las|Un|Una|Unos|Unas)\s+",
        re.IGNORECASE,
    ),
    "it": re.compile(
        r"^(?:Gli|Il|Lo|La|I|Le|L'|Un|Una|Uno)\s+",
        re.IGNORECASE,
    ),
    "nl": re.compile(r"^(?:De|Het|Een)\s+", re.IGNORECASE),
    "pl": re.compile(r"^(?:Ta|Ten|To)\s+", re.IGNORECASE),
    "orig": re.compile(
        r"^(?:The|A|An|Der|Die|Das|Den|Dem|Des|Ein|Eine|Les|Le|La|L'|"
        r"El|Los|Las|Il|Lo|Gli|De|Het|Een)\s+",
        re.IGNORECASE,
    ),
}

_LUB_BARE_RE = re.compile(r"(?<!\()\s+lub\s+", re.IGNORECASE)
_CONJ_WORDS = tuple(
    sorted(set(_TITLE_ALTERNATIVE_CONJ.values()), key=len, reverse=True)
)
_NESTED_ALT_RE = re.compile(
    r"\(("
    + "|".join(re.escape(c) for c in _CONJ_WORDS)
    + r")\s+(.+?)\s+\(\1\s+(.+?)\)\)",
    re.IGNORECASE,
)


def _strip_one_leading_article(text: str, lang_key: str) -> str | None:
    """Zwraca tytul bez jednego wiodacego artykulu albo None, gdy artykulu brak."""
    pat = _ARTICLE_PREFIX_RES.get(lang_key) or _ARTICLE_PREFIX_RES["orig"]
    s = (text or "").strip()
    m = pat.match(s)
    if not m:
        return None
    return s[m.end() :].strip()


def _is_article_only_alternative(primary: str, alt: str, lang_key: str) -> bool:
    """True gdy alt to tylko primary bez wiodacego artykulu (The/Der/Le…)."""
    stripped = _strip_one_leading_article(primary, lang_key)
    if not stripped:
        return False
    return stripped.casefold() == (alt or "").strip().casefold()


_ALT_SUFFIX_RE = re.compile(
    r"^(.+?)\s+\(("
    + "|".join(re.escape(c) for c in sorted(set(_TITLE_ALTERNATIVE_CONJ.values())))
    + r")\s+(.+)\)$",
    re.IGNORECASE | re.DOTALL,
)


def _split_title_alternatives(inner: str, conj: str) -> list[str]:
    parts = [p.strip() for p in inner.split("/") if p.strip()]
    if len(parts) <= 1:
        conj_pat = re.compile(r"\s+" + re.escape(conj) + r"\s+", re.IGNORECASE)
        parts = [p.strip() for p in conj_pat.split(inner) if p.strip()]
    return parts


def drop_article_only_alternatives(title: str, lang_key: str) -> str:
    """Usuwa alternatywy bedace glownym tytulem bez artykulu («The X (or X)»)."""
    text = (title or "").strip()
    m = _ALT_SUFFIX_RE.match(text)
    if not m:
        return text
    primary, conj, inner = m.group(1).strip(), m.group(2), m.group(3).strip()
    kept = [
        alt
        for alt in _split_title_alternatives(inner, conj)
        if not _is_article_only_alternative(primary, alt, lang_key)
    ]
    if not kept:
        return primary
    if len(kept) == 1:
        return f"{primary} ({conj} {kept[0]})"
    return f"{primary} ({conj} {'/'.join(kept)})"


def collapse_nested_title_alternatives(title: str) -> str:
    """«A (lub B (lub C))» -> «A (lub B/C)» — drugi spojnik zamieniony na «/»."""
    text = (title or "").strip()
    if not text:
        return text
    while True:
        m = _NESTED_ALT_RE.search(text)
        if not m:
            break
        conj, first, second = m.group(1), m.group(2).strip(), m.group(3).strip()
        text = text[: m.start()] + f"({conj} {first}/{second})" + text[m.end() :]
    return text


def title_needs_lub_paren_fix(title: str) -> bool:
    """True gdy tytul ma «lub» poza nawiasem (np. «A lub B» zamiast «A (lub B)»)."""
    return bool(_LUB_BARE_RE.search((title or "").strip()))


def normalize_title_alternatives(title: str, lang_key: str) -> str:
    """Wszystkie gole «lub» -> «(spójnik …)» w jezyku docelowym; wielokrotnie."""
    text = (title or "").strip()
    if not text:
        return text
    conj = _TITLE_ALTERNATIVE_CONJ.get(lang_key, "lub")
    while True:
        m = _LUB_BARE_RE.search(text)
        if not m:
            break
        primary = text[: m.start()].strip()
        alt = text[m.end() :].strip()
        if not primary or not alt:
            break
        text = f"{primary} ({conj} {alt})"
    text = collapse_nested_title_alternatives(text)
    return drop_article_only_alternatives(text, lang_key)


def format_title_alternative_parenthetical(title: str, lang_key: str) -> str:
    """«A lub B» -> «A (spójnik B)» w jezyku docelowym (np. EN: or, NL: of)."""
    return normalize_title_alternatives(title, lang_key)


def _title_for_change_prompt(text: str, *, lang_key: str) -> str:
    """Tytul do promptu — bez koncowej kropki, alternatywa w nawiasie."""
    base = (text or "").strip().rstrip(".")
    return normalize_title_alternatives(base, lang_key)


def build_title_change_prompt(
    *,
    painting_title: str,
    artist: str,
    titles: dict[str, str],
) -> str:
    """Buduje prompt do zmiany tytulow produktu (do wklejenia w Cursorze)."""
    change_lines: list[str] = []
    for key, label in _TITLE_CHANGE_PRIMARY_PROMPT:
        val = _title_for_change_prompt(titles.get(key) or "", lang_key=key)
        if val:
            change_lines.append(f"{label}: {val}")
    other_lines: list[str] = []
    for key, label in _TITLE_CHANGE_OTHER_LANG_PROMPT:
        val = _title_for_change_prompt(titles.get(key) or "", lang_key=key)
        if val:
            other_lines.append(f"{label}: {val}")
    if other_lines:
        change_lines.append("Tytuły w pozostałych językach:")
        change_lines.extend(other_lines)
    if not change_lines:
        raise ValueError("Brak tytulow do wpisania w prompt.")
    return (
        "W produkcie: \n\n"
        f"{painting_title.strip()}\n"
        f"{artist.strip()}\n\n"
        "Zmień:\n"
        + "\n".join(change_lines)
        + f"\n\n{_TITLE_CAPITALIZATION_NOTE}"
    )


TITLE_EDIT_LANG_KEYS: tuple[str, ...] = (
    "orig",
    "pl",
    "en",
    "de",
    "fr",
    "es",
    "nl",
    "it",
)

TITLE_EDIT_FIELD_LABELS: dict[str, str] = {
    key: label
    for key, label in (
        *_TITLE_CHANGE_PRIMARY_PROMPT,
        *_TITLE_CHANGE_OTHER_LANG_PROMPT,
    )
}


def _primary_title_for_alt(title: str, lang_key: str = "en") -> str:
    """Glowny tytul bez alternatywy w nawiasie — do alt tekstu obrazu."""
    text = (title or "").strip()
    m = _ALT_SUFFIX_RE.match(text)
    if m:
        return m.group(1).strip()
    return text


def _apply_locale_title_fields(
    body_html: str,
    loc: str,
    *,
    original_title: str,
    locale_title: str,
) -> str:
    from .body_i18n import BODY_LABELS_I18N

    title = (locale_title or "").strip()
    if not title:
        return body_html
    labels = BODY_LABELS_I18N[loc]
    updated = body_html
    updated = set_detail_value_in_body_html(updated, labels["tytul_orig"], original_title)
    updated = set_detail_value_in_body_html(updated, labels["tytul"], title)
    updated = set_display_title_in_body_html(updated, title)
    return updated


def load_product_title_fields(product_id: int) -> dict[str, str]:
    """Tytuly obrazu ze sklepu: orig, pl, en, de, fr, es, nl, it."""
    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, product_id)
    if not prod.get("id"):
        raise sc.ShopifyError(f"Nie znaleziono produktu id={product_id}")
    body_pl = prod.get("body_html") or ""
    out: dict[str, str] = {
        "pl": extract_display_title_from_body_html(body_pl),
        "orig": extract_original_title_from_body_html(body_pl),
    }
    gid = sc.product_gid(product_id)
    for loc in TRANSLATION_LANGS:
        tr = get_translated_fields(shop, token, gid, loc)
        body = (tr.get("body_html") or "").strip()
        out[loc] = extract_display_title_from_body_html(body) if body else ""
    return out


def apply_product_title_fields(
    *,
    product_id: int,
    artist: str,
    titles: dict[str, str],
    logger: Logger = None,
) -> dict[str, Any]:
    """Zapisuje tytuly obrazu w PL i tlumaczeniach (body_html + SEO + alt)."""
    from .body_i18n import BODY_LABELS_I18N, SUPPORTED_LANGS
    from .create import build_seo, full_alt_text, preview_alt_text
    from .parser import image_ref_is_mockup, mockup_alt_text, mockup_suffixes_in_image_refs

    pl_title = (titles.get("pl") or "").strip()
    original_title = (titles.get("orig") or "").strip()
    if not pl_title:
        raise ValueError("Tytul polski nie moze byc pusty.")
    if not original_title:
        raise ValueError("Tytul oryginalny nie moze byc pusty.")

    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, product_id)
    if not prod.get("id"):
        raise sc.ShopifyError(f"Nie znaleziono produktu id={product_id}")

    pl_body = prod.get("body_html") or ""
    pl_body = set_display_title_in_body_html(pl_body, pl_title)
    pl_body = set_detail_value_in_body_html(
        pl_body, BODY_LABELS_I18N["pl"]["tytul"], pl_title,
    )
    pl_body = set_detail_value_in_body_html(
        pl_body, BODY_LABELS_I18N["pl"]["tytul_orig"], original_title,
    )

    new_product_title = f"{artist.strip()} - {pl_title}"
    title_tag, meta_desc, handle = build_seo(
        tytul=pl_title,
        artysta=artist.strip(),
        gatunek="",
        nurt="",
    )
    _log(logger, f"[tytul] PUT id={product_id}: {new_product_title}")
    sc.update_product(
        shop,
        token,
        product_id,
        {"title": new_product_title, "handle": handle, "body_html": pl_body},
    )
    sc.set_seo_metafields(
        shop, token, product_id, title_tag=title_tag, description_tag=meta_desc,
    )

    gid = sc.product_gid(product_id)
    saved_locales: list[str] = []
    for loc in SUPPORTED_LANGS:
        locale_title = (titles.get(loc) or "").strip()
        if not locale_title:
            continue
        tr = get_translated_fields(shop, token, gid, loc)
        body = (tr.get("body_html") or "").strip()
        if not body:
            _log(
                logger,
                f"[tytul] Brak body_html ({loc}) — buduje z szablonu PL.",
            )
            updated = build_locale_body_html_from_pl(
                pl_body,
                loc,
                locale_title=locale_title,
                original_title=original_title,
                artist=artist.strip(),
            )
        else:
            updated = _apply_locale_title_fields(
                body,
                loc,
                original_title=original_title,
                locale_title=locale_title,
            )
        sc.register_translations(
            shop, token, resource_gid=gid, locale=loc, fields={"body_html": updated},
        )
        saved_locales.append(loc)

    en_title = (titles.get("en") or "").strip()
    alt_en = _primary_title_for_alt(en_title) if en_title else pl_title
    for img in prod.get("images") or []:
        img_id = int(img.get("id") or 0)
        if not img_id:
            continue
        src = (img.get("src") or "").lower()
        alt_existing = img.get("alt") or ""
        if "(full)" in src or img.get("position") == 1:
            alt = full_alt_text(artist.strip(), alt_en)
        elif "(preview)" in src:
            alt = preview_alt_text(artist.strip(), alt_en)
        elif image_ref_is_mockup(src) or image_ref_is_mockup(alt_existing):
            suffixes = mockup_suffixes_in_image_refs([alt_existing, img.get("src")])
            sfx = "CZCZ" if "CZCZ" in suffixes else ("CZB" if "CZB" in suffixes else "")
            alt = mockup_alt_text(artist.strip(), alt_en, name_suffix=sfx)
        else:
            alt = f"{artist.strip()} - {alt_en}"
        sc.rest_put(
            shop,
            token,
            f"products/{product_id}/images/{img_id}.json",
            {"image": {"id": img_id, "alt": alt}},
        )

    admin_url = (
        f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"
    )
    return {
        "product_id": product_id,
        "product_title": new_product_title,
        "pl_title": pl_title,
        "saved_locales": saved_locales,
        "admin_url": admin_url,
    }


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_AKAPIT_KEY_RE = re.compile(r"^akapit[_\s-]?(\d+)$", re.IGNORECASE)
_PRODUKT_KEY_RE = re.compile(r"^produkt[_\s-]?(\d+)$", re.IGNORECASE)


def _prepare_json_raw(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Pusty JSON.")
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw.strip())
    return raw


def _scan_json_objects(raw: str) -> list[str]:
    """Skanuje kolejne obiekty { ... } w juz przygotowanym tekscie."""
    blobs: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        while i < n and raw[i] != "{":
            i += 1
        if i >= n:
            break
        start = i
        depth = 0
        in_string = False
        escape = False
        j = i
        while j < n:
            ch = raw[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        blobs.append(raw[start : j + 1])
                        i = j + 1
                        break
            j += 1
        else:
            # Niekompletny obiekt (np. cudzyslow w tekscie) — szukaj kolejnego.
            i = start + 1
    return blobs


def _repair_json_scan_text(raw: str) -> str:
    """Naprawia typowe bledy LLM przed skanowaniem wielu obiektow JSON."""
    from .prompt_builder import (
        _fix_polish_open_close_quote_pairs,
        _sanitize_control_chars_in_strings,
        _sanitize_inner_quotes,
        _sanitize_polish_ascii_quotes,
        _strip_json_trailing_commas,
    )

    return _sanitize_inner_quotes(
        _sanitize_polish_ascii_quotes(
            _sanitize_control_chars_in_strings(
                _strip_json_trailing_commas(_fix_polish_open_close_quote_pairs(raw))
            )
        )
    )


def _extract_json_objects(text: str) -> list[str]:
    """Wyciaga kolejne obiekty JSON { ... } z tekstu (np. 4 obiekty pod soba)."""
    from .prompt_builder import _fix_polish_open_close_quote_pairs

    raw = _prepare_json_raw(text)
    best: list[str] = []
    for candidate in (raw, _fix_polish_open_close_quote_pairs(raw), _repair_json_scan_text(raw)):
        blobs = _scan_json_objects(candidate)
        if len(blobs) > len(best):
            best = blobs
    return best


def _extract_json_blob(text: str) -> str:
    blobs = _extract_json_objects(text)
    if blobs:
        return blobs[0]
    raw = _prepare_json_raw(text)
    m = _JSON_OBJECT_RE.search(raw)
    return m.group(0) if m else raw


def _parse_translation_dict(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ValueError("Oczekiwany obiekt JSON z kluczami en, de, fr, es, nl, it.")
    out: dict[str, str] = {}
    missing: list[str] = []
    for lang in TRANSLATION_LANGS:
        val = data.get(lang)
        if not isinstance(val, str) or not val.strip():
            missing.append(lang)
        else:
            out[lang] = val.strip()
    if missing:
        raise ValueError(
            "Brak lub puste tlumaczenia dla jezykow: "
            + ", ".join(missing)
        )
    return out


def _parse_akapit_wrapped_translations(data: dict[str, Any]) -> list[dict[str, str]] | None:
    """Format LLM: {\"akapit_1\": {en, de, ...}, \"akapit_2\": {...}, ...}."""
    if not data:
        return None
    indexed: list[tuple[int, dict[str, Any]]] = []
    for key, val in data.items():
        if not isinstance(key, str):
            return None
        m = _AKAPIT_KEY_RE.match(key.strip())
        if not m:
            return None
        if not isinstance(val, dict):
            raise ValueError(f'Klucz "{key}": oczekiwany obiekt z tlumaczeniami.')
        indexed.append((int(m.group(1)), val))
    indexed.sort(key=lambda x: x[0])
    out: list[dict[str, str]] = []
    for num, obj in indexed:
        try:
            out.append(_parse_translation_dict(obj))
        except ValueError as exc:
            raise ValueError(f"Akapit {num}: {exc}") from exc
    return out


def _parse_one_translation_object(blob: str) -> dict[str, str]:
    from .prompt_builder import _loads_json_object_blob

    try:
        data = _loads_json_object_blob(blob)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Niepoprawny JSON: {exc}") from exc
    return _parse_translation_dict(data)


def parse_paragraph_translations_json(text: str) -> dict[str, str]:
    """Parsuje JSON {en: \"...\", de: \"...\", ...} — tlumaczenia jednego akapitu."""
    return _parse_one_translation_object(_extract_json_blob(text))


def parse_giga_translations_json(text: str) -> dict[int, list[dict[str, str]]]:
    """Parsuje JSON GIGA: {produkt_1: {akapit_1: {en,...}, ...}, produkt_2: {...}}."""
    from .prompt_builder import _loads_json_object_blob

    blob = _extract_json_blob(text)
    try:
        data = _loads_json_object_blob(blob)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Niepoprawny JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Oczekiwany obiekt JSON z kluczami produkt_1, produkt_2, ...")

    indexed: list[tuple[int, dict[str, Any]]] = []
    for key, val in data.items():
        if not isinstance(key, str):
            continue
        m = _PRODUKT_KEY_RE.match(key.strip())
        if not m:
            continue
        if not isinstance(val, dict):
            raise ValueError(f'Klucz "{key}": oczekiwany obiekt z akapitami.')
        indexed.append((int(m.group(1)), val))
    if not indexed:
        raise ValueError("Nie znaleziono kluczy produkt_1, produkt_2, ... w JSON.")

    indexed.sort(key=lambda x: x[0])
    out: dict[int, list[dict[str, str]]] = {}
    for num, obj in indexed:
        wrapped = _parse_akapit_wrapped_translations(obj)
        if wrapped is None:
            raise ValueError(
                f"Produkt {num}: oczekiwane klucze akapit_1, akapit_2, ... "
                f"z tlumaczeniami en, de, fr, es, nl, it."
            )
        if len(wrapped) > _AKAPITY_MAX:
            raise ValueError(
                f"Produkt {num}: maksymalnie {_AKAPITY_MAX} akapitow (jest {len(wrapped)})."
            )
        out[num] = wrapped
    return out


def parse_paragraph_translations_batch(text: str) -> list[dict[str, str]]:
    """Parsuje jeden lub wiecej obiektow JSON — kazdy obiekt = tlumaczenia jednego akapitu.

    Obslugiwane formaty:
    - kilka obiektow {en, de, ...} pod soba;
    - jeden obiekt {akapit_1: {en, ...}, akapit_2: {...}, ...}.
    """
    blobs = _extract_json_objects(text)
    if not blobs:
        blob = _extract_json_blob(text).strip()
        if not blob.startswith("{"):
            raise ValueError("Nie znaleziono obiektu JSON.")
        blobs = [blob]

    if len(blobs) == 1:
        from .prompt_builder import _loads_json_object_blob

        try:
            data = _loads_json_object_blob(blobs[0])
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Niepoprawny JSON: {exc}") from exc
        if isinstance(data, dict):
            wrapped = _parse_akapit_wrapped_translations(data)
            if wrapped is not None:
                if len(wrapped) > _AKAPITY_MAX:
                    raise ValueError(
                        f"Maksymalnie {_AKAPITY_MAX} akapitow (jest {len(wrapped)})."
                    )
                return wrapped

    out: list[dict[str, str]] = []
    for i, blob in enumerate(blobs[:_AKAPITY_MAX], start=1):
        try:
            out.append(_parse_one_translation_object(blob))
        except ValueError as exc:
            raise ValueError(f"Akapit {i}: {exc}") from exc
    if len(blobs) > _AKAPITY_MAX:
        raise ValueError(f"Maksymalnie {_AKAPITY_MAX} obiektow JSON (jest {len(blobs)}).")
    return out


def parse_full_akapity_json(text: str) -> list[str]:
    """Parsuje JSON z pelna lista akapitow: {\"akapity\": [\"...\", ...]}."""
    blob = _extract_json_blob(text)
    try:
        from .prompt_builder import _loads_json_object_blob

        data = _loads_json_object_blob(blob)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Niepoprawny JSON: {exc}") from exc
    akapity: Any
    if isinstance(data, dict):
        akapity = data.get("akapity")
    elif isinstance(data, list):
        akapity = data
    else:
        raise ValueError('Oczekiwany obiekt {"akapity": [...]} lub tablica stringow.')
    if not isinstance(akapity, list):
        raise ValueError('Pole "akapity" musi byc lista stringow.')
    cleaned = [a.strip() for a in akapity if isinstance(a, str) and a.strip()]
    if len(cleaned) < 3:
        raise ValueError(f"Minimum 3 akapity (jest {len(cleaned)}).")
    if len(cleaned) > _AKAPITY_MAX:
        cleaned = cleaned[:_AKAPITY_MAX]
    return cleaned


def _log(logger: Logger, msg: str) -> None:
    if logger:
        logger(msg)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _filename_tail(name: str) -> str:
    return (name or "").strip().split("/")[-1].split("?")[0].lower()


def merge_paragraphs(
    existing: list[str],
    new: list[str],
    mode: UpdateMode,
    *,
    paragraph_index: int = 0,
) -> list[str]:
    """Scala akapity wedlug trybu aktualizacji."""
    ex = [a.strip() for a in existing if (a or "").strip()]
    nw = [a.strip() for a in new if (a or "").strip()]
    if mode == "replace_all":
        merged = nw
    elif mode == "replace_paragraph":
        if not nw:
            raise ValueError("Brak akapitow w JSON do podmiany.")
        idx = max(0, min(int(paragraph_index), _AKAPITY_MAX - 1))
        merged = list(ex)
        while len(merged) <= idx:
            merged.append("")
        replacement = nw[idx] if idx < len(nw) else nw[-1]
        merged[idx] = replacement
        merged = [a for a in merged if a.strip()]
    elif mode == "add_paragraph":
        if not nw:
            raise ValueError("Brak akapitow w JSON do dodania.")
        if len(nw) > len(ex):
            merged = ex + nw[len(ex) :]
        elif len(nw) == len(ex) + 1:
            merged = ex + [nw[-1]]
        else:
            extra = [p for p in nw if _norm(p) not in {_norm(x) for x in ex}]
            merged = ex + extra
    else:
        raise ValueError(f"Nieznany tryb: {mode}")
    if len(merged) < 3:
        raise ValueError(f"Po scaleniu musza zostac min. 3 akapity (jest {len(merged)}).")
    if len(merged) > _AKAPITY_MAX:
        raise ValueError(f"Maksymalnie {_AKAPITY_MAX} akapity (jest {len(merged)}).")
    return merged


def get_translated_fields(shop: str, token: str, product_gid: str, locale: str) -> dict[str, str]:
    """Pola przetlumaczone w Shopify (np. body_html, title) dla danego locale."""
    query = """
    query($id: ID!, $locale: String!) {
      translatableResource(resourceId: $id) {
        translations(locale: $locale) { key value }
      }
    }
    """
    try:
        data = sc.graphql(shop, token, query, {"id": product_gid, "locale": locale})
    except sc.ShopifyError:
        return {}
    res = (data or {}).get("translatableResource") or {}
    out: dict[str, str] = {}
    for t in res.get("translations") or []:
        k = (t or {}).get("key")
        v = (t or {}).get("value")
        if k and v is not None:
            out[str(k)] = str(v)
    return out


def artist_sort_index_value(row: dict[str, Any]) -> int:
    """Indeks artysty z menu (0 = pierwszy w katalogu). Nie traktuj 0 jako brak."""
    raw = row.get("artist_sort_index")
    if raw is None:
        return 999_999
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 999_999


def product_catalog_sort_key(row: dict[str, Any]) -> tuple:
    """Sortowanie A-Z po nazwisku (z katalogu/menu), potem imie i tytul obrazu."""
    return (
        (row.get("surname") or "\uffff").lower(),
        (row.get("firstname") or "").lower(),
        (row.get("painting_title") or "").lower(),
    )


def _match_artist_catalog_entry(
    artist: str,
    catalog_order: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Dopasowuje artyste produktu do pozycji menu katalogu (Nazwisko, Imie)."""
    artist_norm = (artist or "").strip().lower()
    if not artist_norm or not catalog_order:
        return None
    guessed = artist_collection_title(artist).strip()
    guessed_lower = guessed.lower()
    by_title = {
        (e.get("collection_title") or "").strip().lower(): e for e in catalog_order
    }
    if guessed_lower in by_title:
        return by_title[guessed_lower]
    for entry in catalog_order:
        title = (entry.get("collection_title") or "").strip()
        if collection_title_matches_expected(title, guessed):
            return entry
    by_display = {
        artist_display_from_catalog_title(e.get("collection_title") or "").strip().lower(): e
        for e in catalog_order
    }
    hit = by_display.get(artist_norm)
    if hit:
        return hit
    artist_tokens = frozenset(artist_norm.replace("-", " ").split())
    if len(artist_tokens) >= 2:
        for entry in catalog_order:
            title = (entry.get("collection_title") or "").strip()
            display = artist_display_from_catalog_title(title).strip().lower()
            if display and frozenset(display.replace("-", " ").split()) == artist_tokens:
                return entry
    return None


def load_product_catalog_rows(
    *,
    logger: Logger = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Lista produktow typu Obraz do wyboru w oknie aktualizacji opisu."""
    shop, token = sc.load_session()
    if on_progress:
        on_progress("Pobieram kolejnosc artystow z menu...")
    catalog_order = sc.fetch_artist_catalog_order(shop, token)
    if on_progress:
        on_progress("Pobieram produkty...")
    products = sc.fetch_all_products(
        shop,
        token,
        product_type=PRODUCT_TYPE,
        fields="id,title,handle,vendor,image",
        should_cancel=should_cancel,
        on_page_progress=lambda n: on_progress(f"Produkty: {n}") if on_progress else None,
    )
    rows: list[dict[str, Any]] = []
    for prod in products:
        pid = int(prod.get("id") or 0)
        if not pid:
            continue
        title_full = (prod.get("title") or "").strip()
        artist, painting_title = _split_artist_title(title_full, prod.get("vendor"))
        catalog_entry = _match_artist_catalog_entry(artist, catalog_order)
        if catalog_entry:
            catalog_title = (catalog_entry.get("collection_title") or "").strip()
            artist_sort_index = int(catalog_entry.get("sort_index") or 0)
            surname, firstname = parse_artist_catalog_title(catalog_title)
        else:
            catalog_title = artist_collection_title(artist)
            artist_sort_index = 999_999
            surname, firstname = parse_artist_catalog_title(catalog_title)
            if not firstname and artist:
                parts = artist.split()
                surname = parts[-1] if parts else artist
                firstname = " ".join(parts[:-1]) if len(parts) > 1 else ""
        image = prod.get("image") or {}
        src = (image.get("src") or "").strip()
        image_filename = src.rsplit("/", 1)[-1].split("?", 1)[0] if src else ""
        rows.append(
            {
                "product_id": pid,
                "product_title": title_full,
                "artist": artist,
                "artist_catalog_title": catalog_title,
                "artist_sort_index": artist_sort_index,
                "surname": surname,
                "firstname": firstname,
                "painting_title": painting_title,
                "handle": (prod.get("handle") or "").strip(),
                "image_src": src,
                "image_filename": image_filename,
                "admin_url": (
                    f"https://{shop.replace('.myshopify.com', '')}.myshopify.com"
                    f"/admin/products/{pid}"
                ),
            }
        )
    rows.sort(key=product_catalog_sort_key)
    _log(logger, f"[opis] Wczytano {len(rows)} produkt(ow) do listy.")
    return rows


def match_json_entry_for_product(
    product: dict[str, Any],
    llm_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Dopasowuje wpis JSON do wybranego produktu (plik, source_key, tytul)."""
    if len(llm_items) == 1:
        return llm_items[0]
    artist = (product.get("artist") or "").strip()
    painting = (product.get("painting_title") or "").strip()
    image_fn = _filename_tail(product.get("image_filename") or "")
    src_key = compute_source_key(artist, painting) if artist and painting else ""

    best: dict[str, Any] | None = None
    best_score = -1

    for item in llm_items:
        plik = (item.get("plik") or "").strip()
        score = 0
        if plik and image_fn and _filename_tail(plik) == image_fn:
            score = 100
        else:
            try:
                a2, t2 = parse_filename(plik)
            except ValueError:
                a2, t2 = "", ""
            if a2 and t2:
                if compute_source_key(a2, t2) == src_key and src_key:
                    score = max(score, 90)
                canon = _filename_tail(canonical_product_filename(a2, t2, suffix=".webp"))
                if canon and image_fn and canon == image_fn:
                    score = max(score, 85)
                if _norm(a2) == _norm(artist) and _norm(t2) == _norm(painting):
                    score = max(score, 80)
        tytul_pl = (item.get("tytul_polski") or "").strip()
        if tytul_pl and painting and _norm(tytul_pl) == _norm(painting):
            score = max(score, 70)
        if score > best_score:
            best_score = score
            best = item

    return best if best_score >= 70 else None


def _lifespan_for_artist(shop: str, token: str, artist: str) -> str:
    coll_title = artist_collection_title(artist)
    collection = sc.find_artist_collection(shop, token, coll_title)
    return (collection or {}).get("lifespan") or "" if collection else ""


def _facts_for_locale(
    llm_item: dict[str, Any],
    lang: str,
    *,
    artist: str,
    painting_pl: str,
    original_title: str,
    lifespan: str,
) -> dict[str, str]:
    block = (llm_item.get("tlumaczenia") or {}).get(lang) or {}
    pl = llm_item

    def field(key: str, pl_key: str | None = None) -> str:
        pk = pl_key or key
        if lang == "pl":
            return (pl.get(pk) or "").strip()
        v = (block.get(pk) or "").strip()
        if v:
            return v
        return translate_field_value_or_pl((pl.get(pk) or "").strip(), lang)

    return {
        "tytul_obrazu": (
            (pl.get("tytul_polski") or "").strip()
            if lang == "pl"
            else (block.get("tytul_polski") or painting_pl or "").strip()
        ),
        "artysta": artist,
        "data": lifespan,
        "tytul_orginalny": (pl.get("tytul_orginalny") or original_title or "").strip(),
        "data_powstania": field("data_powstania"),
        "miejsce_powstania": field("miejsce_powstania"),
        "technika": field("technika"),
        "gatunek": field("gatunek"),
        "nurt": field("nurt"),
        "forma": field("forma"),
    }


def load_current_paragraphs(
    *,
    product_id: int,
    full_product: dict[str, Any],
    locale: str,
    shop: str,
    token: str,
) -> list[str]:
    """Akapity opisu aktualnie w Shopify (PL z body_html, obce z Translations API)."""
    if locale == "pl":
        body = (full_product.get("body_html") or "").strip()
    else:
        gid = sc.product_gid(product_id)
        tr = get_translated_fields(shop, token, gid, locale)
        body = (tr.get("body_html") or "").strip()
    return extract_paragraphs_from_body_html(body)


def normalize_paragraphs_for_save(
    paragraphs: Iterable[str],
    *,
    locale: str = "",
) -> list[str]:
    """Zachowuje pozycje akapitow; wymaga min. 3 niepustych slotow."""
    paras = [a.strip() for a in paragraphs][: _AKAPITY_MAX]
    while len(paras) > 3 and not paras[-1]:
        paras.pop()
    label = LOCALE_LABELS.get(locale, locale) if locale else "Opis"
    if len(paras) < 3:
        raise ValueError(f"{label}: co najmniej 3 akapity (jest {len(paras)}).")
    if sum(1 for p in paras if p) < 3:
        raise ValueError(f"{label}: co najmniej 3 niepuste akapity.")
    if len(paras) > _AKAPITY_MAX:
        raise ValueError(f"{label}: maks. {_AKAPITY_MAX} akapity.")
    return paras


def apply_current_paragraphs_update(
    *,
    product_id: int,
    locale: str,
    paragraphs: list[str],
    logger: Logger = None,
) -> dict[str, Any]:
    """Zapisuje recznie edytowane akapity obecnego opisu (bez JSON LLM)."""
    paras = normalize_paragraphs_for_save(paragraphs, locale=locale)

    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, product_id)
    if not prod:
        raise sc.ShopifyError(f"Nie znaleziono produktu id={product_id}")

    if locale == "pl":
        body = (prod.get("body_html") or "").strip()
        if not body:
            raise ValueError("Produkt nie ma body_html — nie mozna zaktualizowac akapitow.")
        new_body = replace_paragraphs_in_body_html(body, paras)
        _log(logger, f"[opis] PUT body_html (reczna edycja) id={product_id}, {len(paras)} akapitow.")
        sc.update_product(shop, token, product_id, {"body_html": new_body})
    else:
        gid = sc.product_gid(product_id)
        tr = get_translated_fields(shop, token, gid, locale)
        body = (tr.get("body_html") or "").strip()
        if not body:
            body = (prod.get("body_html") or "").strip()
        if not body:
            raise ValueError(
                f"Brak body_html dla {LOCALE_LABELS.get(locale, locale)} — "
                "najpierw dodaj tlumaczenie opisu."
            )
        new_body = replace_paragraphs_in_body_html(body, paras)
        _log(
            logger,
            f"[opis] translationsRegister body_html ({locale}) id={product_id}, "
            f"{len(paras)} akapitow.",
        )
        sc.register_translations(
            shop,
            token,
            resource_gid=gid,
            locale=locale,
            fields={"body_html": new_body},
        )

    admin_url = (
        f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"
    )
    return {
        "product_id": product_id,
        "locale": locale,
        "paragraph_count": len(paras),
        "admin_url": admin_url,
    }


def apply_current_paragraphs_batch(
    *,
    product_id: int,
    locales_paragraphs: dict[str, list[str]],
    logger: Logger = None,
) -> dict[str, Any]:
    """Zapisuje recznie edytowane akapity obecnego opisu dla wielu jezykow naraz."""
    if not locales_paragraphs:
        raise ValueError("Brak wersji jezykowych do zapisania.")

    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, product_id)
    if not prod:
        raise sc.ShopifyError(f"Nie znaleziono produktu id={product_id}")

    saved: list[str] = []
    errors: list[dict[str, str]] = []

    for locale, paragraphs in locales_paragraphs.items():
        try:
            paras = normalize_paragraphs_for_save(paragraphs, locale=locale)
        except ValueError as exc:
            errors.append({"locale": locale, "error": str(exc)})
            continue
        if len(paras) > _AKAPITY_MAX:
            errors.append(
                {
                    "locale": locale,
                    "error": f"{LOCALE_LABELS.get(locale, locale)}: maks. {_AKAPITY_MAX} akapity.",
                }
            )
            continue
        try:
            if locale == "pl":
                body = (prod.get("body_html") or "").strip()
                if not body:
                    raise ValueError("Brak body_html PL.")
                new_body = replace_paragraphs_in_body_html(body, paras)
                _log(
                    logger,
                    f"[opis] PUT body_html (reczna edycja batch) id={product_id}, "
                    f"{len(paras)} akapitow PL.",
                )
                sc.update_product(shop, token, product_id, {"body_html": new_body})
                prod["body_html"] = new_body
            else:
                gid = sc.product_gid(product_id)
                tr = get_translated_fields(shop, token, gid, locale)
                body = (tr.get("body_html") or "").strip()
                if not body:
                    body = (prod.get("body_html") or "").strip()
                if not body:
                    raise ValueError("Brak body_html dla tlumaczenia.")
                new_body = replace_paragraphs_in_body_html(body, paras)
                _log(
                    logger,
                    f"[opis] translationsRegister body_html ({locale}, batch) "
                    f"id={product_id}, {len(paras)} akapitow.",
                )
                sc.register_translations(
                    shop,
                    token,
                    resource_gid=gid,
                    locale=locale,
                    fields={"body_html": new_body},
                )
            saved.append(locale)
        except Exception as exc:
            errors.append({"locale": locale, "error": str(exc)})

    if not saved:
        detail = "; ".join(f"{e['locale']}: {e['error']}" for e in errors)
        raise ValueError(detail or "Nie zapisano zadnej wersji jezykowej.")

    admin_url = (
        f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"
    )
    return {
        "product_id": product_id,
        "saved_locales": saved,
        "errors": errors,
        "admin_url": admin_url,
    }


def _new_paragraphs_source(llm_item: dict[str, Any], lang: str) -> list[str]:
    if lang == "pl":
        return [a.strip() for a in (llm_item.get("akapity") or []) if (a or "").strip()]
    block = (llm_item.get("tlumaczenia") or {}).get(lang) or {}
    tr_ak = block.get("akapity")
    if isinstance(tr_ak, list) and [a for a in tr_ak if (a or "").strip()]:
        return [a.strip() for a in tr_ak if (a or "").strip()]
    return [a.strip() for a in (llm_item.get("akapity") or []) if (a or "").strip()]


def compute_locale_preview(
    *,
    product: dict[str, Any],
    full_product: dict[str, Any],
    llm_item: dict[str, Any],
    mode: UpdateMode,
    paragraph_index: int,
    locale: str,
    shop: str,
    token: str,
) -> dict[str, Any]:
    """Podglad zmian dla jednego jezyka: stare/nowe akapity i indeksy zmian."""
    artist = (product.get("artist") or "").strip()
    painting = (product.get("painting_title") or "").strip()
    original_title = (llm_item.get("tytul_orginalny") or "").strip()
    lifespan = _lifespan_for_artist(shop, token, artist)

    body_pl = (full_product.get("body_html") or "").strip()
    if locale == "pl":
        old_paragraphs = extract_paragraphs_from_body_html(body_pl)
    else:
        gid = sc.product_gid(int(product["product_id"]))
        tr = get_translated_fields(shop, token, gid, locale)
        old_paragraphs = extract_paragraphs_from_body_html(tr.get("body_html") or "")

    new_src = _new_paragraphs_source(llm_item, locale)
    new_paragraphs = merge_paragraphs(
        old_paragraphs, new_src, mode, paragraph_index=paragraph_index
    )

    changed: list[int] = []
    for i, (o, n) in enumerate(
        zip(
            old_paragraphs + [""] * _AKAPITY_MAX,
            new_paragraphs + [""] * _AKAPITY_MAX,
        )
    ):
        if i >= _AKAPITY_MAX:
            break
        if _norm(o) != _norm(n) and (o.strip() or n.strip()):
            changed.append(i)

    if mode == "add_paragraph" and len(new_paragraphs) > len(old_paragraphs):
        for i in range(len(old_paragraphs), len(new_paragraphs)):
            if i not in changed:
                changed.append(i)

    facts = _facts_for_locale(
        llm_item,
        locale,
        artist=artist,
        painting_pl=(llm_item.get("tytul_polski") or painting).strip(),
        original_title=original_title,
        lifespan=lifespan,
    )
    new_body_html = build_body_html(akapity=new_paragraphs, lang=locale, **facts)

    return {
        "locale": locale,
        "locale_label": LOCALE_LABELS.get(locale, locale),
        "old_paragraphs": old_paragraphs,
        "new_paragraphs": list(new_paragraphs),
        "changed_indices": sorted(set(changed)),
        "new_body_html": new_body_html,
    }


def apply_description_update(
    *,
    product_id: int,
    product: dict[str, Any],
    llm_item: dict[str, Any],
    mode: UpdateMode,
    paragraph_index: int = 0,
    locales: dict[str, list[str]] | None = None,
    logger: Logger = None,
) -> dict[str, Any]:
    """Zapisuje zaktualizowany opis (PL REST + tlumaczenia). locales: nadpisania akapitow per jezyk."""
    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, product_id)
    if not prod:
        raise sc.ShopifyError(f"Nie znaleziono produktu id={product_id}")

    artist = (product.get("artist") or "").strip()
    painting = (product.get("painting_title") or "").strip()
    original_title = (llm_item.get("tytul_orginalny") or "").strip()
    lifespan = _lifespan_for_artist(shop, token, artist)

    old_pl = extract_paragraphs_from_body_html(prod.get("body_html") or "")
    new_pl_src = [a.strip() for a in (llm_item.get("akapity") or []) if (a or "").strip()]
    merged_pl = merge_paragraphs(old_pl, new_pl_src, mode, paragraph_index=paragraph_index)
    if locales and "pl" in locales:
        merged_pl = [a.strip() for a in locales["pl"] if (a or "").strip()]
        if len(merged_pl) < 3:
            raise ValueError("Polska wersja musi miec co najmniej 3 akapity.")

    facts_pl = _facts_for_locale(
        llm_item,
        "pl",
        artist=artist,
        painting_pl=(llm_item.get("tytul_polski") or painting).strip(),
        original_title=original_title,
        lifespan=lifespan,
    )
    body_html = build_body_html(akapity=merged_pl, lang="pl", **facts_pl)
    _log(logger, f"[opis] PUT body_html produkt id={product_id} ({len(merged_pl)} akapitow).")
    sc.update_product(shop, token, product_id, {"body_html": body_html})

    translations = dict(llm_item.get("tlumaczenia") or {})
    translations_pushed = False
    pushed_locales: list[str] = []
    if translations:
        adjusted: dict[str, dict[str, Any]] = {}
        for lang in TRANSLATION_LANGS:
            block = dict(translations.get(lang) or {})
            if locales and lang in locales:
                paras = [a.strip() for a in locales[lang] if (a or "").strip()]
            else:
                old_lang_body = ""
                if lang != "pl":
                    gid = sc.product_gid(product_id)
                    tr = get_translated_fields(shop, token, gid, lang)
                    old_lang_body = tr.get("body_html") or ""
                old_lang = (
                    extract_paragraphs_from_body_html(old_lang_body)
                    if old_lang_body
                    else old_pl
                )
                src = block.get("akapity") or new_pl_src
                if not isinstance(src, list):
                    src = new_pl_src
                src_clean = [a.strip() for a in src if (a or "").strip()]
                paras = merge_paragraphs(old_lang, src_clean, mode, paragraph_index=paragraph_index)
            if len(paras) >= 3:
                block["akapity"] = paras
                adjusted[lang] = block
        if adjusted:
            push_product_translations(
                product_id=product_id,
                artist=artist,
                translations=adjusted,
                paragraphs_pl=merged_pl,
                original_title=original_title,
                data_powstania=llm_item.get("data_powstania", ""),
                miejsce_powstania=llm_item.get("miejsce_powstania", ""),
                technika=llm_item.get("technika", ""),
                gatunek=llm_item.get("gatunek", ""),
                nurt=llm_item.get("nurt", ""),
                forma=llm_item.get("forma", ""),
                lifespan=lifespan,
                logger=logger,
            )
            translations_pushed = True
            pushed_locales = sorted(adjusted.keys())

    admin_url = (
        f"https://{shop.replace('.myshopify.com', '')}.myshopify.com/admin/products/{product_id}"
    )
    return {
        "product_id": product_id,
        "admin_url": admin_url,
        "paragraph_count": len(merged_pl),
        "mode": mode,
        "translations_pushed": translations_pushed,
        "saved_locales": ["pl", *pushed_locales],
    }
