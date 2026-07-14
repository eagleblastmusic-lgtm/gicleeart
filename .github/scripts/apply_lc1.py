from __future__ import annotations

from pathlib import Path

ROOT = Path("cursor-api")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


launcher = ROOT / "giclee_app" / "launcher.py"
replace_once(
    launcher,
    "\ndef main() -> None:\n    if _LAUNCHER_AUTH_ENABLED:",
    "\nLauncherFactory = Callable[[tk.Tk], object]\n\n\n"
    "def main(app_factory: LauncherFactory | None = None) -> None:\n"
    "    factory = app_factory or GicleeApp\n"
    "    if _LAUNCHER_AUTH_ENABLED:",
)
replace_once(
    launcher,
    "        GicleeApp(root)\n        root.deiconify()",
    "        factory(root)\n        root.deiconify()",
)

wrapper_blocks = {
    ROOT / "giclee_app" / "category_launcher.py": (
        "CategoryGicleeApp",
        "Uruchamia bazowy launcher z klasą nawigacji kategorii.",
    ),
    ROOT / "giclee_app" / "styled_category_launcher.py": (
        "StyledCategoryGicleeApp",
        "Uruchamia launcher kategorii ze spójnymi kafelkami komponentów.",
    ),
    ROOT / "giclee_app" / "options_category_launcher.py": (
        "OptionsCategoryGicleeApp",
        "Uruchamia pełny launcher kategorii z menu Opcje.",
    ),
    ROOT / "giclee_app" / "dragdrop_category_launcher.py": (
        "DragDropCategoryGicleeApp",
        "Uruchamia pełny launcher z menu Opcje i drag-and-drop.",
    ),
}

for path, (class_name, docstring) in wrapper_blocks.items():
    old = (
        "def main() -> None:\n"
        f'    """{docstring}"""\n\n'
        "    original_class = _launcher.GicleeApp\n"
        f"    _launcher.GicleeApp = {class_name}\n"
        "    try:\n"
        "        _launcher.main()\n"
        "    finally:\n"
        "        _launcher.GicleeApp = original_class"
    )
    new = (
        "def main() -> None:\n"
        f'    """{docstring}"""\n\n'
        f"    _launcher.main(app_factory={class_name})"
    )
    replace_once(path, old, new)


