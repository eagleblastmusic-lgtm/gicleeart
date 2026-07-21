from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import safe_theme_writes, service


def test_homepage_json_writers_are_atomic_and_readable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index_path = tmp_path / "templates" / "index.json"
    settings_path = tmp_path / "config" / "settings_data.json"
    calls: list[Path] = []

    monkeypatch.setattr(service, "index_template_path", lambda: index_path)
    monkeypatch.setattr(service, "settings_data_path", lambda: settings_path)

    def atomic_spy(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)

    monkeypatch.setattr(safe_theme_writes, "atomic_write_text", atomic_spy)

    service.save_index_template({"sections": {}, "order": []})
    service.save_theme_settings({"current": {"home_flow_scroll_mode": "native-v2"}})

    assert calls == [index_path, settings_path]
    assert json.loads(service._strip_json_header(index_path.read_text(encoding="utf-8")))["order"] == []
    assert (
        json.loads(service._strip_json_header(settings_path.read_text(encoding="utf-8")))["current"]
        ["home_flow_scroll_mode"]
        == "native-v2"
    )


def test_revision_stamp_replaces_previous_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = tmp_path / "giclee-home-sections.js"
    asset.write_text(
        "window.GICLEE_HOME_STACK = true;\n"
        "window.GICLEE_HOME_BUILD_REVISION = \"old\";\n",
        encoding="utf-8",
    )

    def atomic_spy(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        path.write_text(text, encoding=encoding)

    monkeypatch.setattr(safe_theme_writes, "atomic_write_text", atomic_spy)

    revision = safe_theme_writes._stamp_build_revision(asset, "new-revision")
    text = asset.read_text(encoding="utf-8")

    assert revision == "new-revision"
    assert "old" not in text
    assert text.count("GICLEE_HOME_BUILD_REVISION") == 1
    assert 'window.GICLEE_HOME_BUILD_REVISION = "new-revision";' in text


def test_theme_dev_revision_wait_confirms_served_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, _limit: int) -> bytes:
            return b'window.GICLEE_HOME_BUILD_REVISION = "abc123";'

    monkeypatch.setattr(service, "theme_dev_port_open", lambda: True)
    monkeypatch.setattr(safe_theme_writes, "urlopen", lambda *_args, **_kwargs: Response())

    assert safe_theme_writes.wait_for_theme_dev_revision("abc123", timeout_sec=0.5) is True
