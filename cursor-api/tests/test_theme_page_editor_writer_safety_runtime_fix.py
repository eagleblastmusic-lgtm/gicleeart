"""Regresja WS-1.1: kontekst przycisków jest rozwiązywany po budowie UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor import writer_safety as ws
from Komponenty._shared.theme_page_editor.writer_safety_runtime_fix import (
    install_deferred_context_fix,
)


class _FakeWidget:
    def __init__(self, command: Any = None, **kwargs: Any) -> None:
        self.command = command
        self.kwargs = kwargs

    def pack(self, **_kwargs: Any) -> None:
        return None


class _FakeTtk:
    def Button(self, _master: Any = None, *args: Any, **kwargs: Any) -> _FakeWidget:
        payload = dict(kwargs)
        command = payload.pop("command", None)
        return _FakeWidget(command=command, args=args, **payload)


class _FakeMaster:
    def __init__(self) -> None:
        self.idle_callbacks: list[Any] = []

    def after_idle(self, callback: Any) -> None:
        self.idle_callbacks.append(callback)


def _config(tmp_path: Path) -> PageEditorConfig:
    return PageEditorConfig(
        component_id="gicleeframe",
        component_dir=tmp_path,
        app_title="Giclée Frame",
        intro_title="Giclée Frame",
        intro_body="Test",
        template_rel="templates/page.giclee-frame.json",
        preview_path="/pages/giclee-frame",
        variant_id_prefix="gf",
        zones=(),
    )


def test_save_context_is_resolved_only_after_nested_function_exists(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    install_deferred_context_fix()
    captured: list[Any] = []
    apply_contexts: list[Any] = []
    monkeypatch.setattr(ws, "_run_variant_only_save", lambda context: captured.append(context))
    monkeypatch.setattr(
        ws,
        "_ensure_apply_button",
        lambda _master, context, _ttk: apply_contexts.append(context),
    )

    config = _config(tmp_path)
    host = object()
    master = _FakeMaster()
    proxy = ws._WriterSafetyTtkProxy(_FakeTtk())

    ws._BUILD_STACK.append((host, config))
    try:
        def command() -> Any:
            return _save_all()

        button = proxy.Button(master, text="Zapisz", command=command)

        state = {"variant_id": "gf3"}
        status_var = None

        def _confirm_save(label: str) -> dict[str, str]:
            return {"label": label}

        def _refresh_zone_list() -> None:
            state["refreshed"] = True

        def _save_all() -> Any:
            pending = _confirm_save("Zapisz")
            if pending:
                state["saved"] = True
                _refresh_zone_list()
            return status_var
    finally:
        ws._BUILD_STACK.pop()

    assert captured == []
    button.command()
    assert len(captured) == 1
    context = captured[0]
    assert context.state is state
    assert context.confirm_save is _confirm_save
    assert context.refresh_zone_list is _refresh_zone_list
    assert context.config is config

    assert len(master.idle_callbacks) == 1
    master.idle_callbacks[0]()
    assert len(apply_contexts) == 1
    assert apply_contexts[0].confirm_save is _confirm_save
    assert apply_contexts[0].state is state


def test_deploy_context_is_also_resolved_on_click(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    install_deferred_context_fix()
    captured: list[Any] = []
    monkeypatch.setattr(ws, "_open_deploy_only", lambda context: captured.append(context))

    config = _config(tmp_path)
    host = object()
    master = _FakeMaster()
    proxy = ws._WriterSafetyTtkProxy(_FakeTtk())

    ws._BUILD_STACK.append((host, config))
    try:
        def command() -> Any:
            return _deploy()

        button = proxy.Button(master, text="Wdróż motyw…", command=command)

        state = {"dirty": True}
        status_var = None

        def _deploy() -> Any:
            state["called"] = True
            return status_var
    finally:
        ws._BUILD_STACK.pop()

    assert captured == []
    button.command()
    assert len(captured) == 1
    assert captured[0].state is state
    assert captured[0].config is config
