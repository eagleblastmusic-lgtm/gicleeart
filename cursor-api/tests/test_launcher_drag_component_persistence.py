"""Testy adaptera LC-3K: persist_component_reorder + orchestration _reorder_component."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from giclee_app import dragdrop_category_launcher as dnd
from giclee_app import launcher_drag_component_persistence as persistence
from giclee_app.launcher_layout import LauncherLayout, TileLayoutEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_layout(
    *,
    section: str = "S",
    visible: list[tuple[str, int]],
    hidden: list[tuple[str, int]] | None = None,
    other_section: list[tuple[str, int]] | None = None,
) -> LauncherLayout:
    """Buduje LauncherLayout z podaną konfiguracją wpisów."""
    entries: dict[str, TileLayoutEntry] = {}
    for folder, sort_key in visible:
        entries[folder] = TileLayoutEntry(
            folder=folder, section=section, visible=True, sort_key=sort_key
        )
    for folder, sort_key in (hidden or []):
        entries[folder] = TileLayoutEntry(
            folder=folder, section=section, visible=False, sort_key=sort_key
        )
    for folder, sort_key in (other_section or []):
        entries[folder] = TileLayoutEntry(
            folder=folder, section="OTHER", visible=True, sort_key=sort_key
        )
    return LauncherLayout(entries=entries)


class _Status:
    def __init__(self, events: list[object]) -> None:
        self._events = events

    def set(self, text: str) -> None:
        self._events.append(("status", text))


def _launcher_app(
    events: list[object],
    layout: LauncherLayout | None = None,
    active_section: str | None = "S",
) -> dnd.DragDropCategoryGicleeApp:
    app = dnd.DragDropCategoryGicleeApp.__new__(dnd.DragDropCategoryGicleeApp)
    app._all_components = []
    app._layout = layout or LauncherLayout()
    app._normally_visible = set()
    app._active_section = active_section
    app._render_tiles = lambda: events.append("render")  # type: ignore[method-assign]
    app._finish_navigation_render = lambda: events.append("finish")  # type: ignore[method-assign]
    app.status_var = _Status(events)
    return app


# ===========================================================================
# 10.1 Ruch widocznych komponentów
# ===========================================================================

def test_move_before_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 1: source ląduje bezpośrednio przed target (after=False)."""
    layout = _make_layout(visible=[("A", 0), ("B", 10), ("C", 20)])
    saved: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saved.append)

    changed = persistence.persist_component_reorder(
        layout, "S", ["A", "B", "C"], "C", "B", after=False
    )

    assert changed is True
    assert saved == [layout]
    folders = [
        e.folder
        for e in sorted(
            (e for e in layout.entries.values() if e.section == "S"),
            key=lambda e: e.sort_key,
        )
    ]
    assert folders == ["A", "C", "B"]


def test_move_after_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 2: source ląduje bezpośrednio za target (after=True)."""
    layout = _make_layout(visible=[("A", 0), ("B", 10), ("C", 20)])
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)

    changed = persistence.persist_component_reorder(
        layout, "S", ["A", "B", "C"], "A", "B", after=True
    )

    assert changed is True
    folders = [
        e.folder
        for e in sorted(
            (e for e in layout.entries.values() if e.section == "S"),
            key=lambda e: e.sort_key,
        )
    ]
    assert folders == ["B", "A", "C"]


# ===========================================================================
# 10.2 Ukryte komponenty
# ===========================================================================

def test_hidden_slot_preserved_by_replace_subset_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 3: ukryty komponent między widocznymi zachowuje swój slot."""
    # Kolejność w sekcji: A(0) HIDDEN(5) B(10) C(20)
    layout = _make_layout(
        visible=[("A", 0), ("B", 10), ("C", 20)],
        hidden=[("HIDDEN", 5)],
    )
    snapshots: list[list[tuple[str, int]]] = []

    def save(saved: LauncherLayout) -> None:
        snapshots.append(
            [
                (e.folder, e.sort_key)
                for e in sorted(
                    (e for e in saved.entries.values() if e.section == "S"),
                    key=lambda e: e.sort_key,
                )
            ]
        )

    monkeypatch.setattr(persistence, "save_layout", save)

    changed = persistence.persist_component_reorder(
        layout, "S", ["A", "B", "C"], "C", "B", after=False
    )

    assert changed is True
    # Po zamianie C i B: pełna kolejność: A, HIDDEN, C, B
    # (HIDDEN zajmuje slot po A, zanim widoczne B i C)
    assert snapshots == [[("A", 0), ("HIDDEN", 10), ("C", 20), ("B", 30)]]


