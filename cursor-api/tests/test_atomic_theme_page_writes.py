from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty._shared.theme_page_editor import safe_writes, service_base


def test_shared_page_save_uses_atomic_writer_and_validates_readback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe_writes.install_atomic_theme_page_writes()
    target = tmp_path / "templates" / "page.contact.json"
    calls: list[Path] = []

    def atomic_spy(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)

    monkeypatch.setattr(safe_writes, "atomic_write_text", atomic_spy)

    service_base.save_template_to_path(target, {"sections": {"hero": {"type": "image"}}})

    assert calls == [target]
    raw = target.read_text(encoding="utf-8")
    assert raw.startswith("/*")
    parsed = json.loads(service_base._strip_json_header(raw))
    assert parsed["sections"]["hero"]["type"] == "image"


def test_shared_page_save_failure_keeps_previous_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe_writes.install_atomic_theme_page_writes()
    target = tmp_path / "templates" / "page.faq.json"
    target.parent.mkdir(parents=True)
    target.write_text("previous-content", encoding="utf-8")

    def fail_before_replace(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        raise OSError("simulated atomic write failure")

    monkeypatch.setattr(safe_writes, "atomic_write_text", fail_before_replace)

    with pytest.raises(OSError, match="simulated"):
        service_base.save_template_to_path(target, {"sections": {}})

    assert target.read_text(encoding="utf-8") == "previous-content"
