"""Testy importów Studio — brak side-effect modułów i launcher.GicleeApp."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FORBIDDEN_IMPORT_PREFIXES = (
    "giclee_app.launcher",
    "Komponenty.produkcja.orders_sync",
    "Komponenty._shared.backup",
    "Komponenty.socialmedia.cykl.meta_publisher",
    "Komponenty.dokumentysprzedazy.orders_sync",
)

STUDIO_MODULES = [
    "giclee_app.studio_preview",
    "giclee_app.launcher_studio",
    "giclee_app.launcher_delegate",
    "giclee_app.studio.categories",
    "giclee_app.studio.component_index",
    "giclee_app.studio.status_providers",
    "giclee_app.ui.dashboard",
    "giclee_app.ui.component_hub",
    "giclee_app.ui.topbar",
    "giclee_app.ui.sidebar",
]


def _imports_in_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_studio_source_files_no_forbidden_imports() -> None:
    root = Path(__file__).resolve().parents[1] / "giclee_app"
    paths = [
        root / "launcher_studio.py",
        root / "launcher_delegate.py",
        root / "studio_preview.py",
        root / "studio" / "categories.py",
        root / "studio" / "component_index.py",
        root / "studio" / "status_providers.py",
    ]
    paths.extend((root / "ui").glob("*.py"))
    for path in paths:
        if path.name == "__init__.py":
            continue
        imports = _imports_in_file(path)
        for imp in imports:
            for forbidden in FORBIDDEN_IMPORT_PREFIXES:
                assert not (imp == forbidden or imp.startswith(forbidden + "."))


def test_import_studio_modules() -> None:
    for mod in STUDIO_MODULES:
        __import__(mod)


def test_launcher_studio_does_not_import_launcher_module() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert "giclee_app.launcher" not in text
    assert "from .launcher" not in text
    assert "StudioComponentIndex" in text


def test_launcher_delegate_does_not_import_launcher_module() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_delegate.py"
    text = path.read_text(encoding="utf-8")
    assert "giclee_app.launcher" not in text
    assert "from .launcher" not in text
    assert "import GicleeApp" not in text
