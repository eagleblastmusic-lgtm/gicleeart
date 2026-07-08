"""Dynamiczne wykrywanie komponentow w folderze `Komponenty/`.

Komponent = podkatalog `Komponenty/<nazwa>/` zawierajacy `__main__.py`.
Opcjonalny `component.json` w katalogu komponentu definiuje metadata wyswietlane
na kafelku:

    {
      "name": "Wyswietlana nazwa",
      "description": "Krotki opis (1-2 linie)",
      "icon": "🖼️",      // emoji albo sciezka do PNG/ICO
      "color": "#1e88e5",  // kolor akcentu kafelka (hex)
      "order": 60           // kolejnosc sortowania (mniejsze = wczesniej)
      "hidden": true        // opcjonalnie: ukryj kafelek w launcherze
      "inline_width": 1040  // opcjonalnie: szerokosc okna launchera (tryb inline)
      "inline_height": 900  // opcjonalnie: wysokosc okna launchera (tryb inline)
    }

Jesli brakuje `component.json`, GicleeApp uzywa nazwy folderu i pierwszej linijki
docstringu z `__init__.py`.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# Domyslne kolory akcentow rotacyjne dla komponentow bez wlasnego color.
# Paleta zgodna ze Studio (dark premium): stonowane, ciepłe tony zamiast Material.
_FALLBACK_COLORS = (
    "#c9a962", "#6b9e7a", "#7a89b8", "#b8867a",
    "#8a9e6b", "#a97ab8", "#6b9e9e", "#b8a06b",
)


@dataclass
class Component:
    folder_name: str            # nazwa folderu (= nazwa modulu pythona)
    package_path: Path          # absolutna sciezka do folderu komponentu
    name: str                   # nazwa wyswietlana
    description: str            # opis
    icon: str = ""              # emoji albo sciezka do pliku
    color: str = "#c9a962"      # kolor akcentu (Studio gold)
    order: int = 1000           # mniejsze = wczesniej
    mode: str = "subprocess"    # "subprocess" | "inline" | "url"
    url: str = ""               # tylko dla mode=url
    hidden: bool = False        # z component.json — ukryty na siatce klasycznego launchera
    extras: dict = field(default_factory=dict)

    @property
    def module_path(self) -> str:
        """Sciezka modulu uzywana z `python -m` (tylko subprocess)."""
        return f"Komponenty.{self.folder_name}"

    @property
    def view_module_path(self) -> str:
        """Sciezka modulu z `view.py` (tylko inline)."""
        return f"Komponenty.{self.folder_name}.view"


def _read_first_docstring_line(init_path: Path) -> str:
    """Wyciaga pierwsza linijke docstringu modulu z `__init__.py`."""
    try:
        src = init_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
        doc = ast.get_docstring(tree)
        if not doc:
            return ""
        first = doc.strip().splitlines()[0].strip()
        # docstring czesto wyglada "<nazwa> - <opis>" -- zwracamy calosc.
        return first
    except (OSError, SyntaxError, ValueError):
        return ""


def discover_components(components_dir: Path, *, include_hidden: bool = False) -> list[Component]:
    """Skanuje katalog `Komponenty/` i zwraca posortowana liste komponentow.

    Reguly:
    - tylko foldery (nie pliki),
    - musza zawierac `__main__.py` (zeby `python -m` zadzialal),
    - katalogi `__pycache__`, hidden (zaczynajace od `.` lub `_`) sa pomijane.
    """
    out: list[Component] = []
    if not components_dir.exists() or not components_dir.is_dir():
        return out

    color_idx = 0
    for entry in sorted(components_dir.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith(".") or name.startswith("__"):
            continue
        if name == "__pycache__":
            continue

        # Manifest
        manifest_path = entry / "component.json"
        manifest: dict = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    manifest = {}
            except (OSError, json.JSONDecodeError, ValueError):
                manifest = {}

        if manifest.get("hidden") and not include_hidden:
            continue

        mode = str(manifest.get("mode") or "subprocess").strip().lower()
        if mode not in {"subprocess", "inline", "url"}:
            mode = "subprocess"

        # Walidacja zaleznie od trybu
        main_py = entry / "__main__.py"
        view_py = entry / "view.py"
        if mode == "subprocess" and not main_py.exists():
            # Stary kontrakt - musi byc __main__.py.
            continue
        if mode == "inline" and not view_py.exists():
            # Tryb inline wymaga view.py z funkcja build_view(parent, on_back).
            continue
        # mode=url: nie wymaga zadnych plikow Pythona, tylko component.json.

        # Fallbacki
        display_name = str(manifest.get("name") or name).strip() or name

        description = str(manifest.get("description") or "").strip()
        if not description:
            init_py = entry / "__init__.py"
            if init_py.exists():
                description = _read_first_docstring_line(init_py)

        icon = str(manifest.get("icon") or "").strip()

        color = str(manifest.get("color") or "").strip()
        if not color:
            color = _FALLBACK_COLORS[color_idx % len(_FALLBACK_COLORS)]
        color_idx += 1

        try:
            order = int(manifest.get("order", 1000))
        except (TypeError, ValueError):
            order = 1000

        url = str(manifest.get("url") or "").strip()
        is_hidden = bool(manifest.get("hidden"))

        # Extras = wszystkie pozostale pola manifestu (na przyszlosc)
        known = {"name", "description", "icon", "color", "order", "mode", "url", "hidden"}
        extras = {k: v for k, v in manifest.items() if k not in known}

        out.append(Component(
            folder_name=name,
            package_path=entry,
            name=display_name,
            description=description,
            icon=icon,
            color=color,
            order=order,
            mode=mode,
            url=url,
            hidden=is_hidden,
            extras=extras,
        ))

    out.sort(key=lambda c: (c.order, c.name.lower()))
    return out


def find_components_dir(start: Path | None = None) -> Path:
    """Znajduje katalog `Komponenty/` szukajac w kilku znanych lokalizacjach.

    0) PyInstaller: `sys._MEIPASS/Komponenty` (bundlowany folder danych)
    1) <start>/Komponenty,
    2) <start>/cursor-api/Komponenty,
    3) idzie w gore katalogow do 4 poziomow szukajac `Komponenty/`.
    """
    # --- PyInstaller (.exe): Komponenty spakowane jako datas -> _MEIPASS/Komponenty
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        bundled = meipass / "Komponenty"
        if bundled.is_dir():
            return bundled

    here = (start or Path(__file__).resolve()).parent
    candidates: list[Path] = [
        here.parent / "Komponenty",                  # cursor-api/Komponenty
        here / "Komponenty",
    ]
    cur = here
    for _ in range(4):
        cur = cur.parent
        candidates.append(cur / "Komponenty")
        candidates.append(cur / "cursor-api" / "Komponenty")
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # Najbardziej prawdopodobna domyslna lokalizacja
    return here.parent / "Komponenty"