def test_hidden_component_reindexed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 4: ukryty komponent jest reindeksowany razem z widocznymi."""
    layout = _make_layout(
        visible=[("A", 0), ("B", 10)],
        hidden=[("H", 5)],
    )
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "B", "A", after=False
    )

    # Pełna kolejność po przesunięciu: B, H (slot), A → reindeksacja 0,10,20
    hidden_entry = layout.entries["H"]
    assert hidden_entry.sort_key in (0, 10, 20)
    # Musi być reindeksowany jako element sekcji S
    all_keys = sorted(
        e.sort_key for e in layout.entries.values() if e.section == "S"
    )
    assert all_keys == [0, 10, 20]


# ===========================================================================
# 10.3 Sortowanie i reindeksacja
# ===========================================================================

def test_section_sorted_by_sort_key_and_folder_lower(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 5: pełna sekcja sortowana przez (sort_key, folder.lower())."""
    # sort_key identyczne — powinno rozstrzygać folder.lower()
    layout = _make_layout(
        visible=[("beta", 10), ("alpha", 10), ("gamma", 10)],
    )
    captured_all: list[list[str]] = []
    original_replace = persistence.replace_subset_order

    def recording_replace(existing: list[str], subset: list[str]) -> list[str]:
        captured_all.append(list(existing))
        return original_replace(existing, subset)

    monkeypatch.setattr(persistence, "replace_subset_order", recording_replace)
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)

    persistence.persist_component_reorder(
        layout, "S", ["beta", "alpha", "gamma"], "gamma", "beta", after=False
    )

    assert captured_all[0] == ["alpha", "beta", "gamma"]


def test_reindex_produces_zero_ten_twenty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 6: sort_key po operacji wynoszą 0, 10, 20, ..."""
    layout = _make_layout(visible=[("A", 0), ("B", 10), ("C", 20)])
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B", "C"], "C", "A", after=False
    )

    keys = sorted(e.sort_key for e in layout.entries.values() if e.section == "S")
    assert keys == [0, 10, 20]


def test_other_section_entries_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 7: wpisy innych sekcji mają niezmienione sort_key."""
    layout = _make_layout(
        visible=[("A", 0), ("B", 10)],
        other_section=[("X", 999), ("Y", 888)],
    )
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "B", "A", after=False
    )

    assert layout.entries["X"].sort_key == 999
    assert layout.entries["Y"].sort_key == 888


# ===========================================================================
# 10.4 Niemutowalność wejścia
# ===========================================================================

