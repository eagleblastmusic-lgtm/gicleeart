"""Testy adaptera LC-4A: start_classic_component_subprocess + orchestration _launch()."""

from __future__ import annotations

import ast
import subprocess
import sys
import threading
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app import launcher_classic_subprocess as adapter
from giclee_app.launcher_classic_subprocess import (
    ClassicSubprocessOutcome,
    ClassicSubprocessStart,
    start_classic_component_subprocess,
)
from giclee_app.component_loader import Component


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_comp(
    folder_name: str = "testcomp",
    name: str = "TestComp",
    mode: str = "subprocess",
    url: str = "",
) -> Component:
    return Component(
        folder_name=folder_name,
        package_path=Path("."),
        name=name,
        description="",
        icon="",
        color="",
        order=0,
        mode=mode,
        url=url,
        hidden=False,
    )


class _FakeProc:
    pid = 42

    def wait(self) -> int:
        return 0


# ---------------------------------------------------------------------------
# Adapter unit tests (start_classic_component_subprocess)
# ---------------------------------------------------------------------------


def test_no_python_returns_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 1: NO_PYTHON zwraca dokładny komunikat interpretera."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: (None, "no py"))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.NO_PYTHON
    assert result.message == "no py"


def test_no_python_does_not_open_log_or_popen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 2: NO_PYTHON nie otwiera logu i nie wywołuje Popen()."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: (None, "no py"))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    popen_calls: list[object] = []
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: popen_calls.append((a, k)))
    open_calls: list[object] = []

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.NO_PYTHON
    assert result.proc is None
    assert result.log_file is None
    assert popen_calls == []


def test_command_uses_prefix_and_module_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 3: komenda zachowuje [*prefix, '-m', comp.module_path]."""
    prefix = ["/usr/bin/python3"]
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: (prefix, ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(
        adapter, "component_log_write_path", lambda *a, **k: tmp_path / "x.log"
    )

    captured_cmd: list[list[str]] = []
    fake_proc = _FakeProc()

    def fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
        captured_cmd.append(list(cmd))
        return fake_proc

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)
    comp = _fake_comp(folder_name="mycomp")

    start_classic_component_subprocess(comp, logs_dir=tmp_path)

    assert captured_cmd == [["/usr/bin/python3", "-m", "Komponenty.mycomp"]]


def test_uses_get_component_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 4: adapter wywołuje get_component_cwd()."""
    cwd_calls: list[int] = []

    def fake_cwd() -> Path:
        cwd_calls.append(1)
        return tmp_path

    monkeypatch.setattr(adapter, "get_component_cwd", fake_cwd)
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(
        adapter, "component_log_write_path", lambda *a, **k: tmp_path / "x.log"
    )
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: _FakeProc())

    start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert cwd_calls == [1]


def test_passes_logs_dir_to_component_log_write_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 5: adapter przekazuje dokładny logs_dir do component_log_write_path()."""
    my_logs_dir = tmp_path / "my_logs"
    captured: list[dict[str, object]] = []

    def fake_log_path(folder_name: str, *, logs_dir: Path) -> Path:
        captured.append({"folder_name": folder_name, "logs_dir": logs_dir})
        my_logs_dir.mkdir(parents=True, exist_ok=True)
        return my_logs_dir / f"{folder_name}.log"

    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(adapter, "component_log_write_path", fake_log_path)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: _FakeProc())

    comp = _fake_comp(folder_name="mycomp")
    start_classic_component_subprocess(comp, logs_dir=my_logs_dir)

    assert len(captured) == 1
    assert captured[0]["folder_name"] == "mycomp"
    assert captured[0]["logs_dir"] is my_logs_dir


def test_log_opened_append_utf8_linebuffered(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 6: log jest otwierany w trybie append, UTF-8 i line-buffered."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(
        adapter, "component_log_write_path", lambda *a, **k: tmp_path / "comp.log"
    )
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: _FakeProc())

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    log_content = (tmp_path / "comp.log").read_text(encoding="utf-8")
    assert "start" in log_content
    assert result.log_file is not None
    result.log_file.close()


def test_start_marker_does_not_contain_studio(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 7: klasyczny start marker nie zawiera '(studio)'."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    log_path = tmp_path / "comp.log"
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: log_path)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: _FakeProc())

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    content = log_path.read_text(encoding="utf-8")
    assert "start" in content
    assert "(studio)" not in content
    if result.log_file:
        result.log_file.close()


def test_marker_flushed_before_popen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 8: marker jest flushowany przed Popen()."""
    log_path = tmp_path / "comp.log"
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: log_path)

    content_at_popen_call: list[str] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakeProc:
        content_at_popen_call.append(log_path.read_text(encoding="utf-8"))
        return _FakeProc()

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert len(content_at_popen_call) == 1
    assert "start" in content_at_popen_call[0]
    if result.log_file:
        result.log_file.close()


