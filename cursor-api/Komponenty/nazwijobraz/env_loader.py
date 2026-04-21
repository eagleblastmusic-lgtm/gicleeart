"""Prosty czytnik .env z katalogu nadrzednego (cursor-api/.env).

Brak zewnetrznych zaleznosci. Ladowane przy imporcie modulu.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_LOADED = False


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out


def load_env() -> None:
    """Wczytaj cursor-api/.env do os.environ (jednokrotnie, bez nadpisywania)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            for k, v in _parse_env_file(candidate).items():
                os.environ.setdefault(k, v)
            return


def get(key: str, default: str | None = None) -> str | None:
    load_env()
    val = os.environ.get(key, default)
    if val is None:
        return None
    val = val.strip()
    return val or default


def _find_env_path() -> Path:
    """Znajdz lokalizacje pliku .env (preferuj cursor-api/.env, potem dowolny)."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
        # Specjalne miejsce: cursor-api/ ma byc preferowane jako tworzona lokalizacja.
        if parent.name == "cursor-api":
            return parent / ".env"
    # Fallback: cursor-api/.env relatywnie do parents[2] (Komponenty/nazwijobraz/env_loader.py)
    try:
        return here.parents[2] / ".env"
    except IndexError:
        return here.parent / ".env"


def set_env_value(key: str, value: str) -> Path:
    """Ustawia/aktualizuje wartosc w cursor-api/.env (in-place merge) oraz w os.environ.

    - Jesli plik .env nie istnieje, tworzy go.
    - Jesli klucz juz tam jest, zastepuje linie.
    - Inaczej dopisuje na koncu.
    Zwraca sciezke do pliku .env.
    """
    if not key:
        raise ValueError("klucz nie moze byc pusty")
    path = _find_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    new_line = f"{key}={value}"
    lines: list[str] = []
    found = False
    if path.exists():
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                stripped = raw.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    lines.append(raw)
                    continue
                k, _, _v = stripped.partition("=")
                if k.strip() == key:
                    lines.append(new_line)
                    found = True
                else:
                    lines.append(raw)
        except OSError:
            pass
    if not found:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(new_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Aktualizuj os.environ od razu (nie czekamy na restart)
    os.environ[key] = value
    return path
