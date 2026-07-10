"""Skróty klawiszowe GicleeApp — wspólne dla klasycznego launchera i Studio."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from typing import Mapping


DEFAULT_LAUNCHER_SHORTCUTS: dict[str, str] = {
    "i": "integracjagpt",
}

# Zgodność wsteczna dla klasycznego launchera i Studio.
# Dwupoziomowy launcher korzysta z konfiguracji ładowanej z JSON-a.
LAUNCHER_KEY_SHORTCUTS: dict[str, str] = dict(DEFAULT_LAUNCHER_SHORTCUTS)


def _shortcuts_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "launcher_shortcuts.json"


def normalize_shortcut_key(value: str) -> str | None:
    """Normalizuje bezpośredni skrót: litera, cyfra albo F1–F12."""

    raw = str(value or "").strip().lower()
    if len(raw) == 1 and raw.isalnum():
        return raw
    if raw.startswith("f") and raw[1:].isdigit():
        number = int(raw[1:])
        if 1 <= number <= 12:
            return f"f{number}"
    return None


def shortcut_key_from_event(event: tk.Event) -> str | None:
    ch = event.char or ""
    normalized = normalize_shortcut_key(ch)
    if normalized is not None:
        return normalized
    return normalize_shortcut_key(event.keysym or "")


def shortcut_display_label(key: str) -> str:
    normalized = normalize_shortcut_key(key)
    if normalized is None:
        return ""
    return normalized.upper()


def load_launcher_shortcuts(path: Path | None = None) -> dict[str, str]:
    """Ładuje skróty; brak lub uszkodzony plik przywraca domyślne mapowanie."""

    config_path = path or _shortcuts_path()
    if not config_path.is_file():
        return dict(DEFAULT_LAUNCHER_SHORTCUTS)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return dict(DEFAULT_LAUNCHER_SHORTCUTS)

    if not isinstance(data, dict):
        return dict(DEFAULT_LAUNCHER_SHORTCUTS)
    raw = data.get("shortcuts")
    if not isinstance(raw, dict):
        # Toleruj prosty historyczny format {"i": "integracjagpt"}.
        raw = data

    result: dict[str, str] = {}
    for key, folder in raw.items():
        normalized = normalize_shortcut_key(str(key))
        folder_name = str(folder or "").strip()
        if normalized is None or not folder_name:
            continue
        result[normalized] = folder_name
    return result


def save_launcher_shortcuts(
    shortcuts: Mapping[str, str],
    path: Path | None = None,
) -> None:
    """Zapisuje konfigurację atomowo w `giclee_app/data/launcher_shortcuts.json`."""

    config_path = path or _shortcuts_path()
    clean: dict[str, str] = {}
    for key, folder in shortcuts.items():
        normalized = normalize_shortcut_key(str(key))
        folder_name = str(folder or "").strip()
        if normalized is None or not folder_name:
            continue
        clean[normalized] = folder_name

    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = config_path.with_name(f"{config_path.name}.tmp")
    tmp_path.write_text(
        json.dumps(
            {
                "version": 1,
                "shortcuts": dict(sorted(clean.items())),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(config_path)


def assign_component_shortcut(
    shortcuts: Mapping[str, str],
    key: str,
    folder_name: str,
) -> dict[str, str]:
    """Przypisuje jeden klawisz do komponentu, usuwając wcześniejsze konflikty."""

    normalized = normalize_shortcut_key(key)
    folder = str(folder_name or "").strip()
    if normalized is None or not folder:
        raise ValueError("Nieprawidłowy skrót lub komponent")

    result = {
        existing_key: existing_folder
        for existing_key, existing_folder in shortcuts.items()
        if existing_folder != folder and existing_key != normalized
    }
    result[normalized] = folder
    return result


def remove_component_shortcut(
    shortcuts: Mapping[str, str],
    folder_name: str,
) -> dict[str, str]:
    folder = str(folder_name or "").strip()
    return {
        key: existing_folder
        for key, existing_folder in shortcuts.items()
        if existing_folder != folder
    }


def shortcut_for_component(shortcuts: Mapping[str, str], folder_name: str) -> str | None:
    folder = str(folder_name or "").strip()
    for key, existing_folder in shortcuts.items():
        if existing_folder == folder:
            return key
    return None


def focus_blocks_shortcuts(root: tk.Misc) -> bool:
    """True gdy fokus jest w polu tekstowym (nie uruchamiaj skrótu)."""
    focus = root.focus_get()
    if focus is None:
        return False
    widget: tk.Misc | None = focus
    for _ in range(12):
        if widget is None:
            break
        try:
            cls = widget.winfo_class().lower()
        except tk.TclError:
            break
        if "entry" in cls or "text" in cls or "combobox" in cls:
            return True
        try:
            widget = widget.master
        except (AttributeError, tk.TclError):
            break
    return False


def dialog_blocks_shortcuts(root: tk.Misc) -> bool:
    """True gdy fokus jest w osobnym oknie dialogowym (Toplevel)."""
    focus = root.focus_get()
    if focus is None:
        return False
    cur: tk.Misc | None = focus
    while cur is not None:
        if isinstance(cur, tk.Toplevel) and cur != root:
            return True
        cur = cur.master  # type: ignore[assignment]
    return False
