from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from Komponenty.stronaglowna.gui import _bind_scoped_mousewheel


class _Window:
    def __init__(self) -> None:
        self.sequence = None
        self.callback = None
        self.add = None
        self.unbound = []

    def bind(self, sequence, callback, add=None):
        self.sequence = sequence
        self.callback = callback
        self.add = add
        return "mousewheel-binding"

    def unbind(self, sequence, funcid):
        self.unbound.append((sequence, funcid))


class _Host:
    def __init__(self, window: _Window) -> None:
        self.window = window
        self.destroy_callback = None

    def winfo_toplevel(self):
        return self.window

    def bind(self, sequence, callback, add=None):
        assert sequence == "<Destroy>"
        assert add == "+"
        self.destroy_callback = callback
        return "destroy-binding"


class _Canvas:
    def __init__(self) -> None:
        self.exists = True
        self.scrolls = []

    def winfo_exists(self):
        return self.exists

    def yview_scroll(self, number, what):
        self.scrolls.append((number, what))


def test_scoped_mousewheel_scrolls_live_canvas() -> None:
    window = _Window()
    host = _Host(window)
    canvas = _Canvas()
    _bind_scoped_mousewheel(host, canvas)
    assert window.sequence == "<MouseWheel>"
    assert window.add == "+"
    assert window.callback is not None
    window.callback(SimpleNamespace(delta=120))
    assert canvas.scrolls == [(-1, "units")]


def test_scoped_mousewheel_unbinds_exact_callback_on_host_destroy() -> None:
    window = _Window()
    host = _Host(window)
    canvas = _Canvas()
    _bind_scoped_mousewheel(host, canvas)
    assert host.destroy_callback is not None
    host.destroy_callback(SimpleNamespace(widget=host))
    host.destroy_callback(SimpleNamespace(widget=host))
    assert window.unbound == [("<MouseWheel>", "mousewheel-binding")]


def test_stale_mousewheel_callback_ignores_destroyed_canvas() -> None:
    window = _Window()
    host = _Host(window)
    canvas = _Canvas()
    _bind_scoped_mousewheel(host, canvas)
    canvas.exists = False
    assert window.callback is not None
    window.callback(SimpleNamespace(delta=-120))
    assert canvas.scrolls == []


def test_stronaglowna_no_longer_uses_global_bind_all() -> None:
    source_path = Path(__file__).resolve().parents[1] / "Komponenty" / "stronaglowna" / "gui.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    bind_all_lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "bind_all":
            bind_all_lines.append(node.lineno)
    assert bind_all_lines == []
