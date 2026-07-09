"""Import XLSX → JSON (dev/maintenance). Runtime nie wymaga openpyxl."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from .data_loader import data_dir, slugify
from .prompt_builder import full_prompt_for_modes, short_prompt_for_modes

try:
    import openpyxl
except ImportError as exc:  # pragma: no cover
    openpyxl = None  # type: ignore[assignment]
    _IMPORT_ERR = exc
else:
    _IMPORT_ERR = None

_CATEGORY_BY_NAME: dict[str, str] = {
    "GUI / UI Premium": "UI",
    "Motion Director": "Motion",
    "Cursor Prompt Architect": "Cursor",
    "Code-aware Reviewer": "Cursor",
    "Shopify Snapshot Reviewer": "Shopify",
    "GicleeApp Architect": "GicleeApp",
    "Performance / Debug": "Performance",
    "Writer / Copy Premium": "Copy",
    "Veo / Flow / Image Prompt": "AI Prompt",
    "Medyczny ostrożny": "Medical",
}

_SHORT_LABEL_BY_NAME: dict[str, str] = {
    "GUI / UI Premium": "GUI Premium",
    "Motion Director": "Motion Director",
    "Cursor Prompt Architect": "Cursor Architect",
    "Code-aware Reviewer": "Code-aware Reviewer",
    "Shopify Snapshot Reviewer": "Shopify Snapshot Reviewer",
    "GicleeApp Architect": "GicleeApp Architect",
    "Performance / Debug": "Performance",
    "Writer / Copy Premium": "Copy Premium",
    "Veo / Flow / Image Prompt": "Veo Premium",
    "Medyczny ostrożny": "Medyczny ostrożny",
}

_EXTRA_ALIASES: dict[str, list[str]] = {
    "GUI / UI Premium": ["GUI Premium", "GUI / UI Premium"],
    "Cursor Prompt Architect": ["Cursor Architect", "Cursor Prompt Architect"],
    "Performance / Debug": ["Performance", "Performance / Debug"],
    "Writer / Copy Premium": ["Copy Premium", "Writer / Copy Premium"],
    "Veo / Flow / Image Prompt": ["Veo Premium", "Veo / Flow / Image Prompt"],
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _default_source_path() -> Path:
    return data_dir() / "source" / "tryby_pracy_chatgpt_giclee_art.xlsx"


def _build_search_text(*parts: str) -> str:
    return " ".join(p for p in parts if p)


def _aliases_for_mode(name: str) -> list[str]:
    extras = list(_EXTRA_ALIASES.get(name, []))
    short = _SHORT_LABEL_BY_NAME.get(name, name)
    out: list[str] = []
    for candidate in [short, name, *extras]:
        c = _norm(candidate)
        if c and c not in out:
            out.append(c)
    return out


def _parse_modes_sheet(ws: Any) -> list[dict[str, Any]]:
    modes: list[dict[str, Any]] = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        number = row[0]
        name = _norm(row[1])
        if not name or number is None:
            continue
        purpose = _norm(row[2])
        focus = _norm(row[3])
        when_to_use = _norm(row[4])
        sample_command = _norm(row[5])
        simplest = _norm(row[6])
        aliases = _aliases_for_mode(name)
        modes.append(
            {
                "id": slugify(name),
                "number": int(number),
                "name": name,
                "aliases": aliases,
                "category": _CATEGORY_BY_NAME.get(name, "Inne"),
                "purpose": purpose,
                "focus": focus,
                "when_to_use": when_to_use,
                "sample_command": sample_command,
                "simplest": simplest,
                "search_text": _build_search_text(
                    name,
                    *aliases,
                    purpose,
                    focus,
                    when_to_use,
                    simplest,
                    _CATEGORY_BY_NAME.get(name, ""),
                ),
            }
        )
    return modes


def _alias_lookup(modes: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for mode in modes:
        mode_id = mode["id"]
        keys = {mode["name"], *mode.get("aliases", [])}
        for key in keys:
            k = _norm(key)
            if k:
                lookup[k.casefold()] = mode_id
    return lookup


def _resolve_mode_ids(part: str, lookup: dict[str, str]) -> str | None:
    key = _norm(part).casefold()
    if key in lookup:
        return lookup[key]
    # fuzzy: strip common prefixes
    for prefix in ("tryb ",):
        if key.startswith(prefix):
            trimmed = key[len(prefix):].strip()
            if trimmed in lookup:
                return lookup[trimmed]
    return None


def _split_combination_name(name: str) -> list[str]:
    return [_norm(p) for p in name.split(" + ") if _norm(p)]


def _parse_combinations_sheet(ws: Any, modes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = _alias_lookup(modes)
    by_id = {m["id"]: m for m in modes}
    combinations: list[dict[str, Any]] = []
    for row in ws.iter_rows(min_row=4, values_only=True):
        name = _norm(row[0])
        if not name or name.casefold() == "kombinacja":
            continue
        best_for = _norm(row[1])
        delivers = _norm(row[2])
        usage_example = _norm(row[3])
        note = _norm(row[4])
        parts = _split_combination_name(name)
        mode_ids: list[str] = []
        missing: list[str] = []
        for part in parts:
            resolved = _resolve_mode_ids(part, lookup)
            if resolved:
                if resolved not in mode_ids:
                    mode_ids.append(resolved)
            else:
                missing.append(part)
        if missing:
            raise ValueError(
                f"Nie rozpoznano trybów w kombinacji «{name}»: {', '.join(missing)}"
            )
        mode_objs = [by_id[mid] for mid in mode_ids]
        prompt_short = short_prompt_for_modes(
            [_mode_dict_to_prompt_mode(m) for m in mode_objs]
        )
        prompt_full = full_prompt_for_modes(
            [_mode_dict_to_prompt_mode(m) for m in mode_objs]
        )
        if usage_example:
            prompt_full = (
                f"{prompt_full}\n\nPrzykład użycia:\n{usage_example}"
            )
        combinations.append(
            {
                "id": slugify(name)[:80],
                "name": name,
                "mode_ids": mode_ids,
                "best_for": best_for,
                "delivers": delivers,
                "usage_example": usage_example,
                "note": note,
                "prompt_short": prompt_short,
                "prompt_full": prompt_full,
            }
        )
    return combinations


class _PromptMode:
    """Minimal adapter for prompt_builder during import."""

    def __init__(self, row: dict[str, Any]) -> None:
        self.short_label = row["aliases"][0] if row.get("aliases") else row["name"]
        self.purpose = row["purpose"]
        self.sample_command = row["sample_command"]


def _mode_dict_to_prompt_mode(row: dict[str, Any]) -> _PromptMode:
    return _PromptMode(row)


def import_from_xlsx(source: str | Path | None = None) -> dict[str, int]:
    if openpyxl is None:
        raise RuntimeError(
            "Brak biblioteki openpyxl — zainstaluj: pip install openpyxl"
        ) from _IMPORT_ERR

    path = Path(source) if source else _default_source_path()
    if not path.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku: {path}")

    wb = openpyxl.load_workbook(path, data_only=True)
    if "Tryby pracy" not in wb.sheetnames:
        raise ValueError("Brak arkusza «Tryby pracy»")
    if "Kombinacje" not in wb.sheetnames:
        raise ValueError("Brak arkusza «Kombinacje»")

    modes = _parse_modes_sheet(wb["Tryby pracy"])
    combinations = _parse_combinations_sheet(wb["Kombinacje"], modes)

    out_dir = data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    modes_payload = {
        "version": 1,
        "source": path.name,
        "modes": modes,
    }
    combos_payload = {
        "version": 1,
        "source": path.name,
        "combinations": combinations,
    }

    modes_path = out_dir / "work_modes.json"
    combos_path = out_dir / "combinations.json"
    modes_path.write_text(
        json.dumps(modes_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    combos_path.write_text(
        json.dumps(combos_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"modes": len(modes), "combinations": len(combinations)}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    source = args[0] if args else None
    stats = import_from_xlsx(source)
    print(
        f"Zaimportowano: {stats['modes']} trybow, "
        f"{stats['combinations']} kombinacji -> {data_dir()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