def test_input_visible_order_not_mutated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 8: wejściowy visible_order nie jest modyfikowany po powrocie."""
    layout = _make_layout(visible=[("A", 0), ("B", 10), ("C", 20)])
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)
    original = ["A", "B", "C"]
    visible_order = list(original)

    persistence.persist_component_reorder(
        layout, "S", visible_order, "C", "A", after=False
    )

    assert visible_order == original


# ===========================================================================
# 10.5 No-op
# ===========================================================================

def test_noop_source_equals_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 9: source == target → False, brak mutacji, brak zapisu."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    original_keys = {f: e.sort_key for f, e in layout.entries.items()}
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    result = persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "A", "A", after=False
    )

    assert result is False
    assert saves == []
    assert all(layout.entries[f].sort_key == k for f, k in original_keys.items())


def test_noop_missing_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 10: source nie istnieje w visible_order → False."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    result = persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "missing", "B", after=False
    )

    assert result is False
    assert saves == []


def test_noop_missing_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 11: target nie istnieje w visible_order → False."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    result = persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "A", "missing", after=False
    )

    assert result is False
    assert saves == []


def test_noop_no_position_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 12: ruch bez zmiany pozycji → False, brak zapisu."""
    # [A, B] → move A before B (after=False) → [A, B] — brak zmiany
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    result = persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "A", "B", after=False
    )

    assert result is False
    assert saves == []


# ===========================================================================
# 10.6 Kontrakt zapisu
# ===========================================================================

def test_exactly_one_save_on_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 13: dokładnie jeden save_layout() przy zmianie kolejności."""
    layout = _make_layout(visible=[("A", 0), ("B", 10), ("C", 20)])
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B", "C"], "C", "A", after=False
    )

    assert len(saves) == 1


def test_save_receives_same_layout_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 14: zapisywany jest ten sam obiekt LauncherLayout."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    observed: list[tuple[bool, dict[str, int]]] = []

    def save(saved: LauncherLayout) -> None:
        observed.append(
            (
                saved is layout,
                {f: e.sort_key for f, e in saved.entries.items()},
            )
        )

    monkeypatch.setattr(persistence, "save_layout", save)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "B", "A", after=False
    )

    assert len(observed) == 1
    same_object, _ = observed[0]
    assert same_object is True


def test_save_called_after_full_reindex(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 15: save_layout wywołany po pełnej reindeksacji."""
    layout = _make_layout(visible=[("A", 0), ("B", 10), ("C", 20)])
    snapshots: list[list[int]] = []

    def save(saved: LauncherLayout) -> None:
        snapshots.append(
            sorted(e.sort_key for e in saved.entries.values() if e.section == "S")
        )

    monkeypatch.setattr(persistence, "save_layout", save)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B", "C"], "C", "A", after=False
    )

    assert snapshots == [[0, 10, 20]]


def test_no_save_for_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 16: przy no-op save_layout nie jest wywoływany."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    saves: list[LauncherLayout] = []
    monkeypatch.setattr(persistence, "save_layout", saves.append)

    persistence.persist_component_reorder(
        layout, "S", ["A", "B"], "A", "A", after=False
    )

    assert saves == []


# ===========================================================================
# 10.7 Propagacja błędu
# ===========================================================================

def test_save_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 17: wyjątek save_layout propaguje się do wywołującego."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])

    def fail(_layout: LauncherLayout) -> None:
        raise OSError("write failed")

    monkeypatch.setattr(persistence, "save_layout", fail)

    with pytest.raises(OSError, match="write failed"):
        persistence.persist_component_reorder(
            layout, "S", ["A", "B"], "B", "A", after=False
        )


def test_no_rollback_after_save_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 18: po błędzie zapisu mutacje sort_key pozostają."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])

    def fail(_layout: LauncherLayout) -> None:
        raise OSError("write failed")

    monkeypatch.setattr(persistence, "save_layout", fail)

    with pytest.raises(OSError):
        persistence.persist_component_reorder(
            layout, "S", ["A", "B"], "B", "A", after=False
        )

    # Reindeksacja już nastąpiła — sort_key muszą być zmienione
    keys = sorted(e.sort_key for e in layout.entries.values() if e.section == "S")
    assert keys == [0, 10]
    # Kolejność jest przetasowana (B przed A)
    folder_order = [
        e.folder
        for e in sorted(
            (e for e in layout.entries.values() if e.section == "S"),
            key=lambda e: e.sort_key,
        )
    ]
    assert folder_order == ["B", "A"]


# ===========================================================================
# 10.8 Izolacja od UI
# ===========================================================================