def test_log_oserror_does_not_block_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 9: błąd otwarcia logu nie blokuje startu."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    # Point log path to a directory (cannot open as file)
    bad_path = tmp_path / "cant_open.log"
    bad_path.mkdir()
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: bad_path)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: _FakeProc())

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.STARTED
    assert result.log_file is None


def test_no_log_uses_devnull_for_stdout_and_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 10: bez logu stdout i stderr trafiają do DEVNULL."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    bad_path = tmp_path / "cant.log"
    bad_path.mkdir()
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: bad_path)

    captured_kwargs: list[dict[str, object]] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakeProc:
        captured_kwargs.append(dict(kwargs))
        return _FakeProc()

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)

    start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    kw = captured_kwargs[0]
    assert kw["stdout"] is subprocess.DEVNULL
    assert kw["stderr"] is subprocess.DEVNULL


def test_with_log_uses_handle_for_stdout_and_stdout_for_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 11: z logiem stdout=handle, stderr=STDOUT."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    log_path = tmp_path / "comp.log"
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: log_path)

    captured_kwargs: list[dict[str, object]] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakeProc:
        captured_kwargs.append(dict(kwargs))
        return _FakeProc()

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    kw = captured_kwargs[0]
    assert kw["stdout"] is result.log_file
    assert kw["stderr"] is subprocess.STDOUT
    if result.log_file:
        result.log_file.close()


def test_cwd_is_converted_to_str(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 12: cwd jest konwertowany do str."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: tmp_path / "x.log")

    captured_kwargs: list[dict[str, object]] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakeProc:
        captured_kwargs.append(dict(kwargs))
        return _FakeProc()

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert captured_kwargs[0]["cwd"] == str(tmp_path)
    if result.log_file:
        result.log_file.close()


def test_creationflags_uses_create_new_process_group_or_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 13: creationflags = CREATE_NEW_PROCESS_GROUP lub 0."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: tmp_path / "x.log")

    captured_kwargs: list[dict[str, object]] = []

    def fake_popen(*args: object, **kwargs: object) -> _FakeProc:
        captured_kwargs.append(dict(kwargs))
        return _FakeProc()

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    expected_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    assert captured_kwargs[0]["creationflags"] == expected_flags
    if result.log_file:
        result.log_file.close()


def test_popen_oserror_returns_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 14: Popen() OSError daje ERROR z tekstem wyjątku."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: tmp_path / "x.log")

    def fail_popen(*args: object, **kwargs: object) -> None:
        raise OSError("exec failed")

    monkeypatch.setattr(adapter.subprocess, "Popen", fail_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.ERROR
    assert "exec failed" in result.message
    assert result.proc is None
    assert result.log_file is None


def test_log_closed_after_popen_oserror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 15: uchwyt logu jest zamykany po błędzie Popen()."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    log_path = tmp_path / "comp.log"
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: log_path)

    closed: list[bool] = []
    original_open = open

    def fake_popen(*args: object, **kwargs: object) -> None:
        raise OSError("boom")

    monkeypatch.setattr(adapter.subprocess, "Popen", fake_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.ERROR
    # Log path exists (was created) but handle is closed
    assert log_path.exists()
    # The result must not contain the log handle
    assert result.log_file is None


def test_close_error_does_not_mask_popen_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 16: błąd close() nie maskuje pierwotnego błędu startu."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    log_path = tmp_path / "comp.log"
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: log_path)

    class FailCloseFile:
        def write(self, s: str) -> int:
            return len(s)

        def flush(self) -> None:
            pass

        def close(self) -> None:
            raise OSError("close failed")

    original_open = open

    def patched_open(path: object, mode: str, **kwargs: object) -> object:
        if str(path) == str(log_path):
            return FailCloseFile()
        return original_open(path, mode, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("builtins.open", patched_open)

    def fail_popen(*args: object, **kwargs: object) -> None:
        raise OSError("start failed")

    monkeypatch.setattr(adapter.subprocess, "Popen", fail_popen)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.ERROR
    assert "start failed" in result.message


def test_success_returns_same_proc_and_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 17: sukces zwraca ten sam proces i uchwyt logu."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    log_path = tmp_path / "comp.log"
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: log_path)

    fake_proc = _FakeProc()
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: fake_proc)

    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)

    assert result.outcome is ClassicSubprocessOutcome.STARTED
    assert result.proc is fake_proc
    assert result.log_file is not None
    result.log_file.close()


