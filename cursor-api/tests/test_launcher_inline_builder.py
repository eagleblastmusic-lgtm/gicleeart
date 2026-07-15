"""Testy neutralnego helpera dla sygnatur i wywołań build_view (LC-4B)."""

from __future__ import annotations

import ast
import functools
import inspect
import sys
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app import launcher_inline_builder as lib
from giclee_app.launcher_inline_builder import (
    invoke_inline_builder,
    supports_on_open_component,
)


# ---------------------------------------------------------------------------
# Testy supports_on_open_component
# ---------------------------------------------------------------------------


def test_supports_two_arg() -> None:
    """1. Zwykły builder (parent, on_back) -> False."""
    def builder(parent: Any, on_back: Any) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_positional_or_keyword() -> None:
    """2. POSITIONAL_OR_KEYWORD on_open_component -> True."""
    def builder(parent: Any, on_back: Any, on_open_component: Any = None) -> None:
        pass
    assert supports_on_open_component(builder) is True


def test_supports_keyword_only() -> None:
    """3. KEYWORD_ONLY on_open_component -> True."""
    def builder(parent: Any, on_back: Any, *, on_open_component: Any = None) -> None:
        pass
    assert supports_on_open_component(builder) is True


def test_supports_kwargs() -> None:
    """4. **kwargs -> True."""
    def builder(parent: Any, on_back: Any, **kwargs: Any) -> None:
        pass
    assert supports_on_open_component(builder) is True


def test_supports_args_only() -> None:
    """5. Samo *args -> False."""
    def builder(parent: Any, on_back: Any, *args: Any) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_optional_positional_only() -> None:
    """6. Optional positional-only on_open_component bez **kwargs -> False."""
    def builder(parent: Any, on_back: Any, on_open_component: Any = None, /) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_required_positional_only() -> None:
    """7. Required positional-only on_open_component bez **kwargs -> False."""
    def builder(parent: Any, on_back: Any, on_open_component: Any, /) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_positional_only_with_kwargs() -> None:
    """8. Positional-only on_open_component razem z **kwargs -> True przez **kwargs."""
    def builder(parent: Any, on_back: Any, on_open_component: Any = None, /, **kwargs: Any) -> None:
        pass
    assert supports_on_open_component(builder) is True


def test_supports_callable_instance_two_arg() -> None:
    """9. Callable instance z dwuargumentowym __call__ -> False."""
    class BuilderClass:
        def __call__(self, parent: Any, on_back: Any) -> None:
            pass
    assert supports_on_open_component(BuilderClass()) is False


def test_supports_callable_instance_three_kw() -> None:
    """10. Callable instance z obsługą callbacka -> True."""
    class BuilderClass:
        def __call__(self, parent: Any, on_back: Any, on_open_component: Any = None) -> None:
            pass
    assert supports_on_open_component(BuilderClass()) is True


def test_supports_callable_class_constructor() -> None:
    """11. Callable class, sprawdzająca konstruktor klasy."""
    class BuilderClass:
        def __init__(self, parent: Any, on_back: Any, on_open_component: Any = None) -> None:
            pass
    assert supports_on_open_component(BuilderClass) is True


