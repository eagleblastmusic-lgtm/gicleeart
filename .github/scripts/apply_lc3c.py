from __future__ import annotations

from pathlib import Path


ROOT = Path("cursor-api")
APP = ROOT / "giclee_app"
TESTS = ROOT / "tests"


def replace_exact(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one replacement, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


MODULE = '''"""Adapter Tk dla fallbackowych bindingów skrótów launchera."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk


_KEYPRESS_EVENT = "<KeyPress>"
_DEFAULT_BINDING_MARKER = "_giclee_launcher_shortcut_bound"

ShortcutCallback = Callable[[tk.Event], str | None]
DirectBinder = Callable[[tk.Misc], object]


def bind_shortcut_class(
    root: tk.Misc,
    bindtag: str,
    callback: ShortcutCallback,
) -> bool:
    """Rejestruje class binding prywatnego bindtagu launchera."""

    try:
        root.unbind_class(bindtag, _KEYPRESS_EVENT)
    except (AttributeError, tk.TclError):
        pass
    try:
        root.bind_class(bindtag, _KEYPRESS_EVENT, callback)
    except (AttributeError, tk.TclError):
        return False
    return True


def bind_widget_shortcut(
    widget: tk.Misc,
    callback: ShortcutCallback,
    *,
    marker: str = _DEFAULT_BINDING_MARKER,
) -> bool:
    """Dodaje bezpośredni fallback dokładnie raz dla danego widgetu."""

    if getattr(widget, marker, False):
        return False
    try:
        binding_id = widget.bind(_KEYPRESS_EVENT, callback, add="+")
        setattr(widget, marker, binding_id or True)
    except (AttributeError, tk.TclError):
        return False
    return True


def install_shortcut_bindtags(
    root: tk.Misc,
    bindtag: str,
    callback: ShortcutCallback,
    *,
    bind_direct: DirectBinder | None = None,
) -> None:
    """Instaluje bindtag i fallback na aktualnym drzewie widgetów Tk."""

    direct = bind_direct or (
        lambda widget: bind_widget_shortcut(widget, callback)
    )
    stack: list[tk.Misc] = [root]
    while stack:
        widget = stack.pop()
        try:
            current = tuple(str(tag) for tag in widget.bindtags())
            reordered = (bindtag,) + tuple(
                tag for tag in current if tag != bindtag
            )
            if reordered != current:
                widget.bindtags(reordered)
            direct(widget)
            stack.extend(widget.winfo_children())
        except (AttributeError, tk.TclError):
            continue
'''


TEST_FILE = '''"""Testy LC-3C: adapter bindingów skrótów Tk."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from giclee_app import launcher_tk_shortcut_bindings as bindings
from giclee_app import options_category_launcher as options


class FakeWidget:
    def __init__(
        self,
        tags: tuple[str, ...],
        children: list["FakeWidget"] | None = None,
    ) -> None:
        self._tags = tags
        self._children = children or []
        self.direct_bindings: list[tuple[str, object, str]] = []

    def bindtags(self, tags: tuple[str, ...] | None = None) -> tuple[str, ...]:
        if tags is not None:
            self._tags = tuple(tags)
        return self._tags

    def winfo_children(self) -> list["FakeWidget"]:
        return list(self._children)

    def bind(self, sequence: str, callback: object, add: str = "") -> str:
        self.direct_bindings.append((sequence, callback, add))
        return f"binding-{len(self.direct_bindings)}"


class FakeRoot(FakeWidget):
    def __init__(self, children: list[FakeWidget] | None = None) -> None:
        super().__init__(("root", "Tk", "all"), children)
        self.bound_classes: list[tuple[str, str, object]] = []
        self.unbound_classes: list[tuple[str, str]] = []

    def bind_class(self, tag: str, sequence: str, callback: object) -> None:
        self.bound_classes.append((tag, sequence, callback))

    def unbind_class(self, tag: str, sequence: str) -> None:
        self.unbound_classes.append((tag, sequence))


def _callback(_event: object) -> None:
    return None


def test_bind_shortcut_class_unbinds_then_binds() -> None:
    root = FakeRoot()

    assert bindings.bind_shortcut_class(root, "LauncherTag", _callback) is True

    assert root.unbound_classes == [("LauncherTag", "<KeyPress>")]
    assert root.bound_classes == [("LauncherTag", "<KeyPress>", _callback)]


def test_unbind_error_does_not_block_class_binding() -> None:
    class Root(FakeRoot):
        def unbind_class(self, tag: str, sequence: str) -> None:
            raise options.tk.TclError("missing")

    root = Root()
    assert bindings.bind_shortcut_class(root, "LauncherTag", _callback) is True
    assert root.bound_classes == [("LauncherTag", "<KeyPress>", _callback)]


def test_bind_class_error_returns_false() -> None:
    class Root(FakeRoot):
        def bind_class(self, tag: str, sequence: str, callback: object) -> None:
            raise options.tk.TclError("closed")

    assert bindings.bind_shortcut_class(Root(), "LauncherTag", _callback) is False


def test_bind_widget_shortcut_uses_add_plus_and_marker_once() -> None:
    widget = FakeWidget(("child", "TFrame", ".", "all"))

    assert bindings.bind_widget_shortcut(widget, _callback) is True
    assert bindings.bind_widget_shortcut(widget, _callback) is False

    assert widget.direct_bindings == [("<KeyPress>", _callback, "+")]
    assert getattr(widget, "_giclee_launcher_shortcut_bound") == "binding-1"


def test_bind_widget_shortcut_uses_truthy_marker_for_empty_id() -> None:
    class Widget(FakeWidget):
        def bind(self, sequence: str, callback: object, add: str = "") -> str:
            self.direct_bindings.append((sequence, callback, add))
            return ""

    widget = Widget(("child",))
    assert bindings.bind_widget_shortcut(widget, _callback) is True
    assert getattr(widget, "_giclee_launcher_shortcut_bound") is True


def test_bind_widget_shortcut_tolerates_widget_error() -> None:
    widget = SimpleNamespace(
        bind=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            options.tk.TclError("gone")
        )
    )
    assert bindings.bind_widget_shortcut(widget, _callback) is False


def test_install_places_tag_first_preserves_order_and_binds_tree_once() -> None:
    grandchild = FakeWidget(("grand", "TLabel", ".", "all"))
    child = FakeWidget(("child", "TFrame", ".", "all"), [grandchild])
    root = FakeRoot([child])

    bindings.install_shortcut_bindtags(root, "LauncherTag", _callback)
    bindings.install_shortcut_bindtags(root, "LauncherTag", _callback)

    assert root.bindtags() == ("LauncherTag", "root", "Tk", "all")
    assert child.bindtags() == ("LauncherTag", "child", "TFrame", ".", "all")
    assert grandchild.bindtags() == (
        "LauncherTag",
        "grand",
        "TLabel",
        ".",
        "all",
    )
    assert len(root.direct_bindings) == 1
    assert len(child.direct_bindings) == 1
    assert len(grandchild.direct_bindings) == 1


def test_install_removes_existing_duplicate_bindtags() -> None:
    root = FakeRoot()
    root._tags = ("LauncherTag", "root", "LauncherTag", "all")

    bindings.install_shortcut_bindtags(root, "LauncherTag", _callback)

    assert root.bindtags() == ("LauncherTag", "root", "all")


def test_install_uses_injected_direct_binder_for_each_widget() -> None:
    child = FakeWidget(("child",))
    root = FakeRoot([child])
    visited: list[FakeWidget] = []

    bindings.install_shortcut_bindtags(
        root,
        "LauncherTag",
        _callback,
        bind_direct=visited.append,
    )

    assert visited == [root, child]
    assert root.direct_bindings == []
    assert child.direct_bindings == []


def test_broken_widget_does_not_block_sibling() -> None:
    class BrokenWidget(FakeWidget):
        def bindtags(self, tags=None):  # type: ignore[no-untyped-def]
            raise options.tk.TclError("gone")

    broken = BrokenWidget(("broken",))
    good = FakeWidget(("good",))
    root = FakeRoot([good, broken])

    bindings.install_shortcut_bindtags(root, "LauncherTag", _callback)

    assert good.bindtags()[0] == "LauncherTag"
    assert len(good.direct_bindings) == 1


def test_adapter_module_has_only_tk_boundary_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_tk_shortcut_bindings.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    forbidden = {
        "giclee_app.options_category_launcher",
        "giclee_app.launcher",
        "giclee_app.launcher_shortcut_controller",
        "giclee_app.launcher_windows_shortcuts",
        "giclee_app.dragdrop_category_launcher",
    }
    assert imports.isdisjoint(forbidden)
    assert not any(name.startswith("giclee_app.studio") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)


def _new_app(*, windows: bool = False):
    app = options.OptionsCategoryGicleeApp.__new__(
        options.OptionsCategoryGicleeApp
    )
    app._windows_user32 = object() if windows else None
    app._shortcut_bindtag = "LauncherTag"
    app.root = FakeRoot()
    return app


def test_options_bind_wrapper_delegates_and_installs_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _new_app()
    calls: list[tuple[object, ...]] = []
    installed: list[bool] = []
    monkeypatch.setattr(
        options,
        "bind_shortcut_class",
        lambda *args: calls.append(args) or True,
    )
    app._install_shortcut_bindtags = lambda: installed.append(True)

    app._bind_launcher_shortcuts()

    assert calls == [(app.root, "LauncherTag", app._on_launcher_key_shortcut)]
    assert installed == [True]


def test_options_bind_wrapper_stops_when_class_binding_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _new_app()
    installed: list[bool] = []
    monkeypatch.setattr(options, "bind_shortcut_class", lambda *_args: False)
    app._install_shortcut_bindtags = lambda: installed.append(True)

    app._bind_launcher_shortcuts()

    assert installed == []


def test_options_install_wrapper_preserves_direct_override_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _new_app()
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        options,
        "install_shortcut_bindtags",
        lambda *args, **kwargs: calls.append((*args, kwargs)),
    )

    app._install_shortcut_bindtags()

    assert calls == [
        (
            app.root,
            "LauncherTag",
            app._on_launcher_key_shortcut,
            {"bind_direct": app._bind_shortcut_directly},
        )
    ]


def test_options_direct_wrapper_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _new_app()
    widget = FakeWidget(("child",))
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        options,
        "bind_widget_shortcut",
        lambda *args: calls.append(args) or True,
    )

    app._bind_shortcut_directly(widget)

    assert calls == [(widget, app._on_launcher_key_shortcut)]


def test_windows_mode_skips_all_tk_binding_wrappers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _new_app(windows=True)
    calls: list[str] = []
    monkeypatch.setattr(
        options,
        "bind_shortcut_class",
        lambda *_args: calls.append("class") or True,
    )
    monkeypatch.setattr(
        options,
        "install_shortcut_bindtags",
        lambda *_args, **_kwargs: calls.append("tree"),
    )

    app._bind_launcher_shortcuts()
    app._install_shortcut_bindtags()

    assert calls == []


def test_options_source_keeps_lifecycle_and_handler_ownership() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "options_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    bind_block = source.split("def _bind_launcher_shortcuts", 1)[1].split(
        "\n    def ", 1
    )[0]
    install_block = source.split("def _install_shortcut_bindtags", 1)[1].split(
        "\n    def ", 1
    )[0]

    assert "bind_shortcut_class(" in bind_block
    assert "self._install_shortcut_bindtags()" in bind_block
    assert "install_shortcut_bindtags(" in install_block
    assert "bind_direct=self._bind_shortcut_directly" in install_block
    assert "def _on_launcher_key_shortcut" in source
    assert "self.root.after_idle(self._install_shortcut_bindtags)" in source
    assert "self.root.after(80, self._restore_shortcut_focus)" in source
    assert "self.root.after(320, self._restore_shortcut_focus)" in source
'''


OPTIONS_IMPORT_OLD = '''from .launcher_shortcut_options import show_shortcut_options
from .launcher_windows_shortcuts import (
'''
OPTIONS_IMPORT_NEW = '''from .launcher_shortcut_options import show_shortcut_options
from .launcher_tk_shortcut_bindings import (
    bind_shortcut_class,
    bind_widget_shortcut,
    install_shortcut_bindtags,
)
from .launcher_windows_shortcuts import (
'''

OPTIONS_METHODS_OLD = '''    def _bind_launcher_shortcuts(self) -> None:
        """Rejestruje fallback Tk wyłącznie poza trybem WinAPI."""

        if getattr(self, "_windows_user32", None) is not None:
            return
        try:
            self.root.unbind_class(self._shortcut_bindtag, "<KeyPress>")
        except (AttributeError, tk.TclError):
            pass
        try:
            self.root.bind_class(
                self._shortcut_bindtag,
                "<KeyPress>",
                self._on_launcher_key_shortcut,
            )
        except (AttributeError, tk.TclError):
            return
        self._install_shortcut_bindtags()

    def _install_shortcut_bindtags(self) -> None:
        """Instaluje fallback Tk na całym drzewie widgetów poza Windows WinAPI."""

        if getattr(self, "_windows_user32", None) is not None:
            return
        stack: list[tk.Misc] = [self.root]
        while stack:
            widget = stack.pop()
            try:
                current = tuple(str(tag) for tag in widget.bindtags())
                reordered = (self._shortcut_bindtag,) + tuple(
                    tag for tag in current if tag != self._shortcut_bindtag
                )
                if reordered != current:
                    widget.bindtags(reordered)
                self._bind_shortcut_directly(widget)
                stack.extend(widget.winfo_children())
            except (AttributeError, tk.TclError):
                continue

    def _bind_shortcut_directly(self, widget: tk.Misc) -> None:
        marker = "_giclee_launcher_shortcut_bound"
        if getattr(widget, marker, False):
            return
        try:
            binding_id = widget.bind(
                "<KeyPress>",
                self._on_launcher_key_shortcut,
                add="+",
            )
            setattr(widget, marker, binding_id or True)
        except (AttributeError, tk.TclError):
            pass
'''

OPTIONS_METHODS_NEW = '''    def _bind_launcher_shortcuts(self) -> None:
        """Rejestruje fallback Tk wyłącznie poza trybem WinAPI."""

        if getattr(self, "_windows_user32", None) is not None:
            return
        if not bind_shortcut_class(
            self.root,
            self._shortcut_bindtag,
            self._on_launcher_key_shortcut,
        ):
            return
        self._install_shortcut_bindtags()

    def _install_shortcut_bindtags(self) -> None:
        """Instaluje fallback Tk na całym drzewie widgetów poza Windows WinAPI."""

        if getattr(self, "_windows_user32", None) is not None:
            return
        install_shortcut_bindtags(
            self.root,
            self._shortcut_bindtag,
            self._on_launcher_key_shortcut,
            bind_direct=self._bind_shortcut_directly,
        )

    def _bind_shortcut_directly(self, widget: tk.Misc) -> None:
        bind_widget_shortcut(widget, self._on_launcher_key_shortcut)
'''

LAUNCHER_DOC_OLD = '''**LC-3B Windows adapter:** `launcher_windows_shortcuts.py` izoluje virtual-key mapping, user32, foreground i próbki klawiszy/modyfikatorów. `OptionsCategoryGicleeApp` nadal posiada timery, aktywność, Tk fallback oraz LC-3A orchestration.

---
'''
LAUNCHER_DOC_NEW = '''**LC-3B Windows adapter:** `launcher_windows_shortcuts.py` izoluje virtual-key mapping, user32, foreground i próbki klawiszy/modyfikatorów. `OptionsCategoryGicleeApp` nadal posiada timery, aktywność, Tk fallback oraz LC-3A orchestration.

**LC-3C Tk binding adapter:** `launcher_tk_shortcut_bindings.py` izoluje class binding, rekursywne bindtagi i bezpośredni fallback bez duplikatów. Lifecycle, fokus, aktywacja i handler eventu pozostają w `OptionsCategoryGicleeApp`.

---
'''


def main() -> None:
    (APP / "launcher_tk_shortcut_bindings.py").write_text(
        MODULE,
        encoding="utf-8",
    )
    replace_exact(
        APP / "options_category_launcher.py",
        OPTIONS_IMPORT_OLD,
        OPTIONS_IMPORT_NEW,
    )
    replace_exact(
        APP / "options_category_launcher.py",
        OPTIONS_METHODS_OLD,
        OPTIONS_METHODS_NEW,
    )
    (TESTS / "test_launcher_tk_shortcut_bindings.py").write_text(
        TEST_FILE,
        encoding="utf-8",
    )
    replace_exact(
        APP / "docs" / "launcher-composition-lc3c-contract.md",
        "**Status:** fresh reconnaissance · contract freeze  ",
        "**Status:** LC-3C implemented",
    )
    replace_exact(
        APP / "docs" / "launcher.md",
        LAUNCHER_DOC_OLD,
        LAUNCHER_DOC_NEW,
    )


if __name__ == "__main__":
    main()