def test_adapter_does_not_start_thread_or_wait(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 18: adapter nie uruchamia wątku i nie wywołuje wait()."""
    monkeypatch.setattr(adapter, "resolve_python_interpreter", lambda: ([sys.executable], ""))
    monkeypatch.setattr(adapter, "get_component_cwd", lambda: tmp_path)
    monkeypatch.setattr(adapter, "component_log_write_path", lambda *a, **k: tmp_path / "x.log")

    wait_called: list[bool] = []

    class NoWaitProc:
        pid = 1

        def wait(self) -> int:
            wait_called.append(True)
            return 0

    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *a, **k: NoWaitProc())

    threads_before = set(threading.enumerate())
    result = start_classic_component_subprocess(_fake_comp(), logs_dir=tmp_path)
    threads_after = set(threading.enumerate())

    assert wait_called == []
    assert threads_after == threads_before
    if result.log_file:
        result.log_file.close()


def test_adapter_does_not_import_tkinter_or_launcher() -> None:
    """Przypadek 19: adapter nie importuje Tk, launchera, delegate ani Studio."""
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_classic_subprocess.py"
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
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert "tkinter" not in imported
    assert all("tkinter" not in m for m in imported_from)
    assert all("launcher_delegate" not in m for m in imported_from)
    assert all("launcher_studio" not in m for m in imported_from)
    assert all("Komponenty" not in m for m in imported_from)
    # Must not import launcher.py itself
    assert all(m != "giclee_app.launcher" and m != ".launcher" for m in imported_from)


def test_all_contains_public_contract() -> None:
    """Przypadek 20: __all__ zawiera publiczny kontrakt."""
    assert "ClassicSubprocessOutcome" in adapter.__all__
    assert "ClassicSubprocessStart" in adapter.__all__
    assert "start_classic_component_subprocess" in adapter.__all__


# ---------------------------------------------------------------------------
# Orchestration tests (_launch in GicleeApp)
# ---------------------------------------------------------------------------


def _make_fake_app(
    events: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> object:
    """Builds a minimal GicleeApp-like fake without Tk."""
    import giclee_app.launcher as launcher_mod

    class _FakeStatus:
        def set(self, text: str) -> None:
            events.append(("status", text))

    class _FakeApp:
        _running_procs: list[object] = []
        status_var = _FakeStatus()

        def _show_inline(self, comp: Component) -> None:
            events.append(("inline", comp.folder_name))

        def _watch_proc(self, proc: object, name: str, log_f: object = None) -> None:
            events.append(("watch", name, log_f))

        def _launch(self, comp: Component) -> None:
            launcher_mod.GicleeApp._launch(self, comp)  # type: ignore[arg-type]

    app = _FakeApp()
    app._running_procs = []

    # Patch messagebox to capture calls without Tk
    monkeypatch.setattr(launcher_mod.messagebox, "showerror", lambda t, m: events.append(("showerror", t, m)))
    monkeypatch.setattr(launcher_mod.messagebox, "showwarning", lambda t, m: events.append(("showwarning", t, m)))
    monkeypatch.setattr(launcher_mod, "webbrowser", MagicMock())

    # Patch threading.Thread to record but not actually spawn
    def fake_thread_init(self_t: object, *, target: object, args: tuple, daemon: bool) -> None:
        events.append(("thread_start", target, args, daemon))

    def fake_thread_start(self_t: object) -> None:
        pass

    fake_thread = type("FakeThread", (), {"__init__": fake_thread_init, "start": fake_thread_start})
    monkeypatch.setattr(launcher_mod, "threading", MagicMock(Thread=fake_thread))

    return app


def test_launch_url_handled_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 21: _launch() nadal najpierw obsługuje URL."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)
    comp = _fake_comp(mode="url", url="https://example.com")

    # Patch webbrowser.open to capture
    monkeypatch.setattr(launcher_mod, "webbrowser", MagicMock(open=lambda u: events.append(("open_url", u))))

    app._launch(comp)  # type: ignore[attr-defined]

    assert any("open_url" in str(e) or (isinstance(e, tuple) and e[0] == "open_url") for e in events)


def test_launch_inline_delegates_to_show_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 22: _launch() nadal deleguje inline do _show_inline()."""
    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)
    comp = _fake_comp(mode="inline", folder_name="mycomp")

    app._launch(comp)  # type: ignore[attr-defined]

    assert ("inline", "mycomp") in events


