from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PREVIEW_PATH = REPO_ROOT / "cursor-api" / "Komponenty" / "blog" / "preview.py"
TEST_PATH = REPO_ROOT / "cursor-api" / "tests" / "test_blog_preview_appdata_cache.py"
DOC_PATH = (
    REPO_ROOT
    / "cursor-api"
    / "docs"
    / "repository_safety"
    / "BLOG_PREVIEW_CACHE.md"
)


def replace_once(source: str, old: str, new: str, *, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)


source = PREVIEW_PATH.read_text(encoding="utf-8")
source = replace_once(
    source,
    "Wyjscie: pojedynczy plik `data/preview.html` zawierajacy:",
    (
        "Wyjscie: pojedynczy regenerowalny plik HTML w Local AppData; "
        "legacy `data/preview.html` pozostaje jedynie historyczna lokalizacja."
    ),
    label="module contract",
)
source = replace_once(
    source,
    """from pathlib import Path
from typing import Any

_COMPONENT_DIR = Path(__file__).resolve().parent
_PREVIEW_FILE = _COMPONENT_DIR / "data" / "preview.html"

_LANG_LABELS = [
""",
    """from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, cache_path

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_PREVIEW_FILE = _COMPONENT_DIR / "data" / "preview.html"
_DEFAULT_PREVIEW_FILE = _LEGACY_PREVIEW_FILE
_PREVIEW_FILE = _DEFAULT_PREVIEW_FILE
_PREVIEW_CACHE = cache_path(
    "Komponenty/blog/data/preview.html",
    legacy=_LEGACY_PREVIEW_FILE,
)


def _resolved_preview_file() -> Path:
    """Return an explicit override or the external Local AppData cache path."""

    current = Path(_PREVIEW_FILE)
    if current != _DEFAULT_PREVIEW_FILE:
        return current
    return _PREVIEW_CACHE.write_path


_LANG_LABELS = [
""",
    label="AppData imports and resolver",
)
source = replace_once(
    source,
    "    _PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)\n",
    "    preview_file = _resolved_preview_file()\n",
    label="target resolution",
)
source = replace_once(
    source,
    """    _PREVIEW_FILE.write_text(full, encoding="utf-8")
    return _PREVIEW_FILE
""",
    """    atomic_write_text(preview_file, full)
    return preview_file
""",
    label="atomic external write",
)
PREVIEW_PATH.write_text(source, encoding="utf-8")

TEST_PATH.write_text(
    '''from __future__ import annotations

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
''',
    encoding="utf-8",
)

DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
DOC_PATH.write_text(
    '''# Blog preview cache outside the checkout

`Komponenty/blog/preview.py` generates a disposable multilingual HTML preview.
The file is runtime cache, not source code, and must not be written next to the
component implementation.

## Runtime contract

- new output:
  `%LOCALAPPDATA%/GicleeArt/GicleeApp/data/Komponenty/blog/data/preview.html`,
- the historical `Komponenty/blog/data/preview.html` path is never modified,
- `_PREVIEW_FILE` remains an explicit override point for tests and controlled callers,
- normal writes use `giclee_app.app_paths.cache_path`,
- replacement is atomic through `atomic_write_text`,
- `build_preview_html()` and `open_preview_in_browser()` return/use the resolved
  external path.

No automatic copy or deletion of a historical preview is needed because the file
is fully regenerable.

## Tests

`tests/test_blog_preview_appdata_cache.py` verifies:

1. Local AppData output and preservation of a legacy file,
2. atomic replacement and Unicode content,
3. compatibility of an explicit `_PREVIEW_FILE` override,
4. browser opening of the external file URI,
5. removal of `Komponenty/blog/preview.py` from runtime-write inventory findings.
''',
    encoding="utf-8",
)

print("Prepared blog preview AppData patch:")
for path in (PREVIEW_PATH, TEST_PATH, DOC_PATH):
    print(path.relative_to(REPO_ROOT))