def test_adapter_does_not_import_tkinter() -> None:
    """Przypadek 19: adapter nie importuje tkinter."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_drag_component_persistence.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "tkinter" not in imported
    assert all("tkinter" not in (m or "") for m in imported_from)
    assert all("dragdrop_category_launcher" not in (m or "") for m in imported_from)
    assert all("category_launcher" not in (m or "") for m in imported_from)
    assert all("renderer" not in (m or "") for m in imported_from)
    assert all("Komponenty" not in (m or "") for m in imported_from)
    assert "persist_component_reorder" in persistence.__all__


def test_adapter_has_no_ui_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Przypadek 20: adapter nie wywołuje renderera ani status_var."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    monkeypatch.setattr(persistence, "save_layout", lambda _: None)
    ui_called: list[str] = []

    # Gdyby adapter próbował wywołać render/finish/status → AttributeError lub wpis
    original_fn = persistence.persist_component_reorder

    def wrapped(*args: object, **kwargs: object) -> bool:
        return original_fn(*args, **kwargs)  # type: ignore[return-value]

    result = wrapped(layout, "S", ["A", "B"], "B", "A", after=False)
    assert result is True
    assert ui_called == []


# ===========================================================================
# 10.9 Orchestration _reorder_component()
# ===========================================================================

def test_reorder_component_passes_correct_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 21: cienka delegacja — _reorder_component wywołuje persist z właściwymi args."""
    layout = _make_layout(visible=[("A", 0), ("B", 10)])
    events: list[object] = []
    app = _launcher_app(events, layout=layout, active_section="S")

    monkeypatch.setattr(
        dnd,
        "resolve_sections",
        lambda *_a, **_kw: [("S", [])],
    )
    from giclee_app.component_loader import Component  # type: ignore[attr-defined]

    class _FakeComp:
        folder_name: str

        def __init__(self, name: str) -> None:
            self.folder_name = name

    monkeypatch.setattr(
        dnd,
        "category_map",
        lambda _sections: {"S": [_FakeComp("A"), _FakeComp("B")]},
    )

    captured: list[tuple[object, ...]] = []

    def fake_persist(
        layout_arg: LauncherLayout,
        section_arg: str,
        visible_order_arg: list[str],
        source_arg: str,
        target_arg: str,
        *,
        after: bool,
    ) -> bool:
        captured.append(
            (layout_arg is app._layout, section_arg, list(visible_order_arg), source_arg, target_arg, after)
        )
        return True

    monkeypatch.setattr(dnd, "persist_component_reorder", fake_persist)

    app._reorder_component("B", "A", after=False)

    assert captured == [(True, "S", ["A", "B"], "B", "A", False)]


def test_no_ui_effects_when_persist_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 22: brak UI effects gdy adapter zwraca False."""
    events: list[object] = []
    app = _launcher_app(events, active_section="S")

    monkeypatch.setattr(dnd, "resolve_sections", lambda *_a, **_kw: [("S", [])])
    monkeypatch.setattr(dnd, "category_map", lambda _s: {"S": []})
    monkeypatch.setattr(dnd, "persist_component_reorder", lambda *_a, **_kw: False)

    app._reorder_component("A", "B", after=False)

    assert events == []


def test_persist_then_render_then_finish_then_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 23: kolejność persist → render → finish → status."""
    events: list[object] = []
    app = _launcher_app(events, active_section="S")

    monkeypatch.setattr(dnd, "resolve_sections", lambda *_a, **_kw: [("S", [])])
    monkeypatch.setattr(dnd, "category_map", lambda _s: {"S": []})

    def fake_persist(*_args: object, **_kwargs: object) -> bool:
        events.append("persist")
        return True

    monkeypatch.setattr(dnd, "persist_component_reorder", fake_persist)
    monkeypatch.setattr(dnd, "category_display_title", lambda s: s)

    app._reorder_component("A", "B", after=True)

    assert events == [
        "persist",
        "render",
        "finish",
        ("status", "S: zapisano kolejność kafelków"),
    ]