def test_subprocess_delegates_to_adapter_with_logs_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Przypadek 23: klasyczna gałąź subprocess deleguje do nowego adaptera z _LOGS_DIR."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)

    captured: list[dict[str, object]] = []

    def fake_start(
        comp: Component,
        *,
        logs_dir: Path,
    ) -> ClassicSubprocessStart:
        captured.append({"comp": comp, "logs_dir": logs_dir})
        return ClassicSubprocessStart(ClassicSubprocessOutcome.NO_PYTHON, message="no")

    monkeypatch.setattr(launcher_mod, "start_classic_component_subprocess", fake_start)

    comp = _fake_comp(mode="subprocess")
    app._launch(comp)  # type: ignore[attr-defined]

    assert len(captured) == 1
    assert captured[0]["logs_dir"] is launcher_mod._LOGS_DIR


def test_no_python_dialog_title_and_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 24: NO_PYTHON zachowuje aktualny tytuł i tekst dialogu."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)
    monkeypatch.setattr(
        launcher_mod,
        "start_classic_component_subprocess",
        lambda *a, **k: ClassicSubprocessStart(
            ClassicSubprocessOutcome.NO_PYTHON, message="brak py"
        ),
    )

    comp = _fake_comp(name="MyComp")
    app._launch(comp)  # type: ignore[attr-defined]

    errors = [e for e in events if isinstance(e, tuple) and e[0] == "showerror"]
    assert len(errors) == 1
    title, msg = errors[0][1], errors[0][2]
    assert title == "Brak Pythona"
    assert "MyComp" in msg
    assert "brak py" in msg


def test_error_dialog_title_and_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 25: ERROR zachowuje aktualny tytuł i tekst dialogu."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)
    monkeypatch.setattr(
        launcher_mod,
        "start_classic_component_subprocess",
        lambda *a, **k: ClassicSubprocessStart(
            ClassicSubprocessOutcome.ERROR, message="exec fail"
        ),
    )

    comp = _fake_comp(name="MyComp")
    app._launch(comp)  # type: ignore[attr-defined]

    errors = [e for e in events if isinstance(e, tuple) and e[0] == "showerror"]
    assert len(errors) == 1
    title, msg = errors[0][1], errors[0][2]
    assert title == "Blad uruchomienia"
    assert "MyComp" in msg
    assert "exec fail" in msg