def test_supports_decorated_function() -> None:
    """12. Dekorowana funkcja zachowująca sygnaturę przez functools.wraps."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)
        return wrapper

    @decorator
    def builder(parent: Any, on_back: Any, on_open_component: Any = None) -> None:
        pass
    assert supports_on_open_component(builder) is True


def test_supports_signature_typeerror(monkeypatch: pytest.MonkeyPatch) -> None:
    """13. inspect.signature rzucające TypeError -> False."""
    def bad_sig(_obj: Any) -> None:
        raise TypeError("cant get signature")
    monkeypatch.setattr(inspect, "signature", bad_sig)

    def builder(parent: Any, on_back: Any, on_open_component: Any = None) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_signature_valueerror(monkeypatch: pytest.MonkeyPatch) -> None:
    """14. inspect.signature rzucające ValueError -> False."""
    def bad_sig(_obj: Any) -> None:
        raise ValueError("unsupported object")
    monkeypatch.setattr(inspect, "signature", bad_sig)

    def builder(parent: Any, on_back: Any, on_open_component: Any = None) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_similar_but_different_parameter_name() -> None:
    """15. Parametr o podobnej, ale innej nazwie -> False."""
    def builder(parent: Any, on_back: Any, on_open_comp: Any = None) -> None:
        pass
    assert supports_on_open_component(builder) is False


def test_supports_explicit_and_kwargs() -> None:
    """16. Jawny parametr plus **kwargs -> True."""
    def builder(parent: Any, on_back: Any, on_open_component: Any = None, **kwargs: Any) -> None:
        pass
    assert supports_on_open_component(builder) is True


# ---------------------------------------------------------------------------
# Testy invoke_inline_builder
# ---------------------------------------------------------------------------


def test_invoke_passes_parent() -> None:
    """17. Przekazuje dokładnie ten sam parent."""
    parent_sentinel = object()
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any) -> None:
        seen.append(parent)

    invoke_inline_builder(builder, parent_sentinel, lambda: None)  # type: ignore[arg-type]
    assert seen == [parent_sentinel]


def test_invoke_passes_on_back() -> None:
    """18. Przekazuje dokładnie ten sam on_back."""
    on_back_sentinel = lambda: None
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any) -> None:
        seen.append(on_back)

    invoke_inline_builder(builder, None, on_back_sentinel)  # type: ignore[arg-type]
    assert seen == [on_back_sentinel]


def test_invoke_two_arg_does_not_receive_callback() -> None:
    """19. Builder dwuargumentowy nie dostaje callbacka."""
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any) -> None:
        seen.append(True)

    cb = lambda f: None
    invoke_inline_builder(builder, None, lambda: None, on_open_component=cb)  # type: ignore[arg-type]
    assert seen == [True]


def test_invoke_positional_or_keyword_receives_callback() -> None:
    """20. Positional-or-keyword dostaje callback jako keyword."""
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any, on_open_component: Any = None) -> None:
        seen.append(on_open_component)

    cb = lambda f: None
    invoke_inline_builder(builder, None, lambda: None, on_open_component=cb)  # type: ignore[arg-type]
    assert seen == [cb]


def test_invoke_keyword_only_receives_callback() -> None:
    """21. Keyword-only dostaje callback jako keyword."""
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any, *, on_open_component: Any = None) -> None:
        seen.append(on_open_component)

    cb = lambda f: None
    invoke_inline_builder(builder, None, lambda: None, on_open_component=cb)  # type: ignore[arg-type]
    assert seen == [cb]


def test_invoke_kwargs_receives_callback() -> None:
    """22. **kwargs dostaje callback."""
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any, **kwargs: Any) -> None:
        seen.append(kwargs.get("on_open_component"))

    cb = lambda f: None
    invoke_inline_builder(builder, None, lambda: None, on_open_component=cb)  # type: ignore[arg-type]
    assert seen == [cb]


def test_invoke_optional_positional_only_called_once_with_two_args() -> None:
    """23. Optional positional-only jest wywołany raz z dwoma argumentami."""
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any, on_open_component: Any = "default", /) -> None:
        seen.append(on_open_component)

    cb = lambda f: None
    invoke_inline_builder(builder, None, lambda: None, on_open_component=cb)  # type: ignore[arg-type]
    assert seen == ["default"]


def test_invoke_required_positional_only_propagates_typeerror() -> None:
    """24. Required positional-only jest wywołany raz i propaguje TypeError."""
    calls = 0

    def builder(parent: Any, on_back: Any, on_open_component: Any, /) -> None:
        nonlocal calls
        calls += 1

    cb = lambda f: None
    with pytest.raises(TypeError):
        invoke_inline_builder(builder, None, lambda: None, on_open_component=cb)  # type: ignore[arg-type]
    assert calls == 0


def test_invoke_internal_typeerror_propagates_without_retry() -> None:
    """25. Wewnętrzny TypeError propaguje się bez retry."""
    calls = 0

    def builder(parent: Any, on_back: Any, on_open_component: Any = None) -> None:
        nonlocal calls
        calls += 1
        raise TypeError("internal type error")

    with pytest.raises(TypeError, match="internal type error"):
        invoke_inline_builder(builder, None, lambda: None)  # type: ignore[arg-type]
    assert calls == 1


def test_invoke_runtimeerror_propagates_without_retry() -> None:
    """26. RuntimeError propaguje się bez retry."""
    calls = 0

    def builder(parent: Any, on_back: Any) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        invoke_inline_builder(builder, None, lambda: None)  # type: ignore[arg-type]
    assert calls == 1


def test_invoke_valueerror_propagates_without_retry() -> None:
    """27. ValueError propaguje się bez retry."""
    calls = 0

    def builder(parent: Any, on_back: Any) -> None:
        nonlocal calls
        calls += 1
        raise ValueError("invalid value")

    with pytest.raises(ValueError, match="invalid value"):
        invoke_inline_builder(builder, None, lambda: None)  # type: ignore[arg-type]
    assert calls == 1


def test_invoke_called_exactly_once_on_success() -> None:
    """28. Builder jest wywołany dokładnie raz przy sukcesie."""
    calls = 0

    def builder(parent: Any, on_back: Any) -> str:
        nonlocal calls
        calls += 1
        return "view"

    res = invoke_inline_builder(builder, None, lambda: None)  # type: ignore[arg-type]
    assert res == "view"
    assert calls == 1


def test_invoke_called_exactly_once_on_failure() -> None:
    """29. Builder jest wywołany dokładnie raz przy błędzie."""
    calls = 0

    def builder(parent: Any, on_back: Any) -> None:
        nonlocal calls
        calls += 1
        raise ValueError("error")

    with pytest.raises(ValueError, match="error"):
        invoke_inline_builder(builder, None, lambda: None)  # type: ignore[arg-type]
    assert calls == 1


def test_invoke_returns_widget() -> None:
    """30. Wynik tk.Widget jest zwracany bez zmian."""
    root = tk.Tk()
    root.withdraw()
    widget = tk.Frame(root)

    def builder(parent: Any, on_back: Any) -> tk.Widget:
        return widget

    res = invoke_inline_builder(builder, root, lambda: None)
    assert res is widget
    root.destroy()


def test_invoke_returns_none() -> None:
    """31. None jest zwracane bez zmian."""
    def builder(parent: Any, on_back: Any) -> None:
        return None

    assert invoke_inline_builder(builder, None, lambda: None) is None  # type: ignore[arg-type]


def test_invoke_returns_arbitrary_object() -> None:
    """32. Dowolny inny obiekt jest zwracany bez zmian."""
    obj = object()

    def builder(parent: Any, on_back: Any) -> object:
        return obj

    assert invoke_inline_builder(builder, None, lambda: None) is obj  # type: ignore[arg-type]


def test_invoke_passes_none_callback_if_supported() -> None:
    """33. Callback None jest przekazywany jako keyword, jeśli sygnatura go obsługuje."""
    seen: list[Any] = []

    def builder(parent: Any, on_back: Any, on_open_component: Any = "default") -> None:
        seen.append(on_open_component)

    invoke_inline_builder(builder, None, lambda: None, on_open_component=None)  # type: ignore[arg-type]
    assert seen == [None]


# ---------------------------------------------------------------------------
# Izolacja i API
# ---------------------------------------------------------------------------


def test_exports_in_all() -> None:
    """34. Dokładne __all__."""
    assert "supports_on_open_component" in lib.__all__
    assert "invoke_inline_builder" in lib.__all__


def test_no_forbidden_imports() -> None:
    """35-39. Moduł nie importuje zakazanych bibliotek."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_inline_builder.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    for forbidden in (
        "customtkinter",
        "giclee_app.launcher",
        "launcher_studio",
        "inline_host",
        "Component",
    ):
        assert not any(forbidden in imp for imp in imported)


def test_no_layout_pack_calls() -> None:
    """40. Moduł nie wywołuje .pack()."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_inline_builder.py"
    )
    source = path.read_text(encoding="utf-8")
    assert ".pack(" not in source


def test_no_catch_and_retry_mechanism() -> None:
    """41. Moduł nie zawiera mechanizmu catch-and-retry po TypeError."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_inline_builder.py"
    )
    source = path.read_text(encoding="utf-8")
    assert "except TypeError" not in source