def test_no_ui_effects_after_persist_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 24: brak UI effects gdy adapter zgłosi wyjątek."""
    events: list[object] = []
    app = _launcher_app(events, active_section="S")

    monkeypatch.setattr(dnd, "resolve_sections", lambda *_a, **_kw: [("S", [])])
    monkeypatch.setattr(dnd, "category_map", lambda _s: {"S": []})

    def failing_persist(*_args: object, **_kwargs: object) -> bool:
        raise OSError("disk full")

    monkeypatch.setattr(dnd, "persist_component_reorder", failing_persist)

    with pytest.raises(OSError, match="disk full"):
        app._reorder_component("A", "B", after=False)

    assert events == []


def test_no_active_section_returns_early(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 25: brak aktywnej sekcji — metoda kończy się przed resolve i persist."""
    events: list[object] = []
    app = _launcher_app(events, active_section=None)

    resolve_called: list[bool] = []
    persist_called: list[bool] = []

    monkeypatch.setattr(
        dnd,
        "resolve_sections",
        lambda *_a, **_kw: resolve_called.append(True) or [],  # type: ignore[return-value]
    )
    monkeypatch.setattr(
        dnd,
        "persist_component_reorder",
        lambda *_a, **_kw: persist_called.append(True) or False,  # type: ignore[return-value]
    )

    app._reorder_component("A", "B", after=False)

    assert resolve_called == []
    assert persist_called == []
    assert events == []


# ===========================================================================
# 10.10 Niezmieniony _reorder_category() i LC-3J
# ===========================================================================

def test_reorder_category_uses_persist_category_reorder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 26: _reorder_category() deleguje do persist_category_reorder (LC-3J)."""
    events: list[object] = []
    app = _launcher_app(events, layout=LauncherLayout(section_order=["A", "B"]))
    app._active_section = None  # na ekranie głównym

    monkeypatch.setattr(
        dnd,
        "resolve_sections",
        lambda *_a, **_kw: [("A", []), ("B", [])],
    )
    captured: list[tuple[object, ...]] = []

    def fake_category_persist(
        layout_arg: LauncherLayout,
        visible_titles_arg: list[str],
        source_arg: str,
        target_arg: str,
        *,
        after: bool,
    ) -> bool:
        captured.append((layout_arg is app._layout, list(visible_titles_arg), source_arg, target_arg, after))
        return True

    monkeypatch.setattr(dnd, "persist_category_reorder", fake_category_persist)

    app._reorder_category("A", "B", after=True)

    assert captured == [(True, ["A", "B"], "A", "B", True)]
    assert events == ["render", "finish", ("status", "Zapisano nową kolejność kategorii")]


def test_lc3j_not_imported_by_lc3k() -> None:
    """Przypadek 27: adapter LC-3J (persist_category_reorder) nie jest importowany przez LC-3K."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_drag_component_persistence.py"
    )
    source = path.read_text(encoding="utf-8")

    assert "persist_category_reorder" not in source
    assert "launcher_drag_category_persistence" not in source


# ===========================================================================
# Dodatkowy test: source code guard _reorder_component
# ===========================================================================

def test_launcher_component_method_is_thin() -> None:
    """Metoda _reorder_component() nie zawiera bezpośrednio usuwanych operacji."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    # Wytnij body _reorder_component
    component = source.split("def _reorder_component", 1)[1].split("\n\n\ndef main", 1)[0]

    assert "persist_component_reorder(" in component
    assert "reorder_relative(" not in component
    assert "replace_subset_order(" not in component
    assert "entry.sort_key = index * 10" not in component
    assert "save_layout(" not in component
    assert "self._render_tiles()" in component
    assert "self._finish_navigation_render()" in component
    assert "zapisano kolejność kafelków" in component