test_path = ROOT / "tests" / "test_launcher_composition.py"
test_path.write_text(
    '''"""Kontrakt LC-1: jawny composition root klasycznego launchera."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app import launcher
from giclee_app import category_launcher
from giclee_app import dragdrop_category_launcher
from giclee_app import options_category_launcher
from giclee_app import styled_category_launcher


class _FakeRoot:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def withdraw(self) -> None:
        self._events.append("withdraw")

    def deiconify(self) -> None:
        self._events.append("deiconify")

    def mainloop(self) -> None:
        self._events.append("mainloop")


def _install_fake_runtime(
    monkeypatch: pytest.MonkeyPatch,
    events: list[str],
) -> _FakeRoot:
    root = _FakeRoot(events)
    fake_tkdnd = SimpleNamespace(TkinterDnD=SimpleNamespace(Tk=lambda: root))
    monkeypatch.setitem(sys.modules, "tkinterdnd2", fake_tkdnd)

    from giclee_app import splash_screen

    def run_splash_then(_root: object, callback: Callable[[], None]) -> None:
        events.append("splash")
        callback()

    monkeypatch.setattr(splash_screen, "run_splash_then", run_splash_then)
    return root


def test_final_launcher_mro_is_unchanged() -> None:
    assert dragdrop_category_launcher.DragDropCategoryGicleeApp.__mro__ == (
        dragdrop_category_launcher.DragDropCategoryGicleeApp,
        options_category_launcher.OptionsCategoryGicleeApp,
        styled_category_launcher.StyledCategoryGicleeApp,
        category_launcher.CategoryGicleeApp,
        launcher.GicleeApp,
        object,
    )


@pytest.mark.parametrize(
    ("module", "expected_factory"),
    [
        (category_launcher, category_launcher.CategoryGicleeApp),
        (styled_category_launcher, styled_category_launcher.StyledCategoryGicleeApp),
        (options_category_launcher, options_category_launcher.OptionsCategoryGicleeApp),
        (dragdrop_category_launcher, dragdrop_category_launcher.DragDropCategoryGicleeApp),
    ],
)
def test_layer_entrypoints_pass_factory_without_runtime_class_replacement(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    expected_factory: object,
) -> None:
    captured: list[object] = []
    original_class = launcher.GicleeApp

    def fake_main(*, app_factory: object = None) -> None:
        captured.append(app_factory)

    monkeypatch.setattr(module._launcher, "main", fake_main)
    module.main()

    assert captured == [expected_factory]
    assert launcher.GicleeApp is original_class


@pytest.mark.parametrize(
    "filename",
    [
        "category_launcher.py",
        "styled_category_launcher.py",
        "options_category_launcher.py",
        "dragdrop_category_launcher.py",
    ],
)
def test_layer_sources_do_not_assign_launcher_class(filename: str) -> None:
    source = (Path(__file__).resolve().parents[1] / "giclee_app" / filename).read_text(
        encoding="utf-8"
    )
    assert "_launcher.GicleeApp =" not in source
    assert "original_class = _launcher.GicleeApp" not in source
    assert "_launcher.main(app_factory=" in source


def test_launcher_main_uses_explicit_factory_once_after_splash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    root = _install_fake_runtime(monkeypatch, events)
    calls: list[object] = []

    def factory(received_root: object) -> object:
        events.append("factory")
        calls.append(received_root)
        return object()

    launcher.main(app_factory=factory)

    assert calls == [root]
    assert events == ["withdraw", "splash", "factory", "deiconify", "mainloop"]


def test_launcher_main_defaults_to_base_launcher_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    root = _install_fake_runtime(monkeypatch, events)
    calls: list[object] = []

    def base_factory(received_root: object) -> object:
        events.append("factory")
        calls.append(received_root)
        return object()

    monkeypatch.setattr(launcher, "GicleeApp", base_factory)
    launcher.main()

    assert calls == [root]
    assert events == ["withdraw", "splash", "factory", "deiconify", "mainloop"]


def test_package_main_still_targets_final_dragdrop_entrypoint() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "giclee_app" / "__main__.py"
    ).read_text(encoding="utf-8")
    assert "from .dragdrop_category_launcher import main" in source
    assert "studio_preview" not in source
''',
    encoding="utf-8",
)

launcher_docs = ROOT / "giclee_app" / "docs" / "launcher.md"
replace_once(
    launcher_docs,
    "**Studio Preview (F1):** nowy shell CustomTkinter w "
    "[`studio-preview.md`](studio-preview.md) — `python -m giclee_app.studio_preview`. "
    "Klasyczny launcher pozostaje fallbackiem z pollingiem Shopify, backupami i "
    "widokami inline.\n",
    "**Studio Preview (F1):** nowy shell CustomTkinter w "
    "[`studio-preview.md`](studio-preview.md) — `python -m giclee_app.studio_preview`. "
    "Klasyczny launcher pozostaje fallbackiem z pollingiem Shopify, backupami i "
    "widokami inline.\n\n"
    "**LC-1 composition root:** warstwy klasycznego launchera przekazują finalną "
    "klasę jawnie do `launcher.main(app_factory=...)`. Entry point, MRO i zachowanie "
    "pozostają bez zmian, a runtime nie podmienia już globalnego "
    "`launcher.GicleeApp`.\n",
)

contract = ROOT / "giclee_app" / "docs" / "launcher-composition-l0-contract.md"
replace_once(
    contract,
    "**Status:** contract freeze — docs only  ",
    "**Status:** L-0 complete · LC-1 implemented  ",
)
