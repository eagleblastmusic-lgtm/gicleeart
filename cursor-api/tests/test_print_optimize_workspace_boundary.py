from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from Komponenty.print_optimize import cli, gui, paths
from tools.repository_safety.runtime_writes import scan_python_source


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


def _reset_public_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(paths, "TEST_PHOTOS_DIR", paths._DEFAULT_TEST_PHOTOS_DIR)
    monkeypatch.setattr(paths, "WW_PAIRS_DIR", paths._DEFAULT_WW_PAIRS_DIR)


def test_read_only_default_resolvers_use_local_appdata_without_creating_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    _reset_public_defaults(monkeypatch)

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
    monkeypatch.setattr(paths, "_LEGACY_TEST_PHOTOS_DIR", legacy_test)
    monkeypatch.setattr(paths, "_LEGACY_WW_PAIRS_DIR", legacy_pairs)
    _reset_public_defaults(monkeypatch)
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
    override = tmp_path / f"chosen-{constant_name.lower()}"
    monkeypatch.setattr(paths, constant_name, override)
    resolver = getattr(paths, resolver_name)

    assert resolver() == override
    assert not override.exists()
    assert resolver(for_write=True) == override
    assert override.is_dir()


def test_gui_resolves_workspace_defaults_at_app_construction() -> None:
    source = inspect.getsource(gui.PrintOptimizeApp.__init__)

    assert "default_test_photos = test_photos_dir()" in source
    assert "default_ww_pairs = ww_pairs_dir()" in source
    assert "value=str(default_test_photos)" in source
    assert source.count("value=str(default_ww_pairs)") == 2
    assert paths.COMPONENT_DIR not in paths.test_photos_dir().parents
    assert paths.COMPONENT_DIR not in paths.ww_pairs_dir().parents


def test_cli_collect_pairs_uses_safe_defaults_when_paths_are_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    default_input = tmp_path / "default-test-photos"
    default_output = tmp_path / "default-ww-pairs"
    calls: list[tuple[Path, Path, str, str, bool]] = []

    monkeypatch.setattr(cli, "test_photos_dir", lambda *, for_write=False: default_input)
    monkeypatch.setattr(cli, "ww_pairs_dir", lambda *, for_write=False: default_output)

    def fake_collect(
        input_dir: Path,
        output_dir: Path,
        *,
        product: str,
        locale: str,
        headless: bool,
    ) -> list[Any]:
        calls.append((Path(input_dir), Path(output_dir), product, locale, headless))
        return []

    monkeypatch.setattr(cli, "collect_pairs_for_directory", fake_collect)
    args = cli.build_parser().parse_args(["collect-pairs"])

    assert args.func(args) == 0
    assert calls == [
        (
            default_input,
            default_output,
            "item-acrylglasversieglung",
            "eu",
            True,
        )
    ]


def test_cli_explicit_workspace_paths_remain_exact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    chosen_input = tmp_path / "chosen-input"
    chosen_output = tmp_path / "chosen-output"
    calls: list[tuple[Path, Path]] = []

    def fake_collect(input_dir: Path, output_dir: Path, **_kwargs: Any) -> list[Any]:
        calls.append((Path(input_dir), Path(output_dir)))
        return []

    monkeypatch.setattr(cli, "collect_pairs_for_directory", fake_collect)
    args = cli.build_parser().parse_args(
        [
            "collect-pairs",
            "--input-dir",
            str(chosen_input),
            "--output-dir",
            str(chosen_output),
        ]
    )

    assert args.func(args) == 0
    assert calls == [(chosen_input, chosen_output)]


def test_runtime_write_inventory_no_longer_flags_print_optimize_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/print_optimize/paths.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
