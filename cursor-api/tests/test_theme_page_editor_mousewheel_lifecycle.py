from __future__ import annotations

from types import SimpleNamespace

from Komponenty._shared.theme_page_editor.gui_shell import _bind_scoped_mousewheel


class _Widget:
    def __init__(self, master=None) -> None:
        self.master = master
        self.exists = True

    def winfo_exists(self):
        return self.exists


class _Window(_Widget):
    def __init__(self) -> None:
        super().__init__()
        self.callback = None
        self.bind_id = "wheel-id"
        self.unbound = []

    def bind(self, sequence, callback, add=None):
        assert sequence == "<MouseWheel>"
        assert add == "+"
        self.callback = callback
        return self.bind_id

    def unbind(self, sequence, funcid):
        self.unbound.append((sequence, funcid))

    def winfo_containing(self, _x, _y):
        return None


class _Host(_Widget):
    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.destroy_callback = None

    def winfo_toplevel(self):
        return self.window

    def bind(self, sequence, callback, add=None):
        assert sequence == "<Destroy>"
        assert add == "+"
        self.destroy_callback = callback
        return "destroy-id"


class _Canvas(_Widget):
    def __init__(self, master=None) -> None:
        super().__init__(master)
        self.scrolls = []

    def yview_scroll(self, number, what):
        self.scrolls.append((number, what))


def test_mousewheel_scrolls_only_inside_editor_area() -> None:
    window = _Window()
    host = _Host(window)
    area = _Widget(host)
    canvas = _Canvas(area)
    label = _Widget(area)
    outside = _Widget(host)

    _bind_scoped_mousewheel(host, area, canvas)

    assert window.callback is not None
    assert window.callback(SimpleNamespace(widget=label, delta=120)) == "break"
    assert canvas.scrolls == [(-1, "units")]

    assert window.callback(SimpleNamespace(widget=outside, delta=120)) is None
    assert canvas.scrolls == [(-1, "units")]


def test_mousewheel_ignores_destroyed_canvas() -> None:
    window = _Window()
    host = _Host(window)
    area = _Widget(host)
    canvas = _Canvas(area)

    _bind_scoped_mousewheel(host, area, canvas)

    canvas.exists = False
    assert window.callback is not None
    assert window.callback(SimpleNamespace(widget=area, delta=-120)) is None
    assert canvas.scrolls == []


def test_mousewheel_unbinds_exact_global_callback_on_destroy() -> None:
    window = _Window()
    host = _Host(window)
    area = _Widget(host)
    canvas = _Canvas(area)

    _bind_scoped_mousewheel(host, area, canvas)

    assert host.destroy_callback is not None
    host.destroy_callback(SimpleNamespace(widget=host))
    host.destroy_callback(SimpleNamespace(widget=host))

    assert window.unbound == [("<MouseWheel>", "wheel-id")]
