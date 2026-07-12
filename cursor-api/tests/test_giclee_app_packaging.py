"""Testy kontraktu pakowania GicleeApp przez PyInstaller."""

from __future__ import annotations

import runpy
from pathlib import Path
from types import SimpleNamespace


def test_pyinstaller_spec_bundles_giclee_app_resources(
    monkeypatch,
) -> None:
    cursor_api_root = Path(__file__).resolve().parents[1]
    spec_path = cursor_api_root / "giclee_app.spec"
    resources_path = cursor_api_root / "giclee_app" / "resources"
    default_path = resources_path / "studio_categories.default.json"

    assert spec_path.is_file()
    assert default_path.is_file()

    captured: dict[str, object] = {}

    def fake_analysis(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["analysis_args"] = args
        captured["datas"] = list(kwargs.get("datas", []))
        return SimpleNamespace(
            pure=[],
            zipped_data=[],
            scripts=[],
            binaries=[],
            zipfiles=[],
            datas=list(kwargs.get("datas", [])),
        )

    def fake_pyz(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["pyz_args"] = args
        return object()

    def fake_exe(*args, **kwargs):  # noqa: ANN002, ANN003
        captured["exe_args"] = args
        return object()

    monkeypatch.chdir(cursor_api_root)

    runpy.run_path(
        str(spec_path),
        init_globals={
            "Analysis": fake_analysis,
            "PYZ": fake_pyz,
            "EXE": fake_exe,
            "SPECPATH": str(cursor_api_root),
        },
    )

    datas = captured.get("datas")
    assert isinstance(datas, list)

    normalized = {
        (
            Path(source).resolve(),
            str(destination).replace("\\", "/"),
        )
        for source, destination in datas
    }

    assert (
        resources_path.resolve(),
        "giclee_app/resources",
    ) in normalized