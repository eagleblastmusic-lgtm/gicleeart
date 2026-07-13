"""Testy GF-M2 — bezstanowe prymitywy UI GICLÉE FRAME."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view as view
from giclee_app.ui import gicleeframe_view_primitives as primitives
from giclee_app.ui import theme

_PRIMITIVES_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_primitives.py"
)
_VIEW_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"

_TOKEN_NAMES = (
    "_BTN_HEIGHT",
    "_CARD_PAD_X",
    "_CARD_PAD_Y",
    "_GF_BG",
    "_GF_PANEL",
    "_GF_CARD",
    "_GF_CARD_SOFT",
    "_GF_FIELD",
    "_GF_FIELD_HOVER",
    "_GF_BORDER",
    "_GF_BORDER_WARM",
    "_GF_GOLD_SOFT",
    "_GF_GOLD",
    "_GF_MUTED",
    "_GF_PREVIEW_BG",
    "_GF_PREVIEW_PAPER",
    "_GF_PREVIEW_MAT",
    "_GF_SUCCESS",
    "_GF_DANGER",
)

_FUNCTION_NAMES = (
    "_f2_entry_kwargs",
    "_make_surface",
    "_make_card",
    "_make_gf_card",
    "_make_section_caption",
    "_make_card_title",
    "_make_section_title",
    "_make_status_pill",
    "_make_pill",
    "_make_empty_state",
    "_build_safety_row",
    "_make_secondary_button",
    "_make_primary_button",
    "_f2_menu_kwargs",
    "_element_pill_colors",
)

_VIEW_REEXPORT_EXCLUDED_AFTER_GF_M6 = frozenset({"_build_safety_row"})

_EXPECTED_TOKEN_VALUES = {
    "_BTN_HEIGHT": 28,
    "_CARD_PAD_X": 14,
    "_CARD_PAD_Y": 12,
    "_GF_BG": "#161618",
    "_GF_PANEL": "#1e1e21",
    "_GF_CARD": "#27272a",
    "_GF_CARD_SOFT": "#303033",
    "_GF_FIELD": "#1a1a1c",
    "_GF_FIELD_HOVER": "#353538",
    "_GF_BORDER": "#3d3d42",
    "_GF_BORDER_WARM": "#52525a",
    "_GF_GOLD_SOFT": "#8a8270",
    "_GF_GOLD": "#b8a878",
    "_GF_MUTED": "#9a9a9f",
    "_GF_PREVIEW_BG": "#131315",
    "_GF_PREVIEW_PAPER": "#2e2e32",
    "_GF_PREVIEW_MAT": "#222225",
    "_GF_SUCCESS": "#7a9480",
    "_GF_DANGER": "#a07068",
}

_FORBIDDEN_PRIMITIVES_TOKENS = (
    "import os",
    "import sys",
    "import time",
    "import tkinter",
    "Komponenty",
    "open(",
    "write_text",
    "requests",
    "subprocess",
    "after(",
)


class FakeFrame:
    last_master: Any = None
    last_kwargs: dict[str, Any] = {}

    def __init__(self, master: Any, **kwargs: Any) -> None:
        FakeFrame.last_master = master
        FakeFrame.last_kwargs = dict(kwargs)


class FakeLabel:
    last_master: Any = None
    last_kwargs: dict[str, Any] = {}

    def __init__(self, master: Any, **kwargs: Any) -> None:
        FakeLabel.last_master = master
        FakeLabel.last_kwargs = dict(kwargs)


class FakeButton:
    last_master: Any = None
    last_kwargs: dict[str, Any] = {}

    def __init__(self, master: Any, **kwargs: Any) -> None:
        FakeButton.last_master = master
        FakeButton.last_kwargs = dict(kwargs)

    def pack(self, **_kwargs: Any) -> None:
        return None


def test_primitives_all_exports_importable() -> None:
    for name in _TOKEN_NAMES + _FUNCTION_NAMES:
        assert hasattr(primitives, name), name


def test_primitives_all_is_immutable_tuple_of_34() -> None:
    assert isinstance(primitives.__all__, tuple)
    assert len(primitives.__all__) == 34
    assert len(set(primitives.__all__)) == 34
    assert set(primitives.__all__) == set(_TOKEN_NAMES) | set(_FUNCTION_NAMES)


def test_view_reexports_all_functions_with_identity() -> None:
    for name in _FUNCTION_NAMES:
        if name in _VIEW_REEXPORT_EXCLUDED_AFTER_GF_M6:
            assert not hasattr(view, name)
            continue
        assert getattr(view, name) is getattr(primitives, name), name


def test_token_values_match_pre_extraction_snapshot() -> None:
    for name, expected in _EXPECTED_TOKEN_VALUES.items():
        assert getattr(primitives, name) == expected, name


def test_f2_entry_kwargs_contract() -> None:
    assert primitives._f2_entry_kwargs() == {
        "height": 32,
        "fg_color": primitives._GF_FIELD,
        "border_width": 1,
        "border_color": primitives._GF_BORDER,
    }


def test_f2_menu_kwargs_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_font = object()
    monkeypatch.setattr(theme, "get_font", lambda size, weight="normal": fake_font)
    assert primitives._f2_menu_kwargs() == {
        "fg_color": primitives._GF_FIELD,
        "button_color": primitives._GF_FIELD,
        "button_hover_color": primitives._GF_FIELD_HOVER,
        "dropdown_fg_color": primitives._GF_PANEL,
        "dropdown_hover_color": primitives._GF_CARD_SOFT,
        "font": fake_font,
    }


@pytest.mark.parametrize(
    ("status", "has_draft_patch", "expected"),
    [
        ("ok", True, (theme.AccentGoldDim, theme.TextPrimary)),
        ("draft_edited", False, (theme.AccentGoldDim, theme.TextPrimary)),
        ("hidden_draft", False, (theme.AccentGoldDim, theme.TextPrimary)),
        ("ok", False, (theme.StatusOk, theme.AppBg)),
        ("needs_review", False, (theme.StatusWarn, theme.AppBg)),
        ("missing_content", False, (theme.StatusErr, theme.TextPrimary)),
        ("legacy_disabled", False, (theme.StatusUnknown, theme.TextPrimary)),
        ("unknown_status", False, (theme.PanelBg, theme.TextMuted)),
    ],
)
def test_element_pill_colors_cases(
    status: str,
    has_draft_patch: bool,
    expected: tuple[str, str],
) -> None:
    assert primitives._element_pill_colors(status, has_draft_patch=has_draft_patch) == expected


@pytest.mark.parametrize(
    ("variant", "expected_fg"),
    [
        ("panel", primitives._GF_CARD),
        ("soft", primitives._GF_CARD_SOFT),
        ("field", primitives._GF_FIELD),
        ("preview", primitives._GF_PREVIEW_BG),
        ("panel_deep", primitives._GF_PANEL),
    ],
)
def test_make_gf_card_variants(
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
    expected_fg: str,
) -> None:
    monkeypatch.setattr(primitives.ctk, "CTkFrame", FakeFrame)
    master = object()
    primitives._make_gf_card(master, variant=variant)
    assert FakeFrame.last_master is master
    assert FakeFrame.last_kwargs == {
        "fg_color": expected_fg,
        "corner_radius": 14,
    }


def test_make_gf_card_bordered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(primitives.ctk, "CTkFrame", FakeFrame)
    master = object()
    primitives._make_gf_card(master, variant="panel_deep", bordered=True)
    assert FakeFrame.last_master is master
    assert FakeFrame.last_kwargs == {
        "fg_color": primitives._GF_PANEL,
        "corner_radius": 14,
        "border_width": 1,
        "border_color": primitives._GF_BORDER,
    }


def test_make_status_pill_default(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_font = object()
    monkeypatch.setattr(theme, "get_font", lambda size, weight="normal": fake_font)
    monkeypatch.setattr(primitives.ctk, "CTkLabel", FakeLabel)
    master = object()
    primitives._make_status_pill(master, "Status")
    assert FakeLabel.last_master is master
    assert FakeLabel.last_kwargs == {
        "text": "Status",
        "font": fake_font,
        "text_color": primitives._GF_MUTED,
        "fg_color": primitives._GF_FIELD,
        "corner_radius": 999,
        "padx": 10,
        "pady": 4,
    }


def test_make_status_pill_bold(monkeypatch: pytest.MonkeyPatch) -> None:
    normal_font = object()
    bold_font = object()

    def _fake_get_font(size: int, weight: str = "normal") -> object:
        return bold_font if weight == "bold" else normal_font

    monkeypatch.setattr(theme, "get_font", _fake_get_font)
    monkeypatch.setattr(primitives.ctk, "CTkLabel", FakeLabel)
    master = object()
    primitives._make_status_pill(master, "Status", bold=True)
    assert FakeLabel.last_kwargs["font"] is bold_font
    assert FakeLabel.last_kwargs["text_color"] == primitives._GF_MUTED


def test_make_status_pill_accent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_font = object()
    monkeypatch.setattr(theme, "get_font", lambda size, weight="normal": fake_font)
    monkeypatch.setattr(primitives.ctk, "CTkLabel", FakeLabel)
    master = object()
    primitives._make_status_pill(master, "Status", accent=True)
    assert FakeLabel.last_kwargs == {
        "text": "Status",
        "font": fake_font,
        "text_color": primitives._GF_GOLD_SOFT,
        "fg_color": primitives._GF_FIELD,
        "corner_radius": 999,
        "padx": 10,
        "pady": 4,
    }


def test_make_status_pill_explicit_colors(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_font = object()
    monkeypatch.setattr(theme, "get_font", lambda size, weight="normal": fake_font)
    monkeypatch.setattr(primitives.ctk, "CTkLabel", FakeLabel)
    master = object()
    primitives._make_status_pill(
        master,
        "Status",
        fg_color="#111111",
        text_color="#222222",
    )
    assert FakeLabel.last_kwargs["fg_color"] == "#111111"
    assert FakeLabel.last_kwargs["text_color"] == "#222222"


def test_make_secondary_button_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_font = object()
    monkeypatch.setattr(theme, "get_font", lambda size, weight="normal": fake_font)
    monkeypatch.setattr(primitives.ctk, "CTkButton", FakeButton)
    master = object()

    def _cmd() -> None:
        return None

    primitives._make_secondary_button(master, "Action", _cmd)
    assert FakeButton.last_master is master
    assert FakeButton.last_kwargs == {
        "text": "Action",
        "height": primitives._BTN_HEIGHT,
        "fg_color": primitives._GF_FIELD,
        "hover_color": primitives._GF_FIELD_HOVER,
        "border_width": 1,
        "border_color": primitives._GF_BORDER,
        "text_color": theme.TextPrimary,
        "font": fake_font,
        "command": _cmd,
    }


def test_make_primary_button_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_font = object()
    monkeypatch.setattr(theme, "get_font", lambda size, weight="normal": fake_font)
    monkeypatch.setattr(primitives.ctk, "CTkButton", FakeButton)
    master = object()

    def _cmd() -> None:
        return None

    primitives._make_primary_button(master, "Primary", _cmd)
    assert FakeButton.last_master is master
    assert FakeButton.last_kwargs == {
        "text": "Primary",
        "width": 220,
        "height": 36,
        "fg_color": primitives._GF_GOLD_SOFT,
        "hover_color": primitives._GF_GOLD,
        "text_color": primitives._GF_BG,
        "font": fake_font,
        "command": _cmd,
    }


def test_primitives_source_guardrails() -> None:
    text = _PRIMITIVES_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert imp not in {"os", "sys", "time", "tkinter"}
        assert not imp.startswith("Komponenty")
    for token in _FORBIDDEN_PRIMITIVES_TOKENS:
        assert token not in text
    for node in ast.walk(tree):
        assert not isinstance(node, ast.ClassDef)
    module_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and not target.id.startswith("_") for target in node.targets)
    ]
    assert module_assignments == []


def test_view_imports_primitives_and_does_not_redefine_symbols() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "gicleeframe_view_primitives" in text
    assert "class GicleeFrameView" in text
    assert "def _env_enabled" in text
    assert "_GF_BOOT_DEFER_MS" in text
    for name in _FUNCTION_NAMES:
        assert f"def {name}" not in text, name
    for name in _TOKEN_NAMES:
        assert f"{name} =" not in text, name
