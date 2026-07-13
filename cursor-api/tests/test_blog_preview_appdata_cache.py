from __future__ import annotations

from pathlib import Path

import pytest

from Komponenty.blog import preview
from tools.repository_safety.runtime_writes import scan_python_source


def _parsed_preview() -> dict[str, object]:
    return {
        "topic": "Zażółć gęślą 🖼️",
        "category": "Fine Art",
        "image_hint": "Claude Monet",
        "languages": {
            "pl": {
                "title": "Tytuł próby",
                "body_html": "<p>Treść próby</p>",
                "summary_html": "Podsumowanie",
                "seo_title": "SEO",
                "seo_description": "Opis",
                "tags": ["sztuka", "giclée"],
            }
        },
    }


def _configure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    local_root = tmp_path / "local-root"
    legacy = tmp_path / "repo" / "cursor-api" / "Komponenty" / "blog" / "data" / "preview.html"
    external = local_root / "data" / "Komponenty" / "blog" / "data" / "preview.html"

    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setattr(preview, "_LEGACY_PREVIEW_FILE", legacy)
    monkeypatch.setattr(preview, "_DEFAULT_PREVIEW_FILE", legacy)
    monkeypatch.setattr(preview, "_PREVIEW_FILE", legacy)
    return legacy, external


def test_preview_is_written_atomically_to_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text("legacy-preview", encoding="utf-8")
    before = legacy.read_bytes()
    calls: list[Path] = []
    real_atomic_write = preview.atomic_write_text

    def _record_atomic_write(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        real_atomic_write(path, text, encoding=encoding)

    monkeypatch.setattr(preview, "atomic_write_text", _record_atomic_write)

    result = preview.build_preview_html(_parsed_preview())

    assert result == external
    assert calls == [external]
    assert external.is_file()
    rendered = external.read_text(encoding="utf-8")
    assert "Zażółć gęślą 🖼️" in rendered
    assert "Tytuł próby" in rendered
    assert legacy.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_explicit_preview_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "override" / "custom-preview.html"
    monkeypatch.setattr(preview, "_PREVIEW_FILE", override)

    result = preview.build_preview_html(_parsed_preview())

    assert result == override
    assert override.is_file()
    assert not external.exists()


def test_open_preview_uses_external_file_uri(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(preview.webbrowser, "open", lambda uri: opened.append(uri) or True)

    result = preview.open_preview_in_browser(_parsed_preview())

    assert result == external
    assert opened == [external.as_uri()]


def test_runtime_write_inventory_no_longer_flags_blog_preview() -> None:
    source_path = Path(preview.__file__)
    findings, error = scan_python_source(
        "Komponenty/blog/preview.py",
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