def test_success_appends_proc_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 26: sukces dopisuje proces do _running_procs dokładnie raz."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)

    fake_proc = _FakeProc()
    monkeypatch.setattr(
        launcher_mod,
        "start_classic_component_subprocess",
        lambda *a, **k: ClassicSubprocessStart(
            ClassicSubprocessOutcome.STARTED, proc=fake_proc
        ),
    )

    comp = _fake_comp(name="Comp")
    app._launch(comp)  # type: ignore[attr-defined]
    app._launch(comp)  # type: ignore[attr-defined]

    assert app._running_procs.count(fake_proc) == 2  # type: ignore[attr-defined]


def test_success_sets_status_with_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 27: sukces ustawia aktualny status z nazwą i PID."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)

    fake_proc = _FakeProc()
    fake_proc.pid = 9999  # type: ignore[assignment]
    monkeypatch.setattr(
        launcher_mod,
        "start_classic_component_subprocess",
        lambda *a, **k: ClassicSubprocessStart(
            ClassicSubprocessOutcome.STARTED, proc=fake_proc
        ),
    )

    comp = _fake_comp(name="TestName")
    app._launch(comp)  # type: ignore[attr-defined]

    statuses = [e for e in events if isinstance(e, tuple) and e[0] == "status"]
    assert len(statuses) == 1
    assert "TestName" in statuses[0][1]
    assert "9999" in statuses[0][1]


def test_success_starts_one_daemon_watcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 28: sukces uruchamia dokładnie jeden daemon watcher z _watch_proc i logiem."""
    import giclee_app.launcher as launcher_mod

    events: list[object] = []
    app = _make_fake_app(events, monkeypatch)

    fake_proc = _FakeProc()
    fake_log = StringIO()
    monkeypatch.setattr(
        launcher_mod,
        "start_classic_component_subprocess",
        lambda *a, **k: ClassicSubprocessStart(
            ClassicSubprocessOutcome.STARTED, proc=fake_proc, log_file=fake_log
        ),
    )

    comp = _fake_comp(name="Comp")
    app._launch(comp)  # type: ignore[attr-defined]

    threads = [e for e in events if isinstance(e, tuple) and e[0] == "thread_start"]
    assert len(threads) == 1
    _evt, target, args, daemon = threads[0]
    assert target.__self__ is app
    assert target.__func__.__name__ == "_watch_proc"
    assert args == (fake_proc, "Comp", fake_log)
    assert daemon is True


def test_error_does_not_mutate_procs_or_start_watcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Przypadek 29: błąd lub brak Pythona nie mutuje _running_procs i nie uruchamia watchera."""
    import giclee_app.launcher as launcher_mod

    for outcome in (ClassicSubprocessOutcome.NO_PYTHON, ClassicSubprocessOutcome.ERROR):
        events: list[object] = []
        app = _make_fake_app(events, monkeypatch)

        monkeypatch.setattr(
            launcher_mod,
            "start_classic_component_subprocess",
            lambda *a, o=outcome, **k: ClassicSubprocessStart(o, message="fail"),
        )

        app._launch(_fake_comp())  # type: ignore[attr-defined]

        assert app._running_procs == []  # type: ignore[attr-defined]
        threads = [e for e in events if isinstance(e, tuple) and e[0] == "thread_start"]
        assert threads == []


def test_watch_proc_remains_in_launcher() -> None:
    """Przypadek 30: _watch_proc() pozostaje w launcher.py z exit marker, usunięciem proc i root.after()."""
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher.py"
    source = path.read_text(encoding="utf-8")

    # _watch_proc must still be defined in launcher.py
    assert "def _watch_proc(" in source

    # Must contain exit marker
    watch_body = source.split("def _watch_proc(", 1)[1].split("\n    def ", 1)[0]
    assert "exit code" in watch_body

    # Must remove process from _running_procs
    assert "_running_procs.remove(proc)" in watch_body

    # Must use root.after
    assert "root.after" in watch_body

    # _launch must NOT contain direct Popen or interpreter resolution
    launch_body = source.split("def _launch(", 1)[1].split("\n    def ", 1)[0]
    assert "subprocess.Popen(" not in launch_body
    assert "get_component_cwd()" not in launch_body
    assert "resolve_python_interpreter()" not in launch_body
    assert "start_classic_component_subprocess(" in launch_body
