from __future__ import annotations

from types import SimpleNamespace

from . import home_flow_phase_return_hotfix as hotfix


class _FakeTree:
    def selection(self):
        return ("section:prehero",)


class _FakeListbox:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def selection_clear(self, start, end) -> None:
        self.calls.append(("clear", start, end))

    def selection_set(self, index) -> None:
        self.calls.append(("set", index))

    def activate(self, index) -> None:
        self.calls.append(("activate", index))

    def event_generate(self, sequence) -> None:
        self.calls.append(("event", sequence))


def test_restore_section_panel_forces_captured_renderer(monkeypatch) -> None:
    host = SimpleNamespace(_giclee_inline_active_phase="phase:portal")
    tree = _FakeTree()
    listbox = _FakeListbox()
    dispatched: list[object] = []

    monkeypatch.setattr(hotfix, "_zone_index_for_section", lambda _stable_id: 2)
    monkeypatch.setattr(hotfix.base_gui, "_find_section_list", lambda _host: listbox)
    monkeypatch.setattr(
        hotfix,
        "_dispatch_captured_callbacks",
        lambda widget: dispatched.append(widget) or True,
    )

    hotfix._restore_section_panel(host, tree, "section:prehero")

    assert ("set", 2) in listbox.calls
    assert ("activate", 2) in listbox.calls
    assert dispatched == [listbox]
    assert host._giclee_inline_active_phase == ""
    assert not any(call[0] == "event" for call in listbox.calls)


def test_restore_section_panel_ignores_stale_selection(monkeypatch) -> None:
    host = SimpleNamespace(_giclee_inline_active_phase="phase:portal")
    tree = SimpleNamespace(selection=lambda: ("section:hero",))
    monkeypatch.setattr(hotfix, "_zone_index_for_section", lambda _stable_id: 0)

    hotfix._restore_section_panel(host, tree, "section:prehero")

    assert host._giclee_inline_active_phase == "phase:portal"
