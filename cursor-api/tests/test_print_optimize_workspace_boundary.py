from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from tools.repository_safety.runtime_writes import scan_python_source

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPONENT_DIR = _REPO_ROOT / "Komponenty" / "print_optimize"
_PATHS_FILE = _COMPONENT_DIR / "paths.py"
_GUI_FILE = _COMPONENT_DIR / "gui.py"
_CLI_FILE = _COMPONENT_DIR / "cli.py"


def _load_paths_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"_print_optimize_paths_boundary_{id(object())}",
        _PATHS_FILE,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(path: Path) -> tuple[bool, tuple[tuple[str, bytes], ...]]:
    if not path.is_dir():
        return False, ()
    files = tuple(
        sorted(
            (str(item.relative_to(path)), item.read_bytes())
            for item in path.rglob("*")
            if item.is_file()
        )
    )
    return True, files


def _reset_public_defaults(paths: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "TEST_PHOTOS_DIR", paths._DEFAULT_TEST_PHOTOS_DIR)
    monkeypatch.setattr(paths, "WW_PAIRS_DIR", paths._DEFAULT_WW_PAIRS_DIR)


def test_read_only_default_resolvers_use_local_appdata_without_creating_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    paths = _load_paths_module()
    _reset_public_defaults(paths, monkeypatch)

    test_photos = paths.test_photos_dir()
    ww_pairs = paths.ww_pairs_dir()

    assert test_photos == local_root / "data" / "Komponenty" / "print_optimize" / "data" / "test_photos"
    assert ww_pairs == local_root / "data" / "Komponenty" / "print_optimize" / "data" / "ww_pairs"
    assert not test_photos.exists()
    assert not ww_pairs.exists()


def test_ensure_data_dirs_creates_only_external_workspace_and_leaves_legacy_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    legacy_test = tmp_path / "legacy" / "test_photos"
    legacy_pairs = tmp_path / "legacy" / "ww_pairs"
    legacy_test.mkdir(parents=True)
    legacy_pairs.mkdir(parents=True)
    (legacy_test / "user-photo.jpg").write_bytes(b"photo")
    (legacy_pairs / "calibration_report.json").write_bytes(b"{}")

    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    paths = _load_paths_module()
    monkeypatch.setattr(paths, "_LEGACY_TEST_PHOTOS_DIR", legacy_test)
    monkeypatch.setattr(paths, "_LEGACY_WW_PAIRS_DIR", legacy_pairs)
    _reset_public_defaults(paths, monkeypatch)
    before_test = _snapshot(legacy_test)
    before_pairs = _snapshot(legacy_pairs)

    paths.ensure_data_dirs()

    assert paths.test_photos_dir().is_dir()
    assert paths.ww_pairs_dir().is_dir()
    assert _snapshot(legacy_test) == before_test
    assert _snapshot(legacy_pairs) == before_pairs
    assert list(paths.test_photos_dir().iterdir()) == []
    assert list(paths.ww_pairs_dir().iterdir()) == []


@pytest.mark.parametrize(
    ("constant_name", "resolver_name"),
    [
        ("TEST_PHOTOS_DIR", "test_photos_dir"),
        ("WW_PAIRS_DIR", "ww_pairs_dir"),
    ],
)
def test_explicit_workspace_override_remains_authoritative(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    constant_name: str,
    resolver_name: str,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    paths = _load_paths_module()
    override = tmp_path / f"chosen-{constant_name.lower()}"
    monkeypatch.setattr(paths, constant_name, override)
    resolver = getattr(paths, resolver_name)

    assert resolver() == override
    assert not override.exists()
    assert resolver(for_write=True) == override
    assert override.is_dir()


def test_public_default_constants_are_outside_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    paths = _load_paths_module()

    assert paths.TEST_PHOTOS_DIR == paths.test_photos_dir()
    assert paths.WW_PAIRS_DIR == paths.ww_pairs_dir()
    assert _COMPONENT_DIR not in Path(paths.TEST_PHOTOS_DIR).parents
    assert _COMPONENT_DIR not in Path(paths.WW_PAIRS_DIR).parents


def test_gui_resolves_workspace_defaults_at_app_construction() -> None:
    source = _GUI_FILE.read_text(encoding="utf-8")

    assert "from .paths import ensure_data_dirs, test_photos_dir, ww_pairs_dir" in source
    assert "default_test_photos = test_photos_dir()" in source
    assert "default_ww_pairs = ww_pairs_dir()" in source
    assert "value=str(default_test_photos)" in source
    assert source.count("value=str(default_ww_pairs)") == 2
    assert "data/test_photos/" not in source


def test_cli_defaults_use_resolvers_and_explicit_paths_remain_authoritative() -> None:
    source = _CLI_FILE.read_text(encoding="utf-8")

    assert "input_dir = args.input_dir or test_photos_dir(for_write=True)" in source
    assert "output_dir = args.output_dir or ww_pairs_dir(for_write=True)" in source
    assert "pairs_dir = args.pairs_dir or ww_pairs_dir()" in source
    assert '"--input-dir",\n        type=Path,' in source
    assert '"--output-dir",\n        type=Path,' in source
    assert '"pairs_dir",\n        type=Path,\n        nargs="?",' in source
    assert 'Path(args.input_dir)' not in source
    assert 'Path(args.output_dir)' not in source


def test_runtime_write_inventory_no_longer_flags_print_optimize_paths() -> None:
    relative = "Komponenty/print_optimize/paths.py"

    findings, error = scan_python_source(
        relative,
        _PATHS_FILE.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
