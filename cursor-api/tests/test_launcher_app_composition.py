"""Kontrakt LC-6/LC-7: kanoniczny composition root klasycznego launchera."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from giclee_app import cached_navigation_launcher
from giclee_app import category_launcher
from giclee_app import dragdrop_category_launcher
from giclee_app import launcher
from giclee_app import launcher_app
from giclee_app import options_category_launcher
from giclee_app import styled_category_launcher


_PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "giclee_app"


def _source(filename: str) -> str:
    return (_PACKAGE_ROOT / filename).read_text(encoding="utf-8")


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        parts = [call.func.attr]
        current: ast.expr = call.func.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def test_launcher_app_is_exact_final_class_with_unchanged_base_mro() -> None:
    assert (
        launcher_app.LauncherApp
        is cached_navigation_launcher.CachedNavigationGicleeApp
    )
    assert launcher_app.LauncherApp.__mro__ == (
        cached_navigation_launcher.CachedNavigationGicleeApp,
        dragdrop_category_launcher.DragDropCategoryGicleeApp,
        options_category_launcher.OptionsCategoryGicleeApp,
        styled_category_launcher.StyledCategoryGicleeApp,
        category_launcher.CategoryGicleeApp,
        launcher.GicleeApp,
        object,
    )


def test_launcher_app_main_passes_exact_factory_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []

    def fake_main(*, app_factory: object = None) -> None:
        captured.append(app_factory)

    monkeypatch.setattr(launcher_app._launcher, "main", fake_main)
    launcher_app.main()

    assert captured == [launcher_app.LauncherApp]


def test_launcher_app_source_is_static_and_import_side_effect_free() -> None:
    source = _source("launcher_app.py")
    tree = ast.parse(source)

    assert not [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert "type(" not in source
    assert "_launcher.GicleeApp =" not in source

    prohibited = (
        "studio_preview",
        "launcher_studio",
        "customtkinter",
        "Komponenty",
        "open(",
        "Path(",
        "Thread(",
        ".after(",
        "mainloop(",
    )
    for token in prohibited:
        assert token not in source

    top_level_calls = [
        node
        for statement in tree.body
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(statement)
        if isinstance(node, ast.Call)
    ]
    assert top_level_calls == []

    alias_assignments = [
        statement
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "LauncherApp"
            for target in statement.targets
        )
    ]
    assert len(alias_assignments) == 1
    assert isinstance(alias_assignments[0].value, ast.Name)
    assert alias_assignments[0].value.id == "CachedNavigationGicleeApp"

    main_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    ]
    assert len(main_nodes) == 1
    calls = [node for node in ast.walk(main_nodes[0]) if isinstance(node, ast.Call)]
    assert len(calls) == 1
    assert _call_name(calls[0]) == "_launcher.main"
    assert calls[0].args == []
    assert len(calls[0].keywords) == 1
    assert calls[0].keywords[0].arg == "app_factory"
    assert isinstance(calls[0].keywords[0].value, ast.Name)
    assert calls[0].keywords[0].value.id == "LauncherApp"


def test_package_main_delegates_only_to_launcher_app() -> None:
    source = _source("__main__.py")
    tree = ast.parse(source)

    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]
    assert len(imports) == 1
    assert imports[0].level == 1
    assert imports[0].module == "launcher_app"
    assert [(item.name, item.asname) for item in imports[0].names] == [("main", None)]
    assert "dragdrop_category_launcher" not in source
    assert "cached_navigation_launcher" not in source
    assert "studio_preview" not in source

    guarded_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node) == "main"
    ]
    assert len(guarded_calls) == 1


@pytest.mark.parametrize(
    ("module", "expected_factory"),
    [
        (category_launcher, category_launcher.CategoryGicleeApp),
        (styled_category_launcher, styled_category_launcher.StyledCategoryGicleeApp),
        (options_category_launcher, options_category_launcher.OptionsCategoryGicleeApp),
        (dragdrop_category_launcher, dragdrop_category_launcher.DragDropCategoryGicleeApp),
        (
            cached_navigation_launcher,
            cached_navigation_launcher.CachedNavigationGicleeApp,
        ),
    ],
)
def test_layer_entrypoints_remain_explicit_and_independent(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    expected_factory: object,
) -> None:
    captured: list[object] = []

    def fake_main(*, app_factory: object = None) -> None:
        captured.append(app_factory)

    monkeypatch.setattr(module._launcher, "main", fake_main)

    module.main()

    assert captured == [expected_factory]


def test_studio_entrypoint_remains_separate_from_classic_composition() -> None:
    source = _source("studio_preview.py")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "giclee_app.launcher_studio" in imported_modules
    assert "giclee_app.launcher" not in imported_modules
    assert "giclee_app.launcher_app" not in imported_modules
    assert "launcher_app" not in imported_modules
    assert "cached_navigation_launcher" not in imported_modules
    assert "dragdrop_category_launcher" not in imported_modules
