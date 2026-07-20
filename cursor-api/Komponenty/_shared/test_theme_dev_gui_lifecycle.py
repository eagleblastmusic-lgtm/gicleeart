from __future__ import annotations

from pathlib import Path


SOURCE_PATH = Path(__file__).with_name("theme_dev_gui.py")


def _source() -> str:
    return SOURCE_PATH.read_text(encoding="utf-8")


def test_theme_dev_log_writes_are_marshaled_to_tk_main_thread() -> None:
    source = _source()

    assert "threading.current_thread() is threading.main_thread()" in source
    assert "master.after(0, write)" in source


def test_theme_dev_callbacks_ignore_destroyed_log_window() -> None:
    source = _source()

    assert "def window_alive() -> bool:" in source
    assert "if not window_alive():" in source
    assert "except tk.TclError:" in source
    assert "if not log.winfo_exists():" in source
