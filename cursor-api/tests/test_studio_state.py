"""Testy StudioState — recent, pinned, crash-safe JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import Component
from giclee_app.studio.state import MAX_PINNED, MAX_RECENT, StudioState


def _make_comp(folder: str, *, order: int = 0, mode: str = "subprocess") -> Component:
    return Component(
        folder_name=folder,
        package_path=Path(f"/fake/{folder}"),
        name=folder.title(),
        description="",
        mode=mode,
        order=order,
    )


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "studio_state.json"
    state = StudioState.load(path)
    assert state.recent == []
    assert state.pinned == []


def test_load_corrupt_json_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "studio_state.json"
    path.write_text("{not json", encoding="utf-8")
    state = StudioState.load(path)
    assert state.recent == []
    assert state.pinned == []


def test_record_launch_dedup(tmp_path: Path) -> None:
    state = StudioState(_path=tmp_path / "s.json")
    comp = _make_comp("alpha")
    state.record_launch(comp)
    state.record_launch(comp)
    assert len(state.recent) == 1
    assert state.recent[0].folder_name == "alpha"


def test_record_launch_limit_10(tmp_path: Path) -> None:
    state = StudioState(_path=tmp_path / "s.json")
    for i in range(15):
        state.record_launch(_make_comp(f"c{i}"))
    assert len(state.recent) == MAX_RECENT


def test_toggle_pin_limit_20(tmp_path: Path) -> None:
    state = StudioState(_path=tmp_path / "s.json")
    for i in range(25):
        state.toggle_pin(f"p{i}")
    assert len(state.pinned) == MAX_PINNED


def test_prune_removes_stale(tmp_path: Path) -> None:
    state = StudioState(_path=tmp_path / "s.json")
    state.record_launch(_make_comp("keep"))
    state.record_launch(_make_comp("drop"))
    state.pinned = ["keep", "gone"]
    state._dirty = True
    changed = state.prune(["keep"])
    assert changed
    assert [e.folder_name for e in state.recent] == ["keep"]
    assert state.pinned == ["keep"]


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "studio_state.json"
    state = StudioState(_path=path)
    state.record_launch(_make_comp("hub"))
    state.toggle_pin("hub")
    state.save()
    loaded = StudioState.load(path)
    assert len(loaded.recent) == 1
    assert loaded.pinned == ["hub"]


def test_serialization_no_secrets(tmp_path: Path) -> None:
    path = tmp_path / "studio_state.json"
    state = StudioState(_path=path)
    state.record_launch(_make_comp("safe"))
    state.toggle_pin("safe")
    state.save()
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    blob = json.dumps(data).lower()
    for forbidden in ("token", "secret", "password", "accesstoken", "api_key"):
        assert forbidden not in blob
    assert set(data.keys()) <= {"version", "recent", "pinned"}
    for entry in data["recent"]:
        assert set(entry.keys()) <= {"folder_name", "name", "mode", "at"}


def test_sorted_order_pinned_recent_default(tmp_path: Path) -> None:
    state = StudioState(_path=tmp_path / "s.json")
    state.pinned = ["b"]
    state.record_launch(_make_comp("a"))
    state.record_launch(_make_comp("c"))
    comps = [
        _make_comp("d", order=10),
        _make_comp("a", order=5),
        _make_comp("b", order=1),
        _make_comp("c", order=2),
    ]
    ordered = state.sorted_components(comps)
    names = [c.folder_name for c in ordered]
    assert names[0] == "b"
    assert names[1] == "c"
    assert names[2] == "a"
    assert names[3] == "d"
